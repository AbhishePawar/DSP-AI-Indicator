"""Production deploys use immutable per-commit image tags and roll back exactly.

The deploy/rollback shell scripts run against a fake ``docker`` that keeps
images and running containers in a JSON file, and a fake ``git`` that reports
a commit SHA and working-tree status, so these tests prove the scripts'
behaviour without a Docker daemon or repository.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]

FAKE_DOCKER = r"""#!/usr/bin/env python3
import json, os, sys, uuid
state_path = os.environ["FAKE_DOCKER_STATE"]
st = json.load(open(state_path))
def save(): json.dump(st, open(state_path, "w"))
a = sys.argv[1:]
st["calls"].append(a)
def ref(svc):
    e = os.environ
    if svc == "api": return f"{e.get('DSP_API_IMAGE','dsp-api')}:{e.get('DSP_IMAGE_TAG','2.0.0')}"
    if svc == "web": return f"{e.get('DSP_WEB_IMAGE','dsp-web')}:{e.get('DSP_IMAGE_TAG_WEB','2.0.0-rc.1')}"
    return None
if a[0] == "compose":
    i = 1
    while a[i] in ("--env-file", "-f"): i += 2
    cmd, rest = a[i], a[i + 1:]
    if cmd == "build":
        for svc in ("api", "web"):
            st["images"][ref(svc)] = "sha256:" + uuid.uuid4().hex
    elif cmd == "up":
        for svc in ("api", "web"):
            r = ref(svc)
            if r not in st["images"]:
                print(f"missing image {r}", file=sys.stderr); save(); sys.exit(1)
            st["running"][svc] = {"ref": r, "id": st["images"][r]}
    elif cmd == "ps":
        svc = rest[-1]
        if svc in st["running"]: print("cid-" + svc)
    elif cmd == "exec":
        save(); sys.exit(1 if os.environ.get("FAKE_UNHEALTHY") else 0)
    save(); sys.exit(0)
if a[:2] == ["image", "inspect"]:
    r = a[-1]
    if r not in st["images"]: save(); sys.exit(1)
    if "-f" in a: print(st["images"][r])
    save(); sys.exit(0)
if a[0] == "inspect":
    c = st["running"][a[-1][4:]]
    print(c["id"] if a[2] == "{{.Image}}" else c["ref"])
    save(); sys.exit(0)
if a[0] == "tag":
    st["images"][a[2]] = a[1]; save(); sys.exit(0)
save(); sys.exit(2)
"""

FAKE_GIT = r"""#!/usr/bin/env python3
import os, sys
a = [x for x in sys.argv[1:]]
if a[:1] == ["-C"]: a = a[2:]
d = os.environ["FAKE_GIT_DIR"]
if a[:1] == ["rev-parse"]:
    print(open(os.path.join(d, "HEAD")).read().strip()); sys.exit(0)
if a[:1] == ["status"]:
    p = os.path.join(d, "DIRTY")
    if os.path.exists(p): print(" M " + open(p).read().strip())
    sys.exit(0)
