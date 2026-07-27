# Coding Standards — DSP AI Indicator

| Field | Value |
|---|---|
| **Version** | `1.0.0` |
| **Status** | **Active** |
| **Last updated** | 2026-07-27 |
| **Audience** | All engineers · AI agents · reviewers |
| **Operational companion** | Day-to-day quick reference → [DSP_CODING_STANDARDS.md](DSP_CODING_STANDARDS.md) |

---

## 1. Python Style

### 1.1 General

| Rule | Standard |
|---|---|
| Python version | 3.11+ (project baseline) |
| Formatter | `ruff format` or project-configured formatter |
| Linter | `ruff check` |
| Type checker | `mypy` (strict on public APIs) |
| Import sorter | `ruff` isort rules or equivalent |
| Line length | 100 characters (project default) |
| Encoding | UTF-8 for all source files |

### 1.2 Module structure

```text
packages/<name>/
├── pyproject.toml
├── README.md
├── src/
│   └── <name>/
│       ├── __init__.py          # Public façade exports
│       ├── <domain>/            # Domain modules
│       └── ports/               # Hexagonal port interfaces
└── tests/
    ├── unit/
    └── integration/
```

### 1.3 Import order

1. Standard library
2. Third-party packages
3. `contracts` and `core`
4. Same-package modules
5. Local imports (avoid unless breaking circular dependency)

Cross-package imports use **public façades only**:

```python
# Correct
from valuation import ValuationEngine

# Incorrect — deep private import
from valuation.dcf.engine import DCFEngine
```

---

## 2. Naming Conventions

### 2.1 Python

| Element | Convention | Example |
|---|---|---|
| Packages | `snake_case` | `data_engine`, `business_quality` |
| Modules | `snake_case` | `income_intelligence.py` |
| Classes | `PascalCase` | `ValuationResult`, `DecisionPack` |
| Functions / methods | `snake_case` | `analyze_financials()` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_LOOKBACK_DAYS` |
| Private members | `_leading_underscore` | `_compute_score()` |
| Type aliases | `PascalCase` | `InstrumentId = str` |
| Enums | `PascalCase` class, `UPPER_SNAKE` members | `AssetClass.EQUITY` |
| Protocols | `PascalCase` with suffix | `DataProviderPort` |

### 2.2 TypeScript (web)

| Element | Convention | Example |
|---|---|---|
| Components | `PascalCase` | `CompanySnapshot.tsx` |
| Hooks | `camelCase` with `use` prefix | `useDecisionPack()` |
| View-models | `PascalCase` with suffix | `DecisionPackViewModel` |
| Mappers | `camelCase` with suffix | `mapDecisionPack()` |
| Constants | `UPPER_SNAKE_CASE` | `RESEARCH_MODE_LABELS` |
| Files | Match primary export | `DecisionDashboard.tsx` |

### 2.3 Documentation & artifacts

| Element | Convention | Example |
|---|---|---|
| ADRs | `ADR-<scope>-<seq>-<slug>.md` | `ADR-FEATURE-001-001-economic-moat-core.md` |
| Sprint briefs | `<EPIC>_SPRINT<n>_<NAME>.md` | `F3_SPRINT7_BUSINESS_QUALITY_AGGREGATOR.md` |
| Feature reports | `FEATURE_<nnn>_<NAME>.md` | `FEATURE_008_INVESTMENT_COMMITTEE.md` |

Terminology authority → [DSP_GLOSSARY.md](DSP_GLOSSARY.md).

---

## 3. Folder Rules

| Rule | Detail |
|---|---|
| One package = one directory under `packages/` | No shared code outside packages except `apps/` |
| Public API in `__init__.py` or dedicated façade module | Consumers import from package root |
| Tests mirror source structure | `tests/unit/test_<module>.py` |
| No business logic in `scripts/` | Scripts are bootstrap, CI, and backfill only |
| No domain code in `apps/web/src/lib/` mappers beyond view-model transformation | Mappers translate envelopes; they do not compute |
| Config outside source | `configs/environments/` for environment YAML |
| Docs in `docs/` only | No README sprawl in random directories (except package README cards) |

---

## 4. Architecture Rules

| Rule | Detail |
|---|---|
| Depend inward only | Lower layers never import higher layers |
| Single ownership | One package owns each durable artifact |
| Cite, don't embed | Reference upstream by ID/digest; never re-home aggregates |
| Composition root | `dsp_platform` wires engines; domains don't import it |
| Thin client | Zero investment math in `apps/web` |
| Hexagonal ports | I/O through port interfaces; adapters at edge |
| No circular imports | Extract to `contracts` or invert via port |
| Freeze discipline | Protected modules require ADR + explicit unlock |
| Application import rule | Apps import `dsp_platform` + `contracts` only |

Full dependency matrices → [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) · [DSP_ARCHITECTURE.md](DSP_ARCHITECTURE.md).

---

## 5. SOLID Principles

### Single Responsibility
Each package, class, and module has one reason to change. Scoring logic lives in the engine that owns the score — not in orchestration, API, or web layers.

### Open/Closed
New valuation methods, indicators, and data providers extend via registry registration — not by modifying existing engine internals.

### Liskov Substitution
Port implementations (adapters, providers) are interchangeable without breaking callers. All `DataProviderPort` implementations return normalized domain objects.

### Interface Segregation
Ports are narrow and purpose-specific. Separate ports for data acquisition, LLM inference, and storage — not a single `GodPort`.

### Dependency Inversion
Domain engines depend on port abstractions (`Protocol` / `ABC`), not concrete vendor SDKs. Vendor code lives in adapter modules at the package edge.

---

## 6. Error Handling

### 6.1 Principles

| Principle | Implementation |
|---|---|
| Fail explicitly | Raise domain exceptions; never return `None` silently for missing required data |
| Classify errors | Distinguish validation, data unavailable, configuration, and internal errors |
| Preserve context | Exception messages include instrument, date range, and operation |
| No bare `except` | Catch specific exception types |
| Unavailable ≠ error | Missing optional data → `Unavailable` status in output, not exception |
| Required data missing | Raise `InsufficientDataError` (or package-specific equivalent) |

### 6.2 Domain exceptions

Define in package-specific `exceptions.py` or inherit from `core` base exceptions:

```python
class InsufficientDataError(DomainError):
    """Required input data is missing or incomplete."""

