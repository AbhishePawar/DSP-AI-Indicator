"""Tests for path classification."""

from __future__ import annotations

from tools.git_recovery.classifier import classify_files, classify_path, is_ignored_path
from tools.git_recovery.models import ChangedFile


def test_classify_core_paths() -> None:
    assert classify_path(".gitignore") == "configuration"
    assert classify_path(".github/workflows/release.yml") == "cicd"
    assert classify_path("docs/EPIC_F000_README.md") == "documentation"
    assert classify_path("docs/PRIVACY_POLICY_v1.6.0.md") == "legal"
    assert classify_path("docker/docker-compose.prod.yml") == "devops"
    assert classify_path("packages/security_platform/src/x.py") == "security"
    assert classify_path("packages/auth/src/auth/x.py") == "authentication"
    assert classify_path("packages/persistence/src/x.py") == "persistence"
    assert classify_path("packages/workspace/src/x.py") == "workspace"
    assert classify_path("packages/data_engine/src/x.py") == "data_engine"
    assert classify_path("packages/dsp_platform/src/x.py") == "platform"
    assert classify_path("packages/api_platform/src/x.py") == "api"


def test_classify_frontend_paths() -> None:
    assert classify_path("apps/web/src/foundation/tokens/colors.ts") == "frontend_foundation"
    assert classify_path("apps/web/src/app/login/LoginForm.tsx") == "frontend_authentication"
    assert classify_path("apps/web/src/app/docs/privacy/page.tsx") == "frontend_legal"
    assert classify_path("apps/web/src/app/dashboard/page.tsx") == "frontend_dashboard"
    assert classify_path("apps/web/src/lib/research-workspace/index.ts") == "frontend_research"
    assert classify_path("apps/web/src/lib/portfolio-intelligence/index.ts") == "frontend_portfolio"
    assert classify_path("apps/web/src/app/admin/page.tsx") == "frontend_admin"
    assert classify_path("apps/web/src/e2e/login.journey.test.tsx") == "tests"


def test_ignore_generated_and_secrets() -> None:
    assert is_ignored_path("apps/web/.next/cache/x")
    assert is_ignored_path("apps/web/node_modules/lodash/index.js")
    assert is_ignored_path(".env")
    assert is_ignored_path("apps/web/.env.local")
    assert not is_ignored_path("apps/web/.env.example")
    assert classify_path("apps/web/.next/cache/x") == "ignored"


def test_classify_files_orders_groups() -> None:
    files = [
        ChangedFile("??", "packages/api_platform/x.py"),
        ChangedFile("M", ".gitignore"),
        ChangedFile("??", "docs/A.md"),
    ]
    groups = classify_files(files)
    keys = [g.key for g in groups]
    assert keys.index("configuration") < keys.index("documentation")
    assert keys.index("documentation") < keys.index("api")
