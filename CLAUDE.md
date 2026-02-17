# CLAUDE.md - AIPEA
> Version: 3.0.0 | Updated: 2026-02-16 | Owner: @joshuakirby

```yaml
version: 3.0.0
status: ACTIVE
tier: 2  # Standard (~6K LOC, 2 contributors, internal consumers)
compliance_tier: STANDARD
inherits_from: ../../CLAUDE.md  # Undercurrent Holdings root
maintainer: joshuakirby
last_audit: 2026-02-16
protocol: v4.0
token_budget: 8000
```

---

## 0. Quick Reference

| Dimension | Value |
|-----------|-------|
| **Project type** | Standalone Python library |
| **Entry point** | `from aipea import enhance_prompt, AIPEAEnhancer` |
| **Core deps** | stdlib + httpx (ONLY) |
| **Python** | >=3.11 (target 3.12) |
| **CI matrix** | Python 3.11 + 3.12 |
| **Coverage floor** | 75% |
| **License** | MIT |
| **Source LOC** | ~6,311 |
| **Exports** | 30 symbols in `__all__` |
| **Quick commands** | `make all` (local) / `make ci` (CI parity) |

---

## 1. Purpose & Scope

### 1.1 What This Directory Is

- **Primary Function**: AIPEA (AI Prompt Engineer Agent) — a standalone Python library for prompt preprocessing, security screening, query analysis, and context enrichment
- **Entry Points**:
  - Library: `from aipea import enhance_prompt, AIPEAEnhancer`
  - Tests: `pytest tests/ -v`
- **Consumers**: Agora IV, AEGIS, future Undercurrent AI products
- **License**: MIT

### 1.2 What This Directory Is NOT

