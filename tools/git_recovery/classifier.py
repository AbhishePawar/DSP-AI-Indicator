"""Classify changed files into logical recovery groups."""

from __future__ import annotations

from tools.git_recovery.models import ChangedFile, RecoveryGroup, Risk

# Ordered commit sequence (dependency-aware).
GROUP_ORDER: list[str] = [
    "configuration",
    "cicd",
    "documentation",
    "legal",
    "devops",
    "security",
    "authentication",
    "persistence",
    "workspace",
    "data_engine",
    "platform",
    "api",
    "frontend_foundation",
    "frontend_authentication",
    "frontend_legal",
    "frontend_dashboard",
    "frontend_research",
    "frontend_portfolio",
    "frontend_admin",
    "frontend_other",
    "tests",
    "other",
    "ignored",
]

_GROUP_META: dict[str, dict] = {
    "configuration": {
        "title": "Configuration",
        "purpose": "Repo hygiene, ignore rules, version pins, agent rules.",
        "message": "chore: sync repository configuration and version metadata",
        "depends_on": [],
        "risk": Risk.LOW,
        "epic": "Platform Core",
        "package": "root",
        "action": "COMMIT",
    },
    "cicd": {
        "title": "CI/CD",
        "purpose": "GitHub Actions and release automation.",
        "message": "ci: update continuous integration and release workflows",
        "depends_on": ["configuration"],
        "risk": Risk.MEDIUM,
        "epic": "DevOps",
        "package": ".github",
        "action": "COMMIT",
    },
    "documentation": {
        "title": "Documentation",
        "purpose": "Architecture, epic, ops, and governance documentation.",
        "message": "docs: sync platform documentation and epic guides",
        "depends_on": [],
        "risk": Risk.LOW,
        "epic": "Documentation",
        "package": "docs",
        "action": "COMMIT",
    },
    "legal": {
        "title": "Legal",
        "purpose": "Legal policies, disclaimers, and compliance docs/pages.",
        "message": "docs(legal): sync policies, disclosures, and compliance materials",
        "depends_on": [],
        "risk": Risk.LOW,
        "epic": "Legal / Compliance",
        "package": "docs / apps/web legal",
        "action": "COMMIT",
    },
    "devops": {
        "title": "DevOps",
        "purpose": "Docker, scripts, and operational tooling.",
        "message": "chore(devops): update docker and operational scripts",
        "depends_on": ["configuration"],
        "risk": Risk.MEDIUM,
        "epic": "DevOps",
        "package": "docker / scripts",
        "action": "COMMIT",
    },
    "security": {
        "title": "Security",
        "purpose": "Security platform package and hardening.",
        "message": "feat(security): update security platform hardening",
        "depends_on": [],
        "risk": Risk.HIGH,
        "epic": "Security",
        "package": "packages/security_platform",
        "action": "REVIEW",
    },
    "authentication": {
        "title": "Authentication",
        "purpose": "Auth packages and backend authentication surfaces.",
        "message": "feat(auth): update authentication packages and wiring",
        "depends_on": ["security"],
        "risk": Risk.HIGH,
        "epic": "Authentication",
        "package": "packages/auth",
        "action": "REVIEW",
    },
    "persistence": {
        "title": "Persistence",
        "purpose": "Persistence package and storage layer.",
        "message": "feat(persistence): update persistence package",
        "depends_on": [],
        "risk": Risk.HIGH,
        "epic": "Persistence",
        "package": "packages/persistence",
        "action": "REVIEW",
    },
    "workspace": {
        "title": "Workspace",
        "purpose": "Workspace package and decision workspace backends.",
        "message": "feat(workspace): update workspace package",
        "depends_on": ["persistence"],
        "risk": Risk.HIGH,
        "epic": "Workspace",
        "package": "packages/workspace",
        "action": "REVIEW",
    },
    "data_engine": {
        "title": "Data Engine",
        "purpose": "Market data, statements, corporate actions, orchestrator.",
        "message": "feat(data-engine): update data engine domain modules",
        "depends_on": [],
        "risk": Risk.HIGH,
        "epic": "Data Engine",
        "package": "packages/data_engine",
        "action": "REVIEW",
    },
    "platform": {
        "title": "Platform",
        "purpose": "dsp_platform facades and composition root wiring.",
        "message": "feat(platform): update dsp_platform facades and composition",
        "depends_on": [
            "security",
            "authentication",
            "persistence",
            "workspace",
            "data_engine",
        ],
        "risk": Risk.HIGH,
        "epic": "Platform Core",
        "package": "packages/dsp_platform",
        "action": "REVIEW",
    },
    "api": {
        "title": "API",
        "purpose": "api_platform routers, schemas, and API tests.",
        "message": "feat(api): update api_platform routers and tests",
        "depends_on": ["platform"],
        "risk": Risk.CRITICAL,
        "epic": "API",
        "package": "packages/api_platform",
        "action": "REVIEW",
    },
    "frontend_foundation": {
        "title": "Frontend Foundation",
        "purpose": "Design system, tokens, shell, tooling config.",
        "message": "feat(web): update frontend foundation and design system",
        "depends_on": [],
        "risk": Risk.MEDIUM,
        "epic": "Frontend",
        "package": "apps/web",
        "action": "COMMIT",
    },
    "frontend_authentication": {
        "title": "Frontend Authentication",
        "purpose": "Login, session, route gates, and auth UI.",
        "message": "feat(web): update frontend authentication flows",
        "depends_on": ["frontend_foundation", "authentication"],
        "risk": Risk.HIGH,
        "epic": "Frontend / Auth",
        "package": "apps/web",
        "action": "REVIEW",
    },
    "frontend_legal": {
        "title": "Frontend Legal",
        "purpose": "In-app legal pages and disclaimer gates.",
        "message": "feat(web): update legal pages and disclaimer gates",
        "depends_on": ["frontend_foundation", "legal"],
        "risk": Risk.LOW,
        "epic": "Legal",
        "package": "apps/web",
        "action": "COMMIT",
    },
    "frontend_dashboard": {
        "title": "Frontend Dashboard",
        "purpose": "Dashboard widgets and institutional dashboard UI.",
        "message": "feat(web): update dashboard and institutional widgets",
        "depends_on": ["frontend_foundation"],
        "risk": Risk.MEDIUM,
        "epic": "Dashboard",
        "package": "apps/web",
        "action": "COMMIT",
    },
    "frontend_research": {
        "title": "Frontend Research",
        "purpose": "Research workspace and related UI.",
        "message": "feat(web): update research workspace UI",
        "depends_on": ["frontend_foundation", "api"],
        "risk": Risk.HIGH,
        "epic": "Research",
        "package": "apps/web",
        "action": "REVIEW",
    },
    "frontend_portfolio": {
        "title": "Frontend Portfolio",
        "purpose": "Portfolio intelligence and advisor UI.",
        "message": "feat(web): update portfolio intelligence UI",
        "depends_on": ["frontend_foundation", "api"],
        "risk": Risk.HIGH,
        "epic": "Portfolio",
        "package": "apps/web",
        "action": "REVIEW",
    },
    "frontend_admin": {
        "title": "Frontend Admin",
        "purpose": "Admin console UI and admin API clients.",
        "message": "feat(web): update admin console UI",
        "depends_on": ["frontend_foundation", "api"],
        "risk": Risk.MEDIUM,
        "epic": "Admin",
        "package": "apps/web",
        "action": "COMMIT",
    },
    "frontend_other": {
        "title": "Frontend Other",
        "purpose": "Remaining apps/web changes not mapped to a feature group.",
        "message": "feat(web): update miscellaneous frontend surfaces",
        "depends_on": ["frontend_foundation"],
        "risk": Risk.MEDIUM,
        "epic": "Frontend",
        "package": "apps/web",
        "action": "REVIEW",
    },
    "tests": {
        "title": "Tests",
        "purpose": "Cross-cutting or leftover test-only changes.",
        "message": "test: sync recovery-related and leftover test updates",
        "depends_on": [],
        "risk": Risk.LOW,
        "epic": "Testing",
        "package": "various",
        "action": "COMMIT",
    },
    "other": {
        "title": "Other",
        "purpose": "Unclassified paths requiring human review.",
        "message": "chore: apply unclassified recovery changes",
        "depends_on": [],
        "risk": Risk.HIGH,
        "epic": "Other",
        "package": "various",
        "action": "REVIEW",
    },
    "ignored": {
        "title": "Ignored (never commit)",
        "purpose": "Build outputs, caches, secrets, and generated artifacts.",
        "message": "",
        "depends_on": [],
        "risk": Risk.IGNORE,
        "epic": "Safety",
        "package": "n/a",
        "action": "IGNORE",
    },
}


