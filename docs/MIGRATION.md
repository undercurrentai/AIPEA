# Migration Guide

> Status: **v0 (draft)** — finalized at v2.0.0rc1 (target 2026-09-01).
> Tracks every deprecated symbol scheduled for removal so consumers (Agora IV,
> AEGIS, future products) can migrate ahead of the breaking release.

AIPEA follows [SemVer](https://semver.org/). Deprecated APIs emit a
`DeprecationWarning` for at least one minor release before removal in the next
major. This guide lists each scheduled removal, the replacement, and the
timeline.

---

## Removals scheduled for v2.0.0 (target 2026-10-22; rc1 2026-09-01)

| Symbol | Deprecated in | Removed in | Replacement |
|--------|---------------|------------|-------------|
| `ComplianceMode.FEDRAMP` | v1.3.4 | v2.0.0 | `ComplianceMode.GENERAL` + your own controls |
| `HTTP_TIMEOUT` module alias | v1.6.2 | v2.0.0 | `AIPEA_HTTP_TIMEOUT` env var / `AIPEAConfig.http_timeout` |
| `PromptEngine.create_model_specific_prompt()` | v1.7.0 | v2.0.0 | `AIPEAEnhancer.enhance_for_models()` or `formulate_search_aware_prompt()` |
| `TierProcessor` ABC (internal) | — (v2.0.0rc1) | v2.0.0 | Inlined; no public replacement (zero external refs) |

---

### 1. `ComplianceMode.FEDRAMP` → `ComplianceMode.GENERAL`

**Why**: FEDRAMP was a config-only stub with **no behavioral enforcement** —
it never implemented data-residency checks, FedRAMP-authorized-provider
validation, FIPS 140-2 verification, or continuous monitoring. Keeping a mode
that implies controls it does not enforce is a compliance hazard. See
[`docs/adr/ADR-002-fedramp-removal.md`](adr/ADR-002-fedramp-removal.md).

**Before**
```python
handler = ComplianceHandler(ComplianceMode.FEDRAMP)  # DeprecationWarning since v1.3.4
```
**After**
```python
handler = ComplianceHandler(ComplianceMode.GENERAL)
# Layer FedRAMP controls (residency, authorized providers, FIPS, monitoring)
# in your own application/infrastructure layer — AIPEA does not implement them.
```

### 2. `HTTP_TIMEOUT` alias → `AIPEA_HTTP_TIMEOUT`

**Why**: the bare `HTTP_TIMEOUT` module-level alias was ambiguous and resolved
eagerly at import; the env-var / config form resolves lazily at request time
(per PR #51 / wave-18). Accessing `aipea.search.HTTP_TIMEOUT` emits a
`DeprecationWarning` (PEP 562 `__getattr__`).

**Before**
```python
from aipea.search import HTTP_TIMEOUT  # DeprecationWarning since v1.6.2
```
**After**
```python
import os
os.environ["AIPEA_HTTP_TIMEOUT"] = "30.0"   # or set in .env / config.toml
# resolved per-request; also readable via AIPEAConfig.http_timeout
```

### 3. `create_model_specific_prompt()` → `enhance_for_models()` / `formulate_search_aware_prompt()`

**Why**: `PromptEngine.create_model_specific_prompt()` only wraps an
already-built base prompt with a per-model search-context block. It is **not**
the canonical multi-model path: `AIPEAEnhancer.enhance_for_models()` rebuilds
each model's *full* prompt (including the query section) in the model-preferred
format (`## Query` / `<query>…</query>` / `Query:\n1. …`). Emits a
`DeprecationWarning` since v1.7.0.

**Before**
```python
prompt = await engine.create_model_specific_prompt(base_prompt, "claude-4", ctx)
```
**After**
```python
# Canonical multi-model path (rebuilds each model's full prompt):
prompts = await enhancer.enhance_for_models(query, models=["gpt-4", "claude-4"])

# Or, if you only need per-model search-context formatting on a finished prompt:
prompt = engine.formulate_search_aware_prompt(base_prompt, "claude-4", ctx)
```

### 4. `TierProcessor` ABC (internal) — inlining

**Why**: the `TierProcessor` abstract base (~68 LOC) has zero external
references; its concrete tiers will be inlined at v2.0.0. No public replacement
is needed — it was never part of the public API (`__all__`).

---

## Removals under consideration (not yet scheduled)

- `phi_redaction_enabled` handler flag — the Phase 4.b claims audit (PR #69)
  found it set but unused. Pending confirmation; may be removed at v2.0.0.

---

*Questions or a migration not covered here? Open an issue. This guide is updated
as new deprecations land and finalized at v2.0.0rc1.*