- An Agora-specific module (AIPEA is product-agnostic)
- A standalone service (it's a library; service mode is future)
- A replacement for LLM APIs (it preprocesses inputs TO LLMs)
- An AI-governed system (no model cards or governance artifacts — those live in Libertas-Core)

### 1.3 Out-of-Scope Operations

| Operation | Reason | Where to Do It |
|-----------|--------|----------------|
| Deployment | Library, not a service | Consumer's CI/CD |
| Infrastructure changes | No infra in this project | Libertas-Core |
| AI governance artifacts | STANDARD tier, not AI-GOVERNED | Libertas-Core |

### 1.4 Hierarchy Context

This CLAUDE.md inherits from the Undercurrent Holdings root (`../../CLAUDE.md`).

**Inherited policies** (do not duplicate — refer to parent):
- Reality-First Principle (evidence-backed claims)
- Secret handling (prohibited locations, detection action)
- Evidence requirements (test output, file paths)
- Cross-project coordination gates

**AIPEA-specific overrides**: None. All parent policies apply as-is.

---

## 2. Agent Contract

### 2.1 Allowed Operations

| Operation | Scope | Notes |
|-----------|-------|-------|
| Read any file | All directories | Normal operation |
| Run tests / lint / type check | `make test`, `make lint`, `make type` | Safe, read-only effect |
| Run formatter | `make fmt` | Auto-fix safe |
| Run security scan | `make sec` | Read-only check |
| Modify source | `src/aipea/`, `tests/` | Core development |
| Add tests | `tests/` | Always beneficial |
| Update docs | `docs/` | Documentation updates |

### 2.2 Ask-First Triggers

| Trigger | Reason |
|---------|--------|
| Public API changes (`__init__.py`, `__all__`) | Breaking change risk for consumers |
| New external dependencies in `pyproject.toml` | Minimal-deps design principle |
| Security module changes (`security.py`) | Security audit required |
| Compliance mode or CI workflow changes | Regulatory/gate integrity |
| `pyproject.toml` tool config changes (ruff, mypy) | May break CI gates |
| Modifying `CLAUDE.md` or `SPECIFICATION.md` | Navigation/canonical integrity |
| PyPI release or version bump | Requires release approval |
| Changes to `.github/workflows/publish.yml` | Release pipeline integrity |

### 2.3 Hard Stops

Inherited from parent: secrets in code, force push to main.

| Action | Reason |
|--------|--------|
| Add GPL/LGPL dependencies | License incompatibility (MIT project) |
| Add external deps to core modules (`security.py`, `knowledge.py`, `search.py`) | Zero-external-deps design principle |
| Bypass pre-commit gates (`--no-verify`) | Protocol integrity |
| Delete files without backup confirmation | Data loss prevention |

---

## 3. Standards

### 3.1 Language & Formatting

- **Python**: >=3.11 (target 3.12, CI tests both)
- **Formatter**: Ruff (line-length: 100, target: py312)
- **Linter**: Ruff with rules: E, W, F, I, N, UP, B, S, C90, T20, DTZ, ICN, SIM, RUF
- **Type Checker**: mypy strict mode (`strict = true`)
- **Import Order**: stdlib > third-party > first-party (`aipea.*`)

### 3.2 Testing

- **Framework**: pytest + pytest-asyncio (asyncio_mode = auto)
- **Minimum Coverage**: 75% (`--cov-fail-under=75`)
- **Markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- **Run**: `make test`

### 3.3 Dependencies

- **Core**: stdlib + httpx (ONLY — this is a hard constraint)
- **Dev**: pytest, pytest-asyncio, pytest-cov, ruff, mypy
- **Principle**: Zero external deps in core modules (`security.py`, `knowledge.py`, `search.py`)

### 3.4 Commit & Branch Conventions

- **Branch format**: `<type>/<short-description>` (e.g., `feat/quality-assessor`, `fix/scan-redos`)
- **Commit style**: Conventional Commits (`feat:`, `fix:`, `test:`, `chore:`, `docs:`)
- **Scope**: Use `(module)` when touching a single module (e.g., `fix(security): handle empty patterns`)

---

## 4. Key Architecture

### Module Dependency Graph

```
security.py    <- ZERO aipea imports (stdlib only)
knowledge.py   <- ZERO aipea imports (stdlib only)
search.py      <- ZERO aipea imports (stdlib + httpx)
_types.py      <- Shared enums (ProcessingTier, QueryType, SearchStrategy)
models.py      <- Shared data models (QueryAnalysis)
analyzer.py    <- imports security, _types, models
engine.py      <- imports search, _types
enhancer.py    <- imports ALL (facade)
```

### Design Principles

1. **Zero external deps in core** — security, knowledge, search import only stdlib + httpx
2. **Graceful degradation** — search failures return empty results, never exceptions
3. **Security by default** — injection always blocked, PII always scanned
4. **Model-agnostic** — formatting is an output concern, not an architectural dependency

---

## 5. Tooling & Commands

### 5.1 Local Development

| Action | Command | Notes |
|--------|---------|-------|
| Install (dev) | `make install` | `pip install -e ".[dev]"` |
| Format + autofix | `make fmt` | `ruff format` + `ruff check --fix` |
| Lint (check only) | `make lint` | `ruff check` + `ruff format --check` |
| Type check | `make type` | `mypy src/aipea/` |
| Test + coverage | `make test` | pytest with `--cov-fail-under=75` |
| Security scan | `make sec` | `ruff check --select S` (bandit rules) |
| All (local) | `make all` | fmt + lint + type + test |
| CI parity | `make ci` | lint + type + test (no autofix) |

### 5.2 CI Gates (`.github/workflows/ci.yml`)

| Job | Python | Steps |
|-----|--------|-------|
| `lint` | 3.12 | ruff check + ruff format --check |
| `typecheck` | 3.12 | mypy src/aipea/ |
| `test` | 3.11, 3.12 (matrix) | pytest --cov-fail-under=75 |

### 5.3 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EXA_API_KEY` | (none) | Exa search provider API key |
| `FIRECRAWL_API_KEY` | (none) | Firecrawl provider API key |
| `AIPEA_HTTP_TIMEOUT` | `30.0` | HTTP timeout for search providers (seconds) |

### 5.4 Research & Documentation Tools

Before using or modifying code that depends on external libraries, verify current API patterns:

| Trigger | Tool | Example Query |
|---------|------|---------------|
| httpx client usage or config changes | Context7 | `resolve-library-id: "encode/httpx"` |
| pytest fixture or async test patterns | Context7 | `resolve-library-id: "pytest-dev/pytest"` |
| ruff rule selection or config changes | Context7 | `resolve-library-id: "astral-sh/ruff"` |
| Python packaging best practices (2025/2026) | Exa | `"Python hatchling PyPI trusted publisher"` |
| Security scanning for prompt injection | Exa | `"LLM prompt injection detection patterns"` |
| LLM preprocessing library design | Exa | `"prompt preprocessing library architecture"` |

---

## 6. Playbooks

### 6.1 Add/Modify Feature

1. Read SPECIFICATION.md for architectural context
2. Identify affected modules using dependency graph (Section 4)
3. Write/update tests FIRST (test-driven)
4. Implement changes in source module
5. If public API changes → **ASK** before modifying `__init__.py`
6. Run `make all` (fmt + lint + type + test)
7. Verify coverage >= 75%

### 6.2 Bug Fix

1. Write a failing test that reproduces the bug
2. Fix the bug in the minimal scope
3. Run `make ci` to verify no regressions
4. If fix touches `security.py` → **ASK** (security audit required)

### 6.3 Add/Extend Tests

1. Place tests in `tests/` matching source structure
2. Use appropriate markers (`@pytest.mark.unit`, `.integration`, `.slow`)
3. Use pytest-asyncio for async tests (asyncio_mode = auto)
4. Run `make test` to verify coverage floor
5. PROCEED without asking (tests are always beneficial)

### 6.4 Dependency Update

1. **ASK** before adding ANY new dependency
2. Verify license compatibility (must be MIT-compatible, never GPL/LGPL)
3. Core modules (`security`, `knowledge`, `search`) must NOT gain new deps
4. Update `pyproject.toml`
5. Run `make ci` to verify compatibility
6. Update CLAUDE.md Section 3.3 if dep list changes

### 6.5 Release to PyPI

1. **ASK** user for version bump type (major/minor/patch)
2. Verify all quality gates pass: `make ci`
3. Update version in `pyproject.toml` and `src/aipea/__init__.py` (`__version__`)
4. Update `CHANGELOG.md` with release notes (Keep a Changelog format)
5. Commit: `chore(release): bump version to vX.Y.Z`
6. Push to main, verify CI passes
7. Create GitHub Release via UI or `gh release create vX.Y.Z --title "vX.Y.Z" --notes "..."`
8. `.github/workflows/publish.yml` triggers automatically on release
9. Verify: `pip install aipea==X.Y.Z` from PyPI

**One-time setup** (not yet done):
- Create PyPI account at pypi.org
- Register package name with initial manual upload: `hatch build && hatch publish`
- Configure Trusted Publisher on PyPI: Settings > Publishing > Add GitHub Actions
  - Owner: `undercurrentai`, Repository: `AIPEA`, Workflow: `publish.yml`, Environment: `release`
- Create GitHub Environment `release` with protection rules (optional: require approval)

---

## 7. Security & Compliance Guardrails

### 7.1 Secret Handling

Inherits parent policy (see root `CLAUDE.md` Section 6.1).

**AIPEA-specific runtime secrets** (allowed via environment variables only):
- `EXA_API_KEY` — Exa search provider
- `FIRECRAWL_API_KEY` — Firecrawl provider

**Additional prohibited location**: Test fixtures (use mock values only)

### 7.2 Compliance Modes

AIPEA supports 4 compliance modes. Changes to compliance behavior require ASK-first approval:

| Mode | Description | Restrictions |
|------|-------------|-------------|
| GENERAL | Standard use | None (except global forbidden models) |
| HIPAA | Medical/PHI | BAA-covered models only, PHI redaction |
| TACTICAL | Military/Defense | Local models only, force offline |
| FEDRAMP | Government cloud | FedRAMP-authorized models only |

### 7.3 Third-Party Licensing

| License | Status |
|---------|--------|
| MIT, BSD, Apache 2.0, ISC | Compatible |
| GPL, LGPL, AGPL | **REFUSE** — incompatible with MIT |
| Proprietary/Unknown | **ASK** before adding |

---

## 8. Quality Gates

| Gate | Stage | Command | Python | Bypass? |
|------|-------|---------|--------|---------|
| Lint clean | Local + CI | `make lint` / `ruff check` | 3.12 | User override only |
| Format clean | Local + CI | (included in lint) | 3.12 | User override only |
| Type check | Local + CI | `make type` / `mypy src/aipea/` | 3.12 | User override only |
| Tests pass | Local + CI | `make test` / `pytest` | 3.11, 3.12 | User override only |
| Coverage >= 75% | Local + CI | (included in test) | 3.11, 3.12 | User override only |
| No secrets in diff | Local | Manual review | — | NEVER |
| Quality gate (publish) | CI | Full lint + type + test matrix | 3.11, 3.12 | NEVER (blocks PyPI) |

---

## 9. Ask-First / Refusal Matrix

| Action | Response | Rationale |
|--------|----------|-----------|
| Read any project file | **PROCEED** | Normal operation |
| Run tests / lint / type check | **PROCEED** | Safe, read-only effect |
| Add tests | **PROCEED** | Always beneficial |
| Format fixes | **PROCEED** | Automated, reversible |
| Modify source in `src/aipea/` | **PROCEED** | Core development |
| Modify `__init__.py` exports | **ASK** | Breaking change risk |
| Add external dependency | **ASK** | Minimal-deps principle |
| Modify `security.py` | **ASK** | Security audit required |
| Modify compliance behavior | **ASK** | Regulatory implications |
| Change `pyproject.toml` tool config | **ASK** | May break CI |
| Modify CI/publish workflow | **ASK** | Gate/release integrity |
| Modify `CLAUDE.md` or `SPECIFICATION.md` | **ASK** | Navigation/canonical integrity |
| PyPI release or version bump | **ASK** | Requires release approval |
| Commit secrets or API keys | **REFUSE** | Security policy |
| Add GPL/LGPL dependency | **REFUSE** | License incompatibility |
| Add deps to core modules | **REFUSE** | Zero-deps design principle |
| Force push to main | **REFUSE** | Destructive operation |
| Bypass quality gates | **REFUSE** | Protocol integrity |

---

## 10. Context Management

### Subagent Delegation

| Scenario | Agent | Rationale |
|----------|-------|-----------|
| Broad search across multiple modules | Explore | Cross-module data flow tracing |
| Single-file reads or targeted grep | Direct tools | Faster, lower overhead |
| Running make targets | Bash | Direct execution |
| Multi-file refactor verification | Explore | Post-refactor consistency check |

### Token Budget Awareness

- **Tier 2 ceiling**: 8,000 tokens for this CLAUDE.md
- **Compression**: If context exceeds 70%, switch to concise mode (symbols: →, ✓, ✗)
- **Context clearing**: After completing a multi-file refactor or when switching between unrelated modules

---

## 11. Change Management

### Version Semantics

| Bump | When |
|------|------|
| Major (X.0.0) | Breaking public API change, new compliance mode, architecture restructure |
| Minor (x.Y.0) | New module, new playbook, CI workflow additions |
| Patch (x.y.Z) | Typo fixes, metric updates, audit-only changes |

### Update Triggers

- New module added to `src/aipea/`
- Public API changes (`__init__.py`)
- CI/publish workflow changes
- New compliance mode added
- Dependency changes
- Audit findings

### Change Process

1. Document proposed change
2. Get user approval (**ASK**)
3. Apply change
4. Update version block
5. Update audit packet if scope warrants

### Early Audit Triggers

Audit before quarterly schedule if:
- Security module (`security.py`) is modified
- Compliance mode added or changed
- Public API surface changes significantly (>3 exports)
- New CI/CD workflow added

**Audit schedule**: Quarterly (next: 2026-05-16)

---

## 12. References

| Document | Purpose |
|----------|---------|
| `../../CLAUDE.md` | Parent CLAUDE.md (Undercurrent Holdings root) |
| `SPECIFICATION.md` | Full AIPEA specification (canonical architecture) |
| `docs/adr/ADR-001-extraction.md` | Extraction decision record |
| `docs/design-reference/` | Original Agora V design files (9 files, ~7.9K LOC) |
| `docs/integration/agora-adapter.md` | Agora integration guide |
| `docs/integration/aegis-adapter.md` | AEGIS integration guide |
| `docs/claude/audits/aipea.md` | Audit packet (v4.0 protocol) |

---

*AIPEA Agent Contract v3.0.0 | Protocol v4.0 | Tier 2 (Standard)*
