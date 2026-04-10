# TODO — AIPEA

Canonical tracker for all pending work. Replaces scattered items from ROADMAP.md,
NEXT_STEPS.md, KNOWN_ISSUES.md, SPECIFICATION.md, and discovery findings.

Last updated: 2026-04-10 (Wave 18: 7 deferred bugs fixed, 1 reclassified as INTENTIONAL)

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

## Deferred Bugs (from bug-hunt waves)

All deferred entries from waves 16-17 were resolved in **Wave 18 (2026-04-10)**.
Full details in [KNOWN_ISSUES.md](KNOWN_ISSUES.md) § "Wave 18 Fixes" and
§ "Intentional Design Decisions".

### Wave 18 — resolved

- [x] **#90**: `enhance_for_models` per-model query-section format — FIXED (rebuild per model via `formulate_search_aware_prompt` with cached search context)
- [x] **#91**: `save_dotenv`/`save_toml_config` TOCTOU race — FIXED (atomic `tempfile.mkstemp` + `os.replace`; fsync for durability)
- [x] **#92**: `_test_exa/firecrawl_connectivity` ignore `cfg.*_api_url` — FIXED (added `api_url` parameter, honored by all 4 call sites)
- [x] **#79**: Exa score clamping — RECLASSIFIED AS INTENTIONAL (Exa neural scores are documented `[0, 1]` per https://docs.exa.ai/sdks/python-sdk-specification; normalization would destroy absolute semantics)
- [x] **#80**: Storage stats atomicity — FIXED (single-lock read of node_count + stat; try/except OSError)
- [x] **#81**: HTTP_TIMEOUT lazy resolution — FIXED (httpx call sites now call `_resolve_http_timeout()` at request time)
- [x] **#93**: `_score_clarity` whitespace guard — FIXED (early return 0.0 for whitespace-only enhanced prompts)
- [x] **#94**: `\uXXXX` decode on `.env` read — FIXED (`re.sub` pass in `_parse_dotenv` unescape block)

## Opportunities (nice-to-haves)

- [ ] Mutation testing (`make mut`) in CI
- [ ] Benchmark regression detection (`make perf`) in CI
- [ ] SBOM generation in `publish.yml`
- [x] ~~Dynamic coverage badge (Codecov/Coveralls) to replace static shield~~ — done 2026-04-09 via PR #9
- [ ] Float validation dedup — extract `_clamp_score()` helper
- [ ] `QueryRouter.route()` complexity reduction
- [ ] **v2.0 candidate**: review `PromptEngine.create_model_specific_prompt` for deprecation/removal. After Wave 18 #90 it has zero production callers in AIPEA, zero callers in AEGIS, and zero callers in Agora IV that import from `aipea.engine` (the 4 legacy-migrated test hits in AgoraIV reference the pre-extraction `pcw_prompt_engine` in-tree module, not AIPEA). Method still has 6 direct unit tests in `test_engine.py` that would need to be removed or migrated. Schedule against v2.0 breaking-changes window.

---

*See [docs/ROADMAP.md](docs/ROADMAP.md) for historical design rationale on P1-P4 features.*
