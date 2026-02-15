# ADR-001: Extract AIPEA from AgoraIV into Standalone Library

**Status**: Accepted
**Date**: 2026-02-14
**Deciders**: @joshuakirby, @agora-team

## Context

AIPEA (AI Prompt Engineer Agent) was originally designed as a comprehensive
preprocessing system in Agora V/AIPEA/ (9 files, ~8,200 LOC). A production subset
was built and shipped in AgoraIV as 6 modules (~4,700 LOC). The 3 core modules
(`aipea_security_context.py`, `aipea_offline_knowledge.py`, `aipea_search_providers.py`)
have **zero Agora dependencies** — they import only stdlib + httpx.

AEGIS and future products need prompt preprocessing capabilities. Copying the
modules into each consumer repo creates maintenance burden and divergence risk.

## Decision

Extract AIPEA into `/Projects/AIPEA/` as a standalone Python library (`pip install aipea`).

### Key decisions:

1. **Library, not service** — Ships as `pip install aipea`, not a standalone API server.
   Service mode is a future optional wrapper.

2. **Core modules extracted verbatim** — `security.py`, `knowledge.py`, `search.py`
   are copied as-is from AgoraIV since they have zero Agora dependencies.

3. **Facade generalized** — `AgoraPromptEnhancement` → `AIPEAEnhancer`, removing
   Agora-specific naming. The `enhance_for_agora()` convenience function stays in
   AgoraIV as an adapter.

4. **Consumer adapters live in consumer repos** — AgoraIV keeps a thin adapter
   wrapping `aipea.AIPEAEnhancer`. AEGIS will create its own adapter.

5. **pcw_* modules absorbed** — `pcw_query_analyzer.py` and `pcw_prompt_engine.py`
   are AIPEA modules that were named under the PCW namespace. They move into AIPEA
   as `analyzer.py` and `engine.py` with renamed classes.

## Consequences

### Positive
- Single source of truth for prompt preprocessing logic
- AEGIS and future products can import AIPEA without duplicating code
- Independent versioning and release cycle
- Tests run in isolation (faster CI for AIPEA changes)

### Negative
- AgoraIV needs adapter shims for backward compatibility
- Two repos to update when core AIPEA logic changes
- Version coordination between AIPEA and consumers

### Risks
- **Migration risk**: AgoraIV's 2,188 tests must pass after extraction. Mitigated
  by creating shim re-exports in `pcw_query_analyzer.py` and `pcw_prompt_engine.py`.
- **Dependency risk**: AIPEA adds a new pip dependency for consumers. Mitigated by
  AIPEA having minimal deps itself (stdlib + httpx).

## Alternatives Considered

1. **Keep in AgoraIV, copy to AEGIS** — Rejected due to divergence risk and
   maintenance burden.
2. **Extract as a git submodule** — Rejected due to complexity of submodule workflows.
3. **Extract as a standalone microservice** — Rejected as premature; library is simpler
   and faster (no network hop for preprocessing).
