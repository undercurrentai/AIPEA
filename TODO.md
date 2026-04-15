# TODO — AIPEA

Canonical tracker for all pending work. Replaces scattered items from ROADMAP.md,
NEXT_STEPS.md, KNOWN_ISSUES.md, SPECIFICATION.md, and discovery findings.

Last updated: 2026-04-15 (post-v1.6.0 release; 1217 tests, 93.39% coverage, 50 exports)

---

## Immediate (v1.3.x patch)

- [x] **README badge stale**: "698 passing" → "752 passing", "91.42%" → "91.79%" (fixed 2026-04-09)
- [x] ~~**Dead import**: remove unused `import subprocess as _sp` in `cli.py:348`~~ — NOT dead; used at lines 361 and 378
- [x] **ReDoS self-validation**: self-validate `INJECTION_PATTERNS` against `_is_regex_safe()` at `SecurityScanner.__init__` time
- [x] **Ollama stdout robustness**: defensive try-except around `ollama list` stdout parsing in `engine.py`

## Short-term (v1.4.0)

- [x] ~~**Adaptive Learning Engine**~~ — **DONE** (Wave D1, PR #31, 2026-04-13).
  `src/aipea/learning.py` + enhancer integration + 15 live tests (PR #32)
- [ ] **Missing `test_models.py`** — edge-case tests for `QueryAnalysis` dataclass (to_dict serialization, boundary values, None handling)
- [ ] **AEGIS adapter implementation** — spec complete at `docs/integration/aegis-adapter.md`; implement when AEGIS has a stable API
- [ ] **Exception chaining** — standardize `raise X from e` pattern in `engine.py` (currently bare `raise` in some exception handlers)
- [ ] **Governance templates** — populate `ai/system-register.yaml` and `ai/model-card.yaml` with real AIPEA values (currently placeholder/template)

## Medium-term (v1.5.0+)

- [ ] **Standalone Service Mode** — REST API wrapping the library (SPECIFICATION.md Section 8.4)
- [ ] **BDI Reasoning** (P4, conditional) — only if AIPEA evolves into an autonomous agent participating in multi-agent orchestration

## Declined (v2.0.0 removal scheduled)

- [x] ~~**FedRAMP enforcement**~~ — **declined 2026-04-11, Path B taken**. The config-only stub is deprecated in v1.3.4 and scheduled for hard removal in v2.0.0. No design partner, no enforcement budget, no honest path to an ATO. If a customer emerges this can be reopened as Path A. See [`docs/adr/ADR-002-fedramp-removal.md`](docs/adr/ADR-002-fedramp-removal.md).

## Completed (Waves A-C, 2026-04-11/12)

Consolidated response to two investor reviews (positive + adversarial) of
AIPEA v1.3.2. Full plan: `docs/ROADMAP.md` §P5. Detailed history:
`~/.claude/plans/reactive-growing-lark.md`.

- [x] **Wave A** (PRs #14, #20): v1.3.3 shipped to PyPI (13 security fixes
  incl. HIPAA compliance leak #96, ReDoS #107) + `SECURITY.md` added
- [x] **Wave B** (PR #21): adversarial review committed, README honesty
  sweep, CLAUDE.md header disambiguation, CONTRIBUTING.md expanded (~8 → ~130
  lines)
- [x] **Wave C1** (PRs #24, #26): triple-AI second-reviewer gate
  (gpt-5.4-pro + Codex gpt-5.3-codex + Claude Opus 4.6) +
  `.github/CODEOWNERS`. Dry-run 1 verified (graceful failure); dry-run 2
  verified (GPT PASS 9m13s, Codex PASS 2m53s, Claude FAIL credit balance —
  since topped up). Evidence in
  `docs/claude/audits/ai-second-review-dry-run-2026-04-11.md` §5
- [x] **Wave C2** (PR #22): FedRAMP deprecated via Path B +
  `docs/adr/ADR-002-fedramp-removal.md`
- [x] **Wave C3** (PR #23): `src/aipea/errors.py` (AIPEAError + 5
  subclasses), `cli.py` broad catches tightened, 23 regression tests
- [x] **Wave D1** (PR #31, 2026-04-13): Adaptive Learning Engine
  (`src/aipea/learning.py`). SQLite-backed strategy performance tracking,
  `EnhancementResult.strategy_used` field, `record_feedback()` API,
  `enable_learning` opt-in. 24 tests + 15 live tests (PR #32). Verdict
  enforcement added to AI second-reviewer gate (REQUEST_CHANGES blocks
  merge). All actions SHA-pinned.

## Deferred Bugs (from bug-hunt waves)

All deferred entries from waves 16-17 were resolved in **Wave 18 (2026-04-10)**,
and wave 19 closed out a further 13 findings with zero deferrals plus 4
ultrathink audit extensions. Full details in
[KNOWN_ISSUES.md](KNOWN_ISSUES.md) § "Wave 19 Fixes", § "Wave 19 Ultrathink
Audit Extensions", § "Wave 18 Fixes", and § "Intentional Design Decisions".

### Wave 19 — resolved (2026-04-10)

- [x] **#95** `patient_name` PHI regex IGNORECASE gotcha — FIXED (compile without flag, `(?i:patient)` inline group)
- [x] **#96** `_scan_search_results` compliance leak — FIXED (thread caller context; filter PHI/classified/PII per mode)
- [x] **#97** Uppercase Cyrillic homoglyph gap — FIXED (added U+0406, U+0405, U+0408, U+0458)
- [x] **#98** Formatter URL escaping bypass — FIXED (_escape_markdown/_escape_plaintext on URL field)
- [x] **#99** `save_dotenv` silent data loss on unreadable `.env` — FIXED (strict parse; raise on PermissionError)
- [x] **#100** `Firecrawl.deep_research` hardcoded URL — FIXED (derive from resolved search URL)
- [x] **#101** `formulate_search_aware_prompt` missed Gemma ids — FIXED (delegate to canonical `get_model_family`)
- [x] **#102** `_add_knowledge_sync` two-commit atomicity — FIXED (single transaction with rollback)
- [x] **#103** `enhance_for_models` empty-query guard — FIXED (short-circuit matching `enhance()`)
- [x] **#104** `_parse_dotenv` UTF-8 BOM — FIXED (`utf-8-sig` codec; TOML parser also updated)
- [x] **#105** `_score_density` discontinuous curve — FIXED (monotonic around delta=0)
- [x] **#106** `_init_db` narrow exception class — FIXED (widened to `sqlite3.Error`)
- [x] **#107** `_is_regex_safe` duplicate-alternative ReDoS — FIXED (heuristic + ultrathink extension for 3+ alternatives)

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