def is_ignored_path(path: str) -> bool:
    """Return True for paths that must never be staged by recovery."""
    p = path.replace("\\", "/").lower()
    markers = (
        "node_modules/",
        "/.next/",
        ".next/",
        "__pycache__/",
        ".pyc",
        ".tsbuildinfo",
        ".pack",
        "/dist/",
        "/build/",
        "/coverage/",
        ".pytest_cache/",
        ".ruff_cache/",
        ".mypy_cache/",
        ".venv/",
        "/venv/",
        ".env",
        ".pem",
        ".key",
        "credentials",
        "id_rsa",
    )
    # Allow documented examples
    if p.endswith(".env.example") or p.endswith(".env.production.example"):
        return False
    if p.endswith(".env") or "/.env." in f"/{p}" or p.startswith(".env"):
        return True
    return any(m in p for m in markers if m not in (".env",))


def classify_path(path: str) -> str:
    """Map a single path to a group key."""
    p = path.replace("\\", "/")

    if is_ignored_path(p):
        return "ignored"

    # Root / config
    if p in {".gitignore", "VERSION", "CONTRIBUTING.md", "LICENSE", "LICENSE.md"}:
        return "configuration"
    if p.startswith(".cursor/") or p.startswith(".vscode/") or p.endswith(".editorconfig"):
        return "configuration"
    if p.startswith(".github/"):
        return "cicd"
    if p.startswith("docker/") or p.startswith("scripts/") or p.startswith("monitoring/") or p.startswith("grafana/"):
        return "devops"
    if p.startswith("tools/"):
        # Tooling itself — treat as devops/other tooling
        return "devops"

    # Docs
    if p.startswith("docs/"):
        name = p[5:]
        legal_tokens = (
            "LEGAL",
            "PRIVACY",
            "TERMS",
            "RISK_DISCLOSURE",
            "COOKIE",
            "DATA_USAGE",
            "DISCLAIMER",
            "COMPLIANCE",
            "PEP_004",
            "P4_",
        )
        if any(t in name.upper() for t in legal_tokens) or name.upper().startswith("TERMS"):
            return "legal"
        return "documentation"

    # Packages
    if p.startswith("packages/security_platform/"):
        return "security"
    if p.startswith("packages/auth/"):
        return "authentication"
    if p.startswith("packages/persistence/"):
        return "persistence"
    if p.startswith("packages/workspace/"):
        return "workspace"
    if p.startswith("packages/data_engine/"):
        return "data_engine"
    if p.startswith("packages/dsp_platform/") or p.startswith("packages/dsp/"):
        return "platform"
    if p.startswith("packages/api_platform/"):
        return "api"
    if p.startswith("packages/admin/"):
        # Admin backend sits with platform/admin; fold into platform for recovery order
        return "platform"
    if p.startswith("packages/"):
        return "other"

    # Frontend
    if p.startswith("apps/web/"):
        low = p.lower()
        if any(
            x in low
            for x in (
                "/e2e/",
                ".test.",
                ".spec.",
                "vitest",
                "__tests__/",
                "/tests/",
            )
        ):
            return "tests"
        if any(
            x in low
            for x in (
                "foundation/",
                "/components/ds/",
                "/tokens",
                "eslint.config",
                "prettier",
                "components.json",
                "globals.css",
            )
        ) or low.endswith("tsconfig.json"):
            return "frontend_foundation"
        if any(
            x in low
            for x in (
                "/login",
                "/auth",
                "forgot-password",
                "session-expired",
                "forbidden",
                "unauthorized",
                "authstore",
                "authprovider",
                "protectedroute",
                "authpermission",
            )
        ):
            return "frontend_authentication"
        if any(
            x in low
            for x in (
                "/legal",
                "disclaimer",
                "privacy",
                "terms",
                "cookie",
                "risk-disclosure",
                "data-usage",
            )
        ):
            return "frontend_legal"
        if "dashboard" in low:
            return "frontend_dashboard"
        if "research" in low:
            return "frontend_research"
        if "portfolio" in low or "/advisor/" in low:
            return "frontend_portfolio"
        if "admin" in low:
            return "frontend_admin"
        return "frontend_other"

    # Generic tests outside apps/web
    if "/tests/" in p or p.startswith("tests/") or p.endswith("_test.py") or p.startswith("test_"):
        return "tests"

    return "other"


def classify_files(files: list[ChangedFile]) -> list[RecoveryGroup]:
    """Bucket files into ordered RecoveryGroup objects."""
    buckets: dict[str, list[ChangedFile]] = {k: [] for k in GROUP_ORDER}
    for item in files:
        key = classify_path(item.path)
        if key not in buckets:
            key = "other"
        buckets[key].append(item)

    groups: list[RecoveryGroup] = []
    for key in GROUP_ORDER:
        meta = _GROUP_META[key]
        file_list = buckets[key]
        if not file_list and key == "ignored":
            continue
        if not file_list:
            continue
        groups.append(
            RecoveryGroup(
                key=key,
                title=meta["title"],
                purpose=meta["purpose"],
                files=sorted(file_list, key=lambda f: f.path),
                suggested_message=meta["message"],
                depends_on=list(meta["depends_on"]),
                risk=meta["risk"],
                epic=meta["epic"],
                package=meta["package"],
                action=meta["action"],
            )
        )
    return groups
