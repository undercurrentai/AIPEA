# CLAUDE.md - AIPEA
> Version: 2.0.0 | Updated: 2026-02-14 | Owner: @joshuakirby

```yaml
version: 2.0.0
status: ACTIVE
compliance_tier: STANDARD
last_audit: 2026-02-14
```

---

## 1. Purpose & Scope

### What This Directory Is

- **Primary Function**: AIPEA (AI Prompt Engineer Agent) — a standalone Python library for prompt preprocessing, security screening, query analysis, and context enrichment
- **Entry Points**:
  - Library: `from aipea import enhance_prompt, AIPEAEnhancer`
  - Tests: `pytest tests/ -v`
- **Consumers**: Agora IV, AEGIS, future Undercurrent AI products
- **License**: MIT

### What This Directory Is NOT

- An Agora-specific module (AIPEA is product-agnostic)
- A standalone service (it's a library; service mode is future)
- A replacement for LLM APIs (it preprocesses inputs TO LLMs)
- An AI-governed system (no model cards or governance artifacts — those live in Libertas-Core)

---

## 2. Agent Contract

### 2.1 Allowed Operations

| Operation | Scope | Notes |
|-----------|-------|-------|
| Read any file | All directories | Normal operation |
| Run tests | `make test` or `pytest tests/ -v` | Safe, read-only effect |
| Run formatter | `make fmt` | Auto-fix safe |
| Run linter | `make lint` | Read-only check |
| Run type checker | `make type` | Read-only check |
| Run security scan | `make sec` | Read-only check |
| Modify source | `src/aipea/`, `tests/` | Core development |
| Update docs | `docs/` | Documentation updates |

### 2.2 Out-of-Scope Operations

| Operation | Reason | Where to Do It |
|-----------|--------|----------------|
| Deployment | Library, not a service | Consumer's CI/CD |
| Infrastructure changes | No infra in this project | Libertas-Core |
| AI governance artifacts | STANDARD tier, not AI-GOVERNED | Libertas-Core |
| PyPI publishing | Requires release approval | Manual process |

### 2.3 Ask-First Triggers

| Trigger | Reason |
|---------|--------|
| Public API changes (`__init__.py`, `__all__`) | Breaking change risk for consumers |
| New external dependencies in `pyproject.toml` | Minimal-deps is a design principle |
| Security module changes (`security.py`) | Security audit required |
| Compliance mode changes | Regulatory implications |
| `pyproject.toml` tool config changes (ruff, mypy) | May break CI gates |
| Modifying `CLAUDE.md` | Navigation integrity |
| Changes to `SPECIFICATION.md` | Canonical architecture reference |
| Modifying CI workflow (`.github/workflows/ci.yml`) | Gate integrity |

### 2.4 Hard Stops

| Action | Reason |
|--------|--------|
| Commit secrets or API keys | Security policy violation |
| Add GPL/LGPL dependencies | License incompatibility (MIT project) |
| Delete files without backup confirmation | Data loss prevention |
| Force push to main | Destructive operation |
| Bypass pre-commit gates (`--no-verify`) | Protocol integrity |
| Add external deps to core modules (`security.py`, `knowledge.py`, `search.py`) | Zero-external-deps design principle |

---

## 3. Standards

### 3.1 Language & Formatting

- **Python**: >=3.11 (target 3.12, CI tests both)
- **Formatter**: Ruff (line-length: 100, target: py312)
- **Linter**: Ruff with rules: E, W, F, I, N, UP, B, S, T20, SIM, RUF
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

**Implemented** (read by source code):

| Variable | Default | Description |
|----------|---------|-------------|
| `EXA_API_KEY` | (none) | Exa search provider API key |
| `FIRECRAWL_API_KEY` | (none) | Firecrawl provider API key |
| `AIPEA_HTTP_TIMEOUT` | `30.0` | HTTP timeout for search providers (seconds) |

**Specified but not yet implemented** (defined in SPECIFICATION.md Section 8.1):

| Variable | Default | Description |
|----------|---------|-------------|
| `AIPEA_DB_PATH` | `aipea_knowledge.db` | Path to offline knowledge SQLite database |
| `AIPEA_STORAGE_TIER` | `standard` | Storage tier: ultra_compact, compact, standard, extended |
| `AIPEA_DEFAULT_COMPLIANCE` | `general` | Default compliance mode |
| `AIPEA_OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL for offline models |

---

## 5.5 Research & Documentation Tools (MANDATORY)

### Library Documentation Freshness

Before using or modifying code that depends on httpx, pytest, ruff, or mypy, verify current API patterns:

```yaml
context7_triggers:
  - httpx client usage or configuration changes
  - pytest fixture patterns or async test patterns
  - ruff rule selection or configuration changes
  - mypy strict mode configuration
```

### Research Protocol

When investigating best practices, recent changes, or validating patterns:

```yaml
exa_triggers:
  - Python library packaging best practices (2025/2026)
  - Security scanning patterns for prompt injection
  - LLM preprocessing library design patterns
  - Dependency minimization strategies
```

---

## 6. Playbooks

### 6.1 Add/Modify Feature

```yaml
steps:
  1. Read SPECIFICATION.md for architectural context
  2. Identify affected modules using dependency graph (Section 4)
  3. Write/update tests FIRST (test-driven)
  4. Implement changes in source module
  5. If public API changes -> ASK before modifying __init__.py
  6. Run `make all` (fmt + lint + type + test)
  7. Verify coverage >= 75%
```

### 6.2 Bug Fix

```yaml
steps:
  1. Write a failing test that reproduces the bug
  2. Fix the bug in the minimal scope
  3. Run `make ci` to verify no regressions
  4. If fix touches security.py -> ASK (security audit required)
```

### 6.3 Add/Extend Tests

```yaml
steps:
  1. Place tests in tests/ matching source structure
  2. Use appropriate markers (@pytest.mark.unit, .integration, .slow)
  3. Use pytest-asyncio for async tests (asyncio_mode = auto)
  4. Run `make test` to verify coverage floor
  5. PROCEED without asking (tests are always beneficial)
```

### 6.4 Dependency Update

```yaml
steps:
  1. ASK before adding ANY new dependency
  2. Verify license compatibility (must be MIT-compatible, never GPL/LGPL)
  3. Core modules (security, knowledge, search) must NOT gain new deps
  4. Update pyproject.toml
  5. Run `make ci` to verify compatibility
  6. Update CLAUDE.md Section 3.3 if dep list changes
```

---

## 7. Security & Compliance Guardrails

### 7.1 Secret Handling

```yaml
secrets_policy:
  prohibited_locations:
    - ANY file in repository
    - CLAUDE.md files
    - Commit messages
    - Code comments
    - Test fixtures (use mock values only)

  allowed_at_runtime:
    - Environment variables (EXA_API_KEY, FIRECRAWL_API_KEY)

  detection_action: "STOP immediately, notify user, do NOT commit"
```

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

### 8.1 Pre-Commit (Local)

All must pass before committing:

| Gate | Command | Bypass? |
|------|---------|---------|
| Lint clean | `make lint` | User override only |
| Format clean | (included in `make lint`) | User override only |
| Type check clean | `make type` | User override only |
| Tests pass | `make test` | User override only |
| Coverage >= 75% | (included in `make test`) | User override only |
| No secrets in diff | Manual review | NEVER |

### 8.2 CI (GitHub Actions)

| Gate | Matrix | Failure = Block? |
|------|--------|-----------------|
| Ruff lint + format | Python 3.12 | Yes |
| Mypy strict | Python 3.12 | Yes |
| Pytest + coverage | Python 3.11, 3.12 | Yes |

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
| Modify CI workflow | **ASK** | Gate integrity |
| Modify `CLAUDE.md` | **ASK** | Navigation integrity |
| Modify `SPECIFICATION.md` | **ASK** | Canonical reference |
| Commit secrets or API keys | **REFUSE** | Security policy |
| Add GPL/LGPL dependency | **REFUSE** | License incompatibility |
| Add deps to core modules | **REFUSE** | Zero-deps design principle |
| Force push to main | **REFUSE** | Destructive operation |
| Bypass quality gates | **REFUSE** | Protocol integrity |

---

## 10. Context Management

```yaml
subagent_guidance:
  use_explore_agent:
    - Broad codebase searches across multiple modules
    - Tracing data flow through analyzer -> engine -> enhancer
  use_direct_tools:
    - Single-file reads or targeted grep
    - Running make targets
  context_clearing:
    - After completing a multi-file refactor
    - When switching between unrelated modules
```

---

## 11. Change Management

```yaml
version: 2.0.0
owners:
  - joshuakirby
update_triggers:
  - New module added to src/aipea/
  - Public API changes (__init__.py)
  - CI workflow changes
  - New compliance mode added
  - Dependency changes
  - Audit findings

change_process:
  1. Document proposed change
  2. Get user approval (ASK)
  3. Apply change
  4. Update version block
  5. Update audit packet if scope warrants

audit_schedule: Quarterly (next: 2026-05-14)
```

---

## 12. References

| Document | Purpose |
|----------|---------|
| `SPECIFICATION.md` | Full AIPEA specification (canonical architecture) |
| `docs/adr/ADR-001-extraction.md` | Extraction decision record |
| `docs/design-reference/` | Original Agora V design files (9 files, ~7.6K LOC) |
| `docs/integration/agora-adapter.md` | Agora integration guide |
| `docs/integration/aegis-adapter.md` | AEGIS integration guide |
| `docs/claude/audits/aipea.md` | Audit packet for this CLAUDE.md |

---

*AIPEA Agent Contract v2.0.0*
