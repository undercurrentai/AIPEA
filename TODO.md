# TODO — AIPEA

Canonical tracker for all pending work. Replaces scattered items from ROADMAP.md,
NEXT_STEPS.md, KNOWN_ISSUES.md, SPECIFICATION.md, and discovery findings.

Last updated: 2026-04-09

---

## Immediate (v1.3.2 patch)

- [x] **README badge stale**: "698 passing" → "752 passing", "91.42%" → "91.79%" (fixed 2026-04-09)
- [x] ~~**Dead import**: remove unused `import subprocess as _sp` in `cli.py:348`~~ — NOT dead; used at lines 361 and 378
- [ ] **ReDoS self-validation**: self-validate `INJECTION_PATTERNS` against `_is_regex_safe()` at `SecurityScanner.__init__` time
- [ ] **Ollama stdout robustness**: defensive try-except around `ollama list` stdout parsing in `engine.py`

## Short-term (v1.4.0)

- [ ] **Adaptive Learning Engine** — learn from user feedback to improve enhancement quality over time (P3b from ROADMAP.md; origin: `aipea-offline-knowledge.py` AdaptiveLearningEngine class)
- [ ] **Missing `test_models.py`** — edge-case tests for `QueryAnalysis` dataclass (to_dict serialization, boundary values, None handling)
- [ ] **AEGIS adapter implementation** — spec complete at `docs/integration/aegis-adapter.md`; implement when AEGIS has a stable API
- [ ] **Exception chaining** — standardize `raise X from e` pattern in `engine.py` (currently bare `raise` in some exception handlers)
- [ ] **Governance templates** — populate `ai/system-register.yaml` and `ai/model-card.yaml` with real AIPEA values (currently placeholder/template)

## Medium-term (v1.5.0+)

- [ ] **Standalone Service Mode** — REST API wrapping the library (SPECIFICATION.md Section 8.4)
- [ ] **FedRAMP enforcement** — beyond config stub; actual enforcement logic in `security.py:611-626` (README notes "planned")
- [ ] **BDI Reasoning** (P4, conditional) — only if AIPEA evolves into an autonomous agent participating in multi-agent orchestration

## Deferred Bugs (LOW severity)

All LOW severity with no functional impact. Full details in [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

- [ ] **#79**: Exa score clamping vs normalization (`search.py:583-589`) — clamping works; normalization would require collecting all scores first
- [ ] **#80**: Storage stats atomicity (`knowledge.py:884-896`) — stats are informational only
- [ ] **#81**: HTTP_TIMEOUT eager vs URL lazy resolution inconsistency (`search.py:113`) — timeout frozen at import time is documented behavior

## Opportunities (nice-to-haves)

- [ ] Mutation testing (`make mut`) in CI
- [ ] Benchmark regression detection (`make perf`) in CI
- [ ] SBOM generation in `publish.yml`
- [ ] Dynamic coverage badge (Codecov/Coveralls) to replace static shield
- [ ] Float validation dedup — extract `_clamp_score()` helper
- [ ] `QueryRouter.route()` complexity reduction

---

*See [docs/ROADMAP.md](docs/ROADMAP.md) for historical design rationale on P1-P4 features.*
