# CLAUDE.md - AIPEA
> Version: 1.0.0 | Updated: 2026-02-14 | Owner: @agora-team

```yaml
version: 1.0.0
status: ACTIVE
compliance_tier: STANDARD
```

## 1. Purpose & Scope

### What This Directory Is

- **Primary Function**: AIPEA (AI Prompt Engineer Agent) — a standalone Python library for prompt preprocessing, security screening, query analysis, and context enrichment
- **Entry Points**:
  - Library: `from aipea import enhance`
  - Tests: `pytest tests/ -v`
- **Consumers**: Agora IV, AEGIS, future Undercurrent AI products

### What This Directory Is NOT

- An Agora-specific module (AIPEA is product-agnostic)
- A standalone service (it's a library; service mode is future)
- A replacement for LLM APIs (it preprocesses inputs TO LLMs)

## 2. Agent Contract

### Allowed Operations

- Read all `.py`, `.md`, `.yaml`, `.toml` files
- Run tests: `pytest tests/ -v`
- Execute formatting: `ruff format src/ tests/`
- Run linters: `ruff check src/ tests/`
- Type check: `mypy src/`
- Modify source in `src/aipea/` and `tests/`
- Update documentation in `docs/`

### Decision Matrix

| Condition | Action | Reason |
|-----------|--------|--------|
| Public API changes (`__init__.py`) | **ASK** | Breaking change risk |
| New external dependencies | **ASK** | Minimal deps is a design principle |
| Security module changes | **ASK** | Security audit required |
| Compliance mode changes | **ASK** | Regulatory implications |
| Adding tests | **PROCEED** | Always beneficial |
| Formatting fixes | **PROCEED** | Automated validation |
| Secrets in code | **REFUSE** | Security policy |
| GPL dependencies | **REFUSE** | License incompatibility |

## 3. Standards

### Language & Formatting

- **Python**: 3.12+ required
- **Formatter**: Ruff (line-length: 100)
- **Linter**: Ruff strict mode
- **Type Checker**: mypy strict mode
- **Import Order**: stdlib > third-party > first-party (`aipea.*`)

### Testing

- **Framework**: pytest + pytest-asyncio
- **Minimum Coverage**: 75%
- **Markers**: `@pytest.mark.unit`, `@pytest.mark.integration`
- **Run**: `pytest tests/ -v --cov=src/aipea`

### Dependencies

- **Core**: stdlib + httpx (ONLY)
- **Dev**: pytest, pytest-asyncio, pytest-cov, ruff, mypy
- **Optional**: None currently

## 4. Key Architecture

### Module Dependency Graph

```
security.py    ← ZERO aipea imports (stdlib only)
knowledge.py   ← ZERO aipea imports (stdlib only)
search.py      ← ZERO aipea imports (stdlib + httpx)
_types.py      ← Shared enums
models.py      ← Shared data models
analyzer.py    ← imports security, _types
engine.py      ← imports search, _types
enhancer.py    ← imports ALL (facade)
```

### Design Principles

1. Zero external deps in core modules (security, knowledge, search)
2. Graceful degradation (search failures → empty results, never exceptions)
3. Security by default (injection always blocked, PII always scanned)
4. Model-agnostic (formatting is output concern, not architecture)

## 5. Commands

| Action | Command |
|--------|---------|
| Install | `pip install -e ".[dev]"` |
| Test | `pytest tests/ -v` |
| Coverage | `pytest tests/ --cov=src/aipea --cov-report=term-missing` |
| Format | `ruff format src/ tests/` |
| Lint | `ruff check src/ tests/` |
| Type check | `mypy src/aipea/` |

## 6. References

| Document | Purpose |
|----------|---------|
| `SPECIFICATION.md` | Full AIPEA specification |
| `docs/adr/ADR-001-extraction.md` | Extraction decision record |
| `docs/design-reference/` | Original Agora V design files |
| `docs/integration/agora-adapter.md` | Agora integration guide |
| `docs/integration/aegis-adapter.md` | AEGIS integration guide |

---

*AIPEA Agent Contract v1.0.0*