class ValidationError(DomainError):
    """Input fails domain validation rules."""
```

### 6.3 API layer

- Domain exceptions → HTTP 422 (validation) or 503 (data unavailable)
- Never expose stack traces in production responses
- Log full traceback server-side with correlation ID

### 6.4 Web layer

- API errors → user-friendly messages with retry affordance
- Unavailable data → skeleton/empty states, never fabricated values
- Network failure → offline indicator with cached envelope if available

---

## 7. Logging

| Rule | Detail |
|---|---|
| Library | Standard `logging` module; structured JSON in production |
| Levels | DEBUG (dev only) · INFO (operations) · WARNING (degraded) · ERROR (failures) |
| No secrets | Never log API keys, tokens, or PII |
| Correlation ID | Propagate through request pipeline for traceability |
| Engine logging | Log inputs hash, engine version, and output summary — not full payloads |
| Performance | Log duration for engine execution and API endpoints |
| Audit events | Research queries, exports, and mode changes at INFO with user attribution |

---

## 8. Testing

### 8.1 Test pyramid

| Layer | Scope | Location |
|---|---|---|
| Unit | Single function/class, deterministic | `packages/<name>/tests/unit/` |
| Integration | Cross-module within package | `packages/<name>/tests/integration/` |
| Architecture | Import rules, ownership, cycles | `tests/architecture/` |
| Platform E2E | Full pipeline offline | `packages/dsp_platform/tests/` |
| Web | View-model mappers, components | `apps/web/` (vitest) |

### 8.2 Test requirements

| Requirement | Detail |
|---|---|
| Determinism | Same inputs → same outputs; no network in unit tests |
| Fixtures | Synthetic market data in `tests/fixtures/` |
| Naming | `test_<behavior>_<condition>_<expected>()` |
| Coverage | All public APIs and scoring paths |
| Offline E2E | BUY / SELL / HOLD / partial data / disagreement / failure scenarios |
| Architecture tests | 30/30 PASS minimum (ASI-006) |

### 8.3 Regression policy — official GREEN definition

A change set is **GREEN** only when **all** applicable rows pass:

| Dimension | Pass criteria |
|---|---|
| Build | Relevant packages/apps compile/install without error |
| Tests | Targeted suite passes; full regression when engines/API touched |
| Architecture | Ownership, dependency rules, thin-client invariants hold |
| Public APIs | `/api/v1` backward compatible unless epic explicitly breaks |
| Deterministic outputs | Same engine inputs → same outputs |
| Documentation | STATUS/VERSION_MATRIX updated when release-facing |

If any applicable dimension fails → **not GREEN**. Do not claim COMPLETE.

Testing matrix → [PACKAGE_TESTING_MATRIX.md](PACKAGE_TESTING_MATRIX.md).

---

## 9. Type Hints

| Rule | Detail |
|---|---|
| All public functions | Fully typed parameters and return types |
| Domain models | `@dataclass(frozen=True)` or Pydantic models with typed fields |
| mypy scope | `contracts`, `core`, `orchestration`, `dsp_platform` (Phase A5 baseline) |
| No untyped public APIs | `# type: ignore` requires comment explaining why |
| Protocols | Use `typing.Protocol` for port interfaces |
| Generics | Use `TypeVar` and `Generic` where collections are typed |
| Optional | Use `X | None` (Python 3.10+ union syntax) |