sys.exit(2)
"""

ENV = """DSP_ENVIRONMENT=production
DSP_PUBLIC_DOMAIN=dspaiindicator.com
DSP_WWW_REDIRECT_DOMAIN=www.dspaiindicator.com
DSP_IMAGE_TAG=2.0.0
DSP_IMAGE_TAG_WEB=2.0.0-rc.1
DSP_SMOKE_REQUIRE_HTTPS=false
"""


def _exe(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture()
def site(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "docker").mkdir()
    for name in ("deploy_production.sh", "rollback_production.sh"):
        shutil.copy(_REPO / "scripts" / name, root / "scripts" / name)
    (root / "scripts" / "validate_env.py").write_text("")
    (root / "docker" / "docker-compose.production.yml").write_text("services: {}\n")
    (root / "VERSION").write_text("2.0.0-rc.1\n")
    (root / ".env.production").write_text(ENV)

    bindir = tmp_path / "bin"
    bindir.mkdir()
    _exe(bindir / "docker", FAKE_DOCKER)
    _exe(bindir / "git", FAKE_GIT)
    gitdir = tmp_path / "git"
    gitdir.mkdir()
    _exe(bindir / "python", "#!/bin/sh\nexit 0\n")
    _exe(bindir / "sleep", "#!/bin/sh\nexit 0\n")
    state = tmp_path / "docker.json"
    # A legacy release is live under a mutable tag, as on the VPS today.
    state.write_text(
        json.dumps(
            {
                "images": {
                    "dsp-api:2.0.0-rc.1": "sha256:legacyapi",
                    "dsp-web:2.0.0-rc.1": "sha256:legacyweb",
                },
                "running": {
                    "api": {"ref": "dsp-api:2.0.0-rc.1", "id": "sha256:legacyapi"},
                    "web": {"ref": "dsp-web:2.0.0-rc.1", "id": "sha256:legacyweb"},
                },
                "calls": [],
            }
        )
    )
    env = {
        **os.environ,
        "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}",
        "FAKE_DOCKER_STATE": str(state),
        "FAKE_GIT_DIR": str(gitdir),
    }
    env.pop("COMPOSE_PROFILES", None)

    def set_head(msg: str) -> str:
        sha = hashlib.sha1(msg.encode()).hexdigest()
        (gitdir / "HEAD").write_text(sha)
        return sha

    set_head("release A")

    class Site:
        path = root

        def run(self, script: str, *args: str, **extra: str):
            return subprocess.run(
                ["bash", f"scripts/{script}", *args],
                cwd=root,
                env={**env, **extra},
                capture_output=True,
                text=True,
            )

        def commit(self, msg: str) -> str:
            return set_head(msg)

        def head(self) -> str:
            return (gitdir / "HEAD").read_text()

        def make_dirty(self, path: str) -> None:
            (gitdir / "DIRTY").write_text(path)

        def state(self) -> dict:
            return json.loads(state.read_text())

    return Site()


def _running(site) -> tuple[str, str]:
    r = site.state()["running"]
    return r["api"]["id"], r["web"]["id"]


def test_deploy_tags_images_with_version_and_commit_not_env_defaults(site):
    res = site.run("deploy_production.sh")
    assert res.returncode == 0, res.stderr
    tag = f"2.0.0-rc.1-{site.head()[:12]}"
    st = site.state()
    assert st["running"]["api"]["ref"] == f"dsp-api:{tag}"
    assert st["running"]["web"]["ref"] == f"dsp-web:{tag}"
    assert "DSP_IMAGE_TAG=2.0.0 in" in res.stdout  # env-file tag reported as ignored
    # The legacy mutable images were never overwritten.
    assert st["images"]["dsp-api:2.0.0-rc.1"] == "sha256:legacyapi"


def test_redeploying_same_commit_refuses_to_rebuild_existing_tag(site):
    assert site.run("deploy_production.sh").returncode == 0
    before = site.state()["images"]
    res = site.run("deploy_production.sh")
    assert res.returncode == 1
    assert "already exists" in res.stderr
    assert site.state()["images"] == before


def test_dirty_working_tree_is_refused(site):
    site.make_dirty("scripts/deploy_production.sh")
    res = site.run("deploy_production.sh")
    assert res.returncode == 1
    assert "uncommitted or untracked" in res.stderr
    assert not any(c[:1] == ["compose"] and "build" in c for c in site.state()["calls"])


def test_rollback_restores_previous_release_then_legacy(site):
    assert site.run("deploy_production.sh").returncode == 0
    release_a = _running(site)
    site.commit("release B")
    assert site.run("deploy_production.sh").returncode == 0
    assert _running(site) != release_a

    res = site.run("rollback_production.sh")
    assert res.returncode == 0, res.stderr
    assert _running(site) == release_a


def test_rollback_after_failed_deploy_returns_to_last_known_good(site):
    assert site.run("deploy_production.sh").returncode == 0
    release_a = _running(site)
    site.commit("release B")
    failed = site.run("deploy_production.sh", FAKE_UNHEALTHY="1")
    assert failed.returncode == 1
    assert "was not promoted" in failed.stderr
    assert _running(site) != release_a

    res = site.run("rollback_production.sh")
    assert res.returncode == 0, res.stderr
    assert _running(site) == release_a


def test_first_deploy_pins_live_legacy_release_for_rollback(site):
    assert site.run("deploy_production.sh").returncode == 0
    res = site.run("rollback_production.sh")
    assert res.returncode == 0, res.stderr
    assert _running(site) == ("sha256:legacyapi", "sha256:legacyweb")


def test_rollback_refuses_when_recorded_tag_was_repointed(site):
    assert site.run("deploy_production.sh").returncode == 0
    site.commit("release B")
    assert site.run("deploy_production.sh").returncode == 0
    record = (
        site.path / ".dsp_production_releases" / "known_good_previous.env"
    ).read_text()
    api_ref = next(
        l.split("=", 1)[1] for l in record.splitlines() if l.startswith("API_REF=")
    )
    st = site.state()
    st["images"][api_ref] = "sha256:tampered"
    (site.path.parent / "docker.json").write_text(json.dumps(st))
    res = site.run("rollback_production.sh")
    assert res.returncode == 1
    assert "different image than recorded" in res.stderr


def test_release_records_are_gitignored_so_next_deploy_sees_a_clean_tree():
    ignored = (_REPO / ".gitignore").read_text().splitlines()
    assert ".dsp_production_releases/" in ignored
