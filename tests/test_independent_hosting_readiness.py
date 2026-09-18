"""Independent-hosting readiness contracts."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OVERLAY = REPO / "deploy" / "k8s" / "overlays" / "independent"
START_API = REPO / "scripts" / "start-api.sh"


def test_api_honors_platform_port_and_binds_all_interfaces() -> None:
    text = START_API.read_text(encoding="utf-8")
    assert 'PORT="${PORT:-${DSP_API_PORT:-8000}}"' in text
    assert 'HOST="${DSP_API_HOST:-0.0.0.0}"' in text
    assert '"--port" "$PORT"' in text or '--port "${PORT}"' in text


def test_overlay_uses_external_stateful_services() -> None:
    kustomization = (OVERLAY / "kustomization.yaml").read_text(encoding="utf-8")
    removal = (OVERLAY / "remove-stateful-services.yaml").read_text(encoding="utf-8")
    api = (OVERLAY / "api-patch.yaml").read_text(encoding="utf-8")
    assert "remove-stateful-services.yaml" in kustomization
    assert "name: postgres" in removal
    assert "name: redis" in removal
    assert "dsp-external-secrets" in api


def test_overlay_has_separate_web_and_api_configuration() -> None:
    web = (OVERLAY / "web-patch.yaml").read_text(encoding="utf-8")
    ingress = (OVERLAY / "ingress-patch.yaml").read_text(encoding="utf-8")
    assert "NEXT_PUBLIC_API_BASE_URL" in web
    assert "api.example.com" in ingress
    assert "app.example.com" in ingress


def test_cloud_run_authoritative_files_are_retired() -> None:
    assert not (REPO / "cloudbuild.yaml").exists()
    assert not (REPO / "cloudbuild-frontend.yaml").exists()
    assert not (REPO / "scripts" / "deploy-google-email-auth.sh").exists()


def test_provider_integrations_remain_application_config() -> None:
    env = (REPO / ".env.production.example").read_text(encoding="utf-8")
    assert "GEMINI_API_KEY" in env
    secrets = (OVERLAY / "external-config.example.yaml").read_text(encoding="utf-8")
    assert "dsp-external-secrets" in secrets
    assert "dsp-external-config" in secrets