Policy detail → [TYPING.md](TYPING.md).

---

## 10. Performance

| Rule | Detail |
|---|---|
| Profile before optimizing | Measure engine execution time with representative inputs |
| Immutable value objects | Frozen dataclasses for domain artifacts (enables safe caching) |
| Lazy evaluation | Compute engine outputs on demand, not eagerly for all sections |
| Caching | Decision Pack envelopes cacheable by config hash |
| No premature async | Synchronous engines unless I/O-bound adapter requires async |
| Batch operations | Multi-stock analysis uses batch paths in `universe` |
| Web performance | Lazy panel loading; avoid accidental heavy component trees |
| Memory | Stream large time series; don't load full history into memory |

Performance notes → [packages/dsp_platform/PERFORMANCE.md](../packages/dsp_platform/PERFORMANCE.md).

---

## 11. Documentation

### 11.1 Code documentation

| Element | Standard |
|---|---|
| Public APIs | Docstring with purpose, parameters, returns, raises |
| Domain models | Field-level comments for non-obvious semantics |
| Complex algorithms | Inline comments explaining business logic, not syntax |
| Registries | Each registered item documented with parameters and version |

### 11.2 Package README cards

Every registered package maintains a README per ASI-005:

- Purpose (one sentence)
- Public API entry points
- Dependencies
- Status and version
- Test command

### 11.3 Architectural changes

- ADR required for dependency direction changes, new packages, or freeze modifications
- Sprint brief for every epic delivery
- STATUS update when release-facing

---

## 12. Security

| Rule | Detail |
|---|---|
| Secrets | Never commit API keys, tokens, or credentials |
| Environment | `.env.example` documents required vars; `.env` gitignored |
| Input validation | Validate all external input at API boundary and engine entry |
| Dependency scanning | CI security scan on dependencies |
| Auth | `security_platform` handles auth; domain remains auth-independent |
| RBAC | Role-based access at API layer (future enterprise) |
| Audit | Log research queries and exports with user attribution |
| LLM safety | LLM adapters must not invent financial numbers — see [AI_PRINCIPLES.md](AI_PRINCIPLES.md) |
| SQL injection | Parameterized queries only (when DB layer added) |
| XSS | React auto-escaping; no `dangerouslySetInnerHTML` with user content |

---

## 13. Review Checklist

Every pull request must satisfy this checklist before merge:

### Architecture
- [ ] Dependency direction respected (no upward imports)
- [ ] Single ownership of new artifacts
- [ ] No investment math in `apps/web`
- [ ] Public façade used for cross-package imports
- [ ] No circular imports introduced
- [ ] ADR filed if architecture changed

### Code quality
- [ ] Type hints on all new public APIs
- [ ] Docstrings on public functions and classes
- [ ] No bare `except` clauses
- [ ] No secrets or credentials in diff
- [ ] Naming follows conventions (§2)

### Testing
- [ ] Unit tests for new logic
- [ ] Integration tests if cross-module
- [ ] Architecture tests pass (if applicable)
- [ ] Deterministic: same inputs → same outputs
- [ ] Regression GREEN (§8.3)

### Trust & explainability
- [ ] User-visible outputs cite source and confidence
- [ ] Missing data labeled Unavailable (not fabricated)
- [ ] AI outputs distinguished from calculated values
- [ ] Research Mode terminology used (unless SEBI mode flagged)

### Documentation
- [ ] Package README updated (if new package)
- [ ] STATUS/VERSION_MATRIX updated (if release-facing)
- [ ] Sprint brief updated (if epic delivery)

### Freeze compliance
- [ ] No unauthorized edits to protected modules ([DSP_STATUS.md](DSP_STATUS.md) §Protected)
- [ ] Explicit unlock documented if frozen module touched

---

## 14. Related Documents

| Document | Purpose |
|---|---|
| [DSP_CODING_STANDARDS.md](DSP_CODING_STANDARDS.md) | Operational quick reference |
| [DSP_ARCHITECTURE.md](DSP_ARCHITECTURE.md) | Dependency matrices |
| [IMPLEMENTATION_QUALITY_GATE.md](IMPLEMENTATION_QUALITY_GATE.md) | Quality gate narrative |
| [USER_TRUST_STANDARD.md](USER_TRUST_STANDARD.md) | Trust requirements for outputs |
| [TYPING.md](TYPING.md) | mypy policy |
| [CI.md](CI.md) | CI pipeline and gates |
| [AI_PRINCIPLES.md](AI_PRINCIPLES.md) | AI behavior contract |
