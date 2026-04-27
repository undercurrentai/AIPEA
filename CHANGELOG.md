# Changelog

All notable changes to AIPEA will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Wave-21 (D4-B): paraphrase-verb tier 2 injection patterns** in
  `src/aipea/security.py`. Two new entries appended to
  `INJECTION_PATTERNS` (now 12 total, up from 10):
  - **P4 strong-cue paraphrase**: matches `bypass|reset|cancel|nullify|
    revoke|terminate` + (1-3 cue tokens) + `instructions`. Mirrors the
    shape of the v1.6.1 four-verb pattern (P1) but split into a separate
    entry to stay under the `_MAX_PATTERN_LENGTH` (200 chars) ReDoS
    safety cap. Verbs `scrap`, `void`, `abort` intentionally omitted —
    awkward attack phrasings; the ADR-009 red-team CLI will surface
    them if they become real. Includes a leading `(?<!\w)` lookbehind
    so the verb cannot match as a substring of a longer word (e.g.
    `preset previous instructions` does NOT match `reset` inside
    `preset`).
  - **P5 all-form paraphrase**: same six paraphrase verbs in the
    direct `bypass all instructions` shape. Mirrors P2 with the same
    `(?<!\w)` word-boundary guard.
- **Cross-language coverage intentionally NOT shipped in this wave.**
  A first-iteration cross-language pattern (P6) was prototyped during
  PR #61 review (8 verbs × 7 nouns, then narrowed to 7 non-English
  verbs). The triple-AI second-reviewer gate flagged that bare
  `verb + instructions` is ambiguous in any language — benign foreign
  prose like "ne pas ignorer instructions de votre patron" has the
  same shape as adversarial bare foreign payloads. The asymmetric
  narrowing (English-verb removed for benign-prose protection;
  non-English verbs left bare) was incoherent. Adding cross-language
  qualifiers (`précédentes`, `vorherigen`, `anteriores`, …) would
  roughly double the pattern complexity and re-introduce the
  ReDoS-safety length-cap problem. Per 2026 research (SafePrompt
  regex-only F1 ~0.43; TokenMix PromptBench classifier-only +18%),
  cross-language detection is the architectural ceiling regex hits
  fastest — the right tool is the LLM-as-judge tier proposed in
  ADR-010 (semantic scanner). The corpus has zero foreign-language
  entries today, so deferring the regex layer here costs zero current
  coverage; ADR-009 red-team CLI will generate adversarial
  cross-language payloads for future evaluation.
- **`tests/test_security.py::TestWave21ParaphraseInjectionFamily`**
  (NEW): 14 paraphrase-verb positive cases, 13 cross-language positive
  cases, 14 false-positive guards covering benign uses of the new
  verbs (`reset password`, `cancel the meeting`) and benign uses of
  foreign instruction nouns (`Bitte folgen Sie den Anweisungen`,
  `Suivez les instructions`). 41 new assertions, all green.
- **Adversarial corpus re-tier (5 entries)**: `LLM01-EX-028` (canonical
  "Ignore all previous instructions"), `-055` (case-alternation
  leetspeak), `-056` (extra spaces), `-057` (tabs), `-058` (newlines)
  moved from `extended` → `bright_line`. v1.6.1 regex catches all five;
  same hygiene class as PR #60.
- **Adversarial baseline regenerated**: `bright_line: 62/62 (100%) →
  67/67 (100%)`; `extended: 10/58 (17.2%) → 5/53 (9.4%)`. The extended
  rate dips because 5 passing entries left the pool, not because
  detection regressed. The bright_line floor expanded by 5 must-pass
  payloads — the architecturally meaningful direction.

### Honest scope note

This wave provides **forward-defensive coverage** for paraphrase verb
families and cross-language attacks that do not appear in the current
OWASP-derived corpus. The 48 remaining extended-tier failures
predominantly use **noun substitution** (`filters`, `context`,
`programming`, `directives`) or **passive voice** ("your instructions
have been revoked") — both architectural shifts the regex layer cannot
reach without unbounded pattern growth. Per 2026 industry research
(SafePrompt: regex ceiling F1 ~0.43; TokenMix: PromptBench
classifier-only reduces injection success by ~18%), the path past this
ceiling is the LLM-as-judge tier proposed in ADR-010. The ADR-009
red-team CLI will validate these new Wave-21 patterns against
adversarially generated payloads in a future wave.

- **`docs/adr/ADR-005-pr52-vc-adversarial-review-response.md`** —
  NEW. Formal maintainer response to PR #52 adversarial VC review:
  23-finding triage matrix (13 Accept / 7 BD / 2 Decline / 1 Defer),
  locked user decisions, revised release roadmap, C.1/C.2 declined
  decisions with MADR Revisit triggers (DistilBERT classifier swap;
  opt-out install telemetry), and §12 per-diligence-question
  appendix answering review §7 Q1-Q12. Authored in the v1.7.0 cycle
  but landed early (v1.6.2 release window). Supersedes "forthcoming
  ADR-005" placeholders in TODO.md, `CHANGELOG.md`, `docs/metrics.md`,
  and the merged VC review editorial banner.

## [1.6.2] - 2026-04-24

### Added

- **`src/aipea/search.py`**: PEP 562 module-level `__getattr__` for the
  legacy `HTTP_TIMEOUT` alias — every access now emits
  `DeprecationWarning` AND re-resolves against current config (fixes
  the #81 runtime-config-change gap as a side effect). Hard removal
  scheduled for v2.0.0rc1 per `TODO.md §Release Roadmap`. AgoraIV's
  14 existing references (shim + two regression tests) continue to
  work; the warning fires once per process on first import.
  *(PR #51)*
- **`src/aipea/search.py`**: `_resolve_provider_url(env_var,
  config_field)` private helper; `_resolve_exa_api_url` and
  `_resolve_firecrawl_api_url` now delegate. No behavior change.
  *(PR #51)*
- **`tests/test_search.py::TestV162HTTPTimeoutDeprecation`**: 4 new
  regression tests covering direct access, `from … import …`, live
  re-resolution across `AIPEA_HTTP_TIMEOUT` env-var changes, and
  unknown-attribute still-raising. *(PR #51)*
- **`docs/adopters.md`** — NEW. Named adopters (Agora IV + AEGIS)
  with integration patterns, AIPEA version pinned, and production
  signals. Pydantic-pattern: named-adopters beat anonymized.
  *(PR #51)*
- **`docs/metrics.md`** — NEW. Engineering-quality signals table;
  release-cadence history; adoption-signals section; live pepy.tech
  download-trajectory badge + GitHub-native signal badges (stars,
  forks, issues, last commit, contributors); "Signals we currently
  do NOT publish — and why" section with explicit zero-counts
  (funnel conversion, external contributors, design partners,
  external PRs); opt-out install-telemetry declined-by-policy note
  with forward-pointer to ADR-005 Plan C.2 rationale. *(PR #51 + #53)*
- **`case-studies/agora-iv-v1.md`** — NEW. 10-week narrative
  (v1.0.0 → v1.6.1) with Wave 18/19/20 defect counts, three
  highlighted security fixes (#96 HIPAA leak, #107 ReDoS, #108
  ZWSP bypass), honest-limits section, and reference index.
  *(PR #51)*
- **`docs/claude/audits/vc-adversarial-review-2026-04-24.md`** —
  NEW. 349-line adversarial VC review merged verbatim with
  maintainer editorial-note banner flagging stale metrics (67 →
  238 commits; ~810 → 1,282 tests) and cross-linking to prior
  adversarial review + forthcoming ADR-005. *(PR #52)*
- **`README.md`**: "Adoption & metrics" block linking the three
  new P5e-trio docs. *(PR #53)*
- **GitHub Discussion #54**: "Are you using AIPEA? Tell us how — no
  NDA required" — adopter-outreach thread. *(not committed; live
  at [#54](https://github.com/undercurrentai/AIPEA/discussions/54))*

### Changed

- **`TODO.md`**: full restructure. Release Roadmap table
  (v1.6.2 → v1.7.0 → v1.8.0 → v2.0.0rc1 → v2.0.0) with approved
  2026-10-22 v2.0.0 target based on industry-norm deprecation
  windows (NEP 23 / PEP 387 / SQLAlchemy). All 5 former Open
  Questions closed with decision links. PR #52 Adversarial VC
  Review response section tracking 6 phases. *(PR #51 + #53)*
- **`SPECIFICATION.md`**: header, footer, §7.4 pattern count, and
  §10 roadmap pointer synced to v1.6.1 state (P1-P4 → P1-P5,
  TODO.md as canonical tracker). *(PR #51)*
- **`CLAUDE.md`** (project): library version, `last_audit`, Source
  LOC, and §12 ROADMAP reference all synced to v1.6.1.
  *(PR #51)*
- **`CONTRIBUTING.md` / `SECURITY.md`**: effective-date bumps.
  `SECURITY.md` notes the bump reflects expanded injection-pattern
  coverage shipped in v1.6.1. *(PR #51)*

### Removed

- **`benchmarks/`** (`run.sh` + `perf_baseline.json`) — scaffold-era
  stub; never wired to CI; `pytest-benchmark` not a dep. Industry
  data on hosted-runner benchmark gates (45% FP rate per CodSpeed
  measurement) makes activation unwise for single-maintainer OSS.
  *(PR #51)*
- **`tools/ci/enforce_perf_gate.py`** — companion to the removed
  `benchmarks/`. *(PR #51)*
- **`Makefile`**: `perf:` target + `.PHONY` entry. *(PR #51)*
- **`tools/ci/generate_scorecard.py`**: `("enforce_perf_gate.py",
  "Perf Gate")` tuple entry in LINTERS. *(PR #51)*

### Fixed

- **`src/aipea/enhancer.py:1334-1342`** rolling-average bootstrap
  asymmetry — verified as a **false positive** from `/discover`
  2026-04-23; the `count == 1` branch already correctly
  special-cases the first-update path. No code change required.
  *(PR #51)*

### Governance / meta

- **Repo flipped PUBLIC** (2026-04-23). Pre-flip audit: zero
  committed secrets / real API keys / AWS account IDs / PII leaks.
  GitHub auto-enabled secret scanning, push protection, Dependabot
  security updates, secret-scanning-non-provider-patterns, and
  validity checks.
- **GitHub Discussions enabled** (2026-04-23) for adopter-outreach
  flow referenced from `docs/adopters.md`.
- **Second-committer contract** budget authorized (~$40K/yr, ~0.25
  FTE) per PR #52 response plan. Scope-of-work draft at
  `~/.claude/plans/aipea-second-committer-sow-v0.md` (personal;
  not committed).

## [1.6.1] - 2026-04-22

### Fixed
- **[security]** Injection detector now blocks the canonical jailbreak
  phrase `Ignore all previous instructions` and the wider instruction-
  override family (`disregard`, `forget`, `override`, multi-word
  connectors such as `all your`, `the above`, `everything above`).
  The pre-fix regex `ignore\s+(previous|all)\s+instructions` only
  accepted a single intervening word, so real-world prompt-injection
  attempts slipped through with `is_blocked=False`. The single pattern
  is replaced with three narrower ones to avoid overmatching benign
  prose:
  1. Strong-cue form: only a single optional determiner
     (`the|your|my|any|these|those`) is allowed between verb and a
     strong cue (`previous|prior|above|earlier|preceding|system|
     developer|assistant`), so phrases like `forget the setup
     instructions` or `forget to print your instructions` are not
     matched.
  2. Direct `all` form: `(ignore|disregard|forget|override) all (of|
     the|your|my|these|those|previous|prior|above|earlier|preceding)*
     instructions` — filler restricted to an allow-list, so
     `don't forget to send all instructions` is not matched.
  3. Directional sibling with phrase-end lookahead:
     `(?=\s*[.!?,;:\n]|$)` keeps `ignore all prior art` and
     `disregard everything below deck` unblocked.

  `INJECTION_PATTERNS` now contains 10 entries (was 8);
  `SPECIFICATION.md §7.4` updated to match. Filed by PR #49 review
  (`docs/claude/audits/review-2026-04-22.md` §1 HIGH); tightening
  motivated by PR #50 AI second-review gate (gpt-5.4-pro). New
  regression tests in `TestInstructionOverrideInjectionFamily`:
  13 attack phrasings, 9 overmatch guards, ZWSP normalizer
  composition.
- **[tests]** `tests/test_learning.py::test_readonly_directory` now
  skips when the runner is uid 0 (root bypasses POSIX DAC, so
  `chmod 0o444` cannot force the graceful-degradation path the test
  asserts on). Library behavior for non-root callers is unchanged.
  Filed by PR #49 review §2 MEDIUM.

## [1.6.0] - 2026-04-15

### Added — Taint-Aware Feedback Averaging (ADR-004)
- `LearningPolicy.exclude_tainted_from_averaging` field (default `True`):
  feedback associated with compliance-taint scanner flags (PII/PHI/classified/
  injection) is recorded to `learning_events` for audit but excluded from
  `strategy_performance` averaging by default.
- `LearningRecordResult` frozen dataclass: typed return for
  `AdaptiveLearningEngine.record_feedback` / `arecord_feedback` (replaces
  `None`).
- `FLAG_PII_DETECTED`, `FLAG_PHI_DETECTED`, `FLAG_CLASSIFIED_MARKER`,
  `FLAG_INJECTION_ATTEMPT`, `FLAG_CUSTOM_BLOCKED` — canonical flag-prefix
  constants in `security.py`.
- `_COMPLIANCE_TAINT_PREFIXES` — internal tuple grouping the four
  compliance-taint prefixes.
- `ScanResult.has_compliance_taint()` method.
- `EnhancementResult.scan_result` field (populated by `AIPEAEnhancer.enhance()`).
- `taint_flags` (TEXT) and `excluded_from_averaging` (INTEGER) columns on
  `learning_events` table; additive schema migration via loop-based pattern.
- `LearningRecordResult` exported in `__init__.py` (44 → 50 public symbols).
- ADR-004: Taint-Aware Feedback Averaging.
- 38 new taint-awareness tests in `tests/test_learning_compliance.py`.

### Changed
- `AdaptiveLearningEngine.record_feedback` / `arecord_feedback` now return
  `LearningRecordResult` instead of `None` and accept keyword-only
  `scan_flags: Sequence[str] = ()`. Callers that ignored the previous `None`
  return are unaffected.
- `AIPEAEnhancer.record_feedback` threads `result.scan_result.flags` to the
  engine and logs taint-exclusion decisions.
- Schema migration in `_init_schema` refactored to loop-based pattern
  (per-column graceful degradation).

### Security
- Closes feedback-poisoning vector per ADR-004: tainted feedback cannot shift
  `strategy_performance.avg_score` when `exclude_tainted_from_averaging=True`
  (the default). References OWASP LLM Top 10 2026 (LLM03) and NISTIR 8596.

## [1.5.0] - 2026-04-15

### Added — Compliance-Aware Adaptive Learning (2026-04-14)
- `LearningPolicy` frozen dataclass: controls compliance-aware behavior of
  `AdaptiveLearningEngine` (TACTICAL hard-locked never-record, HIPAA
  default-deny with opt-in, GENERAL unchanged).
- `compliance_mode` column on `learning_events` table for audit trail.
  Additive schema migration via `PRAGMA table_info` + `ALTER TABLE ADD COLUMN`.
- `prune_events()` / `aprune_events()` retention methods with configurable
  `max_age_days` and `max_count` (mirrors `knowledge.py:prune_low_relevance`).
- `AIPEAEnhancer.__init__` accepts `learning_policy` parameter; `record_feedback`
  threads `security_context.compliance_mode` to the engine.
- `LearningPolicy` exported in `__init__.py` (43 → 44 symbols).
- Input validation on `LearningPolicy` and `prune_events` parameters.
- ADR-003: Compliance-Aware Adaptive Learning Engine.
- 34 new compliance tests in `tests/test_learning_compliance.py`.

### Fixed (Wave 20 — Bug Hunt)
- **CRITICAL** `security.py`: Zero-width Unicode characters (ZWSP, ZWNJ, BOM,
  etc.) bypass injection detection, classified marker detection, and
  conversation separator detection. Added three-phase normalization: space-like
  invisible chars → space, Unicode line separators → `\n`, joiners → stripped.
  (#108, #108b)
- `enhancer.py`: `enhance_for_models()` dropped learned strategy when
  rebuilding per-model prompts (`strategy=None` instead of
  `base_result.strategy_used`). (#109)
- `learning.py`: `__init__` leaked SQLite connection when `_init_schema()`
  failed — same pattern fixed in knowledge.py #106 but not applied to
  learning.py. (#110)
- `learning.py`: `_open_connection` leaked connection when PRAGMA
  journal_mode=WAL failed. (#111)
- `config.py`: NUL byte sentinel (`\x00`) in dotenv unescape collided with
  `\u0000` from `_escape_config_value`; NUL bytes corrupted to backslash on
  roundtrip. Fixed with PUA sentinel U+E000. (#112)
- `search.py`: Firecrawl no-score default (0.7) inconsistent with Exa (0.5);
  caused systematic ranking bias in multi-source search. (#113)
- `search.py`: Indented ATX headers (`   # injected`) bypassed markdown
  escaping in search context formatting. (#114)

### Changed
- `engine.py`: Ollama generation timeout is now configurable via
  `AIPEA_OLLAMA_TIMEOUT` env var (default: 120s, was hardcoded 60s).

## [1.4.0] - 2026-04-13

### Added (Wave D1)
- `src/aipea/learning.py` — Adaptive Learning Engine. SQLite-backed strategy
  performance tracking with per-query-type running averages and learned
  strategy suggestion. Opt-in via `AIPEAEnhancer(enable_learning=True)`.
- `AdaptiveLearningEngine` exported in `__init__.py` (42 → 43 symbols).
- `EnhancementResult.strategy_used` field — surfaces the effective strategy
  name on every enhancement result.
- `AIPEAEnhancer.record_feedback(result, score)` — async method to record
  user satisfaction and feed the learning loop.
- `AIPEAEnhancer.get_status()` now includes `learning_enabled` and
  `learning_stats` keys.
- 24 new tests: 18 in `tests/test_learning.py` + 6 in `tests/test_enhancer.py`.
- AI second-reviewer verdict enforcement: `REQUEST_CHANGES` from any of the
  3 AI reviewers now fails the CI job, blocking merge via branch protection.
  Previously verdicts were advisory (comment-only).

### Deprecated
- `ComplianceMode.FEDRAMP` is formally deprecated and scheduled for removal
  in v2.0.0. AIPEA does not implement FedRAMP controls; the mode was always
  a config-only stub with no behavioral enforcement. Constructing a
  `ComplianceHandler` with `ComplianceMode.FEDRAMP` now emits a
  `DeprecationWarning` pointing at
  [ADR-002](docs/adr/ADR-002-fedramp-removal.md). Integrators currently
  using FEDRAMP should migrate to `ComplianceMode.GENERAL` and implement
  FedRAMP controls in their own application layer. The enum value and its
  legacy stub behavior are retained for API back-compat through the v1.x
  line.

### Hardened (PR #36)
- `src/aipea/security.py`: `SecurityScanner.__init__` now validates each
  hardcoded `INJECTION_PATTERNS` entry against `_is_regex_safe()` before
  compiling. Raises `RuntimeError` if a future pattern fails the ReDoS
  safety check (defense-in-depth).
- `src/aipea/engine.py`: `OllamaOfflineClient.get_available_models()` adds
  a final `except Exception` fallback after the existing `OSError` handler,
  logging the full traceback and returning an empty list. Prevents unexpected
  exception types from crashing the enhancement pipeline.
- 4 new tests: 2 in `tests/test_security.py`
  (`TestInjectionPatternSelfValidation`), 2 in `tests/test_engine.py`
  (unexpected exception + stdout-None scenarios).

### Added (Customer E2E)
- `tests/test_customer_e2e.py` — 48 customer-journey-level live tests across
  10 classes: quality scoring, enhance_for_models, strategy override,
  clarifications, config round-trip, error recovery, full lifecycle with
  learning feedback, multi-compliance comparison, temporal awareness, and
  singleton lifecycle. Zero mocks, all `force_offline=True` for determinism.
  Test count: 1034 → 1082, coverage: 93.05% → 93.32%.

### Changed
- README.md, CLAUDE.md, SPECIFICATION.md, TODO.md, SECURITY.md, ROADMAP.md:
  FedRAMP references rewritten to reflect the deprecation. The supported
  compliance modes are now documented as GENERAL, HIPAA, TACTICAL.
- `src/aipea/security.py` `ComplianceHandler._configure_for_mode`: FEDRAMP
  branch now emits `warnings.warn(..., DeprecationWarning)` with a clear
  migration message in addition to its existing `logger.warning`.
- `src/aipea/enhancer.py`: FEDRAMP warning log line tightened to point at
  ADR-002 (the canonical DeprecationWarning now fires from
  ComplianceHandler; no duplicate warning emitted).
- `src/aipea/config.py`: `AIPEA_DEFAULT_COMPLIANCE` env var docstring
  reflects the deprecation. `"fedramp"` remains a valid config value for
  back-compat through v1.x.
- `docs/ROADMAP.md` §P5b: marked resolved via Path B.

### Added
- `src/aipea/errors.py` — custom exception hierarchy: `AIPEAError` base
  class plus 5 subclasses (`SecurityScanError`, `EnhancementError`,
  `KnowledgeStoreError`, `SearchProviderError`, `ConfigError`). All 6
  exported in `__init__.py` (36 → 42 symbols in `__all__`). Wave C3 / PR #23.
- `tests/test_errors.py` — 14 unit tests for the exception hierarchy
  (inheritance, `str()` messages, pickling, `isinstance` contracts).
- `docs/adr/ADR-002-fedramp-removal.md` — decision record for the Path B
  removal of FedRAMP from AIPEA's declared compliance surface. Documents
  context, decision, alternatives considered (including why Path A was
  rejected for now and under what conditions it could be reopened), and
  consequences.
- `tests/test_security.py`: new regression test
  `test_fedramp_mode_deprecation_warning_message` asserting the warning
  message contains "FEDRAMP", "v2.0.0", "ADR-002", and "GENERAL" (the
  migration target). Existing FEDRAMP tests renamed + updated to assert the
  `DeprecationWarning` is raised and to preserve legacy stub behavior for
  back-compat.

### Changed (Wave C3)
- `src/aipea/cli.py`: 4 broad `except Exception:` blocks at lines 191,
  220, 283, and 438 narrowed to specific exception types
  (`httpx.HTTPStatusError`, `httpx.HTTPError`,
  `importlib.metadata.PackageNotFoundError`, `sqlite3.Error`). One
  outermost catch-all retained per CLI command handler at the boundary.
- `tests/test_cli.py`: 9 regression tests verifying the tightened exception
  handling (one per converted block + parametrized variants).
- `tests/test_live.py`: symbol-count assertion updated (36 → 42).

## [1.3.3] - 2026-04-11

**Security-relevant release.** Closes two findings users should upgrade for immediately:

- **#96 — HIPAA/TACTICAL compliance leak** in `_scan_search_results`: hardcoded `SecurityContext(compliance_mode=GENERAL)` meant PHI and classified markers in scraped web snippets were never filtered for HIPAA- or TACTICAL-mode callers, and could be embedded verbatim into the downstream prompt.
- **#107 — ReDoS** in `_is_regex_safe`: duplicated-alternative quantified groups (`(X|X)+`) were not flagged, making the regex validator itself vulnerable to the DoS class it was supposed to prevent.

Plus 11 additional fixes from bug-hunt Wave 19 and 4 ultrathink audit extensions. See details below. Also introduces `SECURITY.md` with a formal vulnerability disclosure policy and honest scope framing (HIPAA/TACTICAL are detection + allowlist only; FedRAMP is an unenforced config stub).

### Added
- `SECURITY.md` — vulnerability disclosure policy, scope, supported versions

### Fixed (Wave 19 — 13 bugs fixed, 4 ultrathink audit extensions, 0 deferred)
- **security**: `patient_name` PHI regex was compiled with `re.IGNORECASE`, a Python gotcha that makes `[A-Z]`/`[a-z]` character classes case-insensitive and collapsed the pattern to "patient + any two words" — every HIPAA-mode query containing "patient" (e.g. "the patient has good vitals") was flagged as PHI. Compile without the flag and scope case-insensitivity to the label via `(?i:patient)` (#95)
- **enhancer**: `_scan_search_results` hardcoded `SecurityContext(compliance_mode=GENERAL)`, so `SecurityScanner.scan` never ran PHI checks (HIPAA-gated) or classified-marker checks (TACTICAL-gated) on scraped web snippets. A user who selected HIPAA/TACTICAL could receive search results containing MRNs, patient names, or SECRET markers embedded verbatim into the prompt forwarded to downstream models — silent compliance leak. Thread the caller's `security_context` through and filter on `phi_detected:*` / `classified_marker:*` / `pii_detected:*` (ultrathink extension for HIPAA Safe Harbor compliance) flags (#96)
- **security**: Incomplete uppercase Cyrillic homoglyph map. Wave 15 #56 covered lowercase U+0456 and U+0455 but NOT their uppercase counterparts U+0406, U+0405, U+0408; since NFKC does not normalise these to Latin, an attacker could bypass injection and classified-marker detection with capital Cyrillic homoglyphs (e.g. U+0406 for `I` in "Ignore"). Add the missing entries (#97)
- **search**: `_format_openai` and `_format_generic` emitted `result.url` without escaping. A scraped page whose URL contained a newline followed by `# ...` or `1. ...` could inject a live markdown header or numbered-list item into the downstream prompt. Apply `_escape_markdown` / `_escape_plaintext` to URL field for parity with title/snippet (#98)
- **config**: `_parse_dotenv` caught `OSError` (including `PermissionError`) and returned `{}`, making "missing" and "unreadable" indistinguishable to `save_dotenv`. A user whose `.env` had been locked down lost every non-AIPEA line on the next `aipea configure` because `os.replace` only needs parent-directory write permission. Distinguish `FileNotFoundError` from other `OSError`; `save_dotenv` passes `strict=True` so unreadable-existing raises instead of silently destroying preserved keys. Extracted `_read_dotenv_text` helper to keep McCabe < 15 (#99)
- **search**: `FirecrawlProvider.deep_research` hardcoded `https://api.firecrawl.dev/v1/deep-research`, ignoring `AIPEA_FIRECRAWL_API_URL` overrides that `search()` already honored. Silent regression of wave 15 #73 for tests stubbing the env var and enterprise mirrors. Derive the deep-research URL from the resolved search URL via string substitution (#100)
- **engine**: `formulate_search_aware_prompt` used an ad-hoc substring chain (`"gemini" in model_lower or "google" in model_lower`) that missed Gemma ids (currently the active offline model). Produced inconsistent formatting where the query section fell through to the generic branch while the sibling search-context block used the canonical `get_model_family` and correctly picked the Gemini-family format. Delegate to `get_model_family` (#101)
- **knowledge**: `_add_knowledge_sync` committed the `knowledge_nodes` upsert and the FTS delete+insert in separate transactions with a narrow `except sqlite3.OperationalError`. Any other `sqlite3.Error` subclass left the KB in a half-written state — the node retrievable by id, invisible to FTS search, until the next restart's `_sync_fts_index` rebuilt the index. Single transaction, widened except clause, explicit rollback + re-raise (#102)
- **enhancer**: `enhance_for_models` lacked the empty-query short-circuit that `enhance()` had. Empty queries slipped through and the per-model loop produced prompts with literally empty query sections. Mirror the guard, return `{}` on empty/whitespace-only input (#103)
- **config**: `_parse_dotenv` used `encoding="utf-8"` which does not strip the UTF-8 BOM. A BOM-prefixed `.env` (Windows Notepad default) parsed the first key as `"\ufeffKEY"`, silently mis-classified as non-AIPEA and written back under the BOM-decorated name. Switch to `encoding="utf-8-sig"`. Ultrathink extension also strips BOM in `_parse_toml_config` for the same class of bug affecting `~/.aipea/config.toml` (#104)
- **quality**: `_score_density` had a discontinuous, non-monotonic curve at `delta = 0` — the positive branch started from 0 (`+0.001` → 0.007) while the negative branch started from 0.5 (`-0.001` → 0.499), so a tiny improvement scored 70x worse than a tiny regression. Rewrite so the positive branch also starts from 0.5 baseline: `0.5 + (delta / 0.15) * 0.5` (#105)
- **knowledge**: `_init_db` only caught `sqlite3.OperationalError`, leaking the half-initialized connection on any other `sqlite3.Error` subclass. Widen to `sqlite3.Error` with `contextlib.suppress` for the close (#106)
- **security**: `_is_regex_safe` missed the duplicated-alternative ReDoS class `(X|X)+` / `(X|X)*` (verified: `^(a|a)*b$` on 25 `a`s takes >1s, `^(a|a|a)*b$` on 18 `a`s takes >11s — catastrophic at even fewer alternatives as the count grows). Ultrathink-extended heuristic catches any quantified group whose first two alternatives are identical regardless of how many additional alternatives follow (#107)

### Fixed (Wave 18 — 7 deferred bugs resolved, 1 reclassified)
- **enhancer**: `enhance_for_models()` now rebuilds the per-model prompt via `formulate_search_aware_prompt()` using the cached search context, so every model gets its own query-section format (GPT markdown, Claude XML, Gemini numbered) instead of baking the first model's format into all outputs (#90)
- **config**: `save_dotenv` and `save_toml_config` now write atomically via `tempfile.mkstemp` + `os.replace`, eliminating the umask/chmod TOCTOU window during which secret files could briefly be world-readable on shared hosts (#91)
- **cli**: `_test_exa_connectivity` and `_test_firecrawl_connectivity` now accept an `api_url` parameter; callers pass `cfg.exa_api_url` / `cfg.firecrawl_api_url` so custom endpoints persisted in `.env` or global TOML are honored (silent regression of wave 15 #73) (#92)
- **knowledge**: `_get_storage_stats_sync` now reads `node_count` and `db_size_bytes` under a single `_with_db_lock()` block, preventing stale-count / fresh-file-size mismatches from concurrent writes (#80)
- **search**: Exa and Firecrawl providers now call `_resolve_http_timeout()` at request time instead of using the module-level `HTTP_TIMEOUT` constant frozen at import; aligns HTTP timeout resolution with the already-lazy URL resolution from wave 15 #73 (#81)
- **quality**: `_score_clarity` returns `0.0` for whitespace-only enhanced prompts instead of the misleading `1 - exp(-1) ≈ 0.632` fallback (#93)
- **config**: `_parse_dotenv` now decodes `\uXXXX` escapes emitted by `_escape_config_value` via `re.sub`, closing the round-trip gap opened by wave 14 #72. Literal backslashes (raw `\\u0041`) are preserved unchanged thanks to the existing `\x00` protection sentinel (#94)

### Reclassified (Wave 18)
- **search**: Exa API score clamping moved from DEFERRED to INTENTIONAL. Exa's official Python SDK spec documents neural scores as `[0, 1]` (https://docs.exa.ai/sdks/python-sdk-specification); normalizing would destroy those absolute semantics and make scores batch-dependent. The `SearchResult.__post_init__` defensive clamp remains as a safety net against malformed upstream responses (#79)

## [1.3.2] - 2026-04-09

### Changed
- Upgrade PyPI classifier: "Development Status :: 4 - Beta" → "Development Status :: 5 - Production/Stable"
- Update README badges: 698→752 tests, 91.42→91.79% coverage
- Add PyPI monthly downloads badge

### Fixed
- Remove `aipea_knowledge.db` from git tracking (runtime artifact, now gitignored)
- Add `.afa.yaml` to `.gitignore`
- Update stale `KNOWN_ISSUES.md` footer timestamp
- Consolidate deferred work items from `NEXT_STEPS.md` and `ROADMAP.md` into canonical `TODO.md`

## [1.3.1] - 2026-03-15

### Changed
- **enhancer**: `enhance()` and `enhance_prompt()` accept `embed_search_context: bool` parameter for controlling search context injection (#74)
- **engine**: `formulate_search_aware_prompt()` accepts `embed_search_context: bool` parameter (#74)
- **config**: `exa_api_url` and `firecrawl_api_url` fields added to `AIPEAConfig` with full config chain support (#73)

### Fixed
- **enhancer**: `AIPEAEnhancer` now supports `close()` and context manager protocol (`with AIPEAEnhancer() as e:`) for deterministic SQLite connection cleanup (#75)
- **config**: dotenv parser correctly handles quoted values with embedded matching quotes (e.g., `KEY='val1' 'val2'`) and no longer unescapes values with missing closing quotes (#76)
- **knowledge**: `_prune_low_relevance_sync` deletes by exact IDs instead of re-evaluating criteria, preventing TOCTOU race between SELECT and DELETE that could orphan FTS entries (#77)
- **cli**: `doctor` connectivity checks no longer produce duplicate output — `silent=True` suppresses raw status lines when called from doctor format (#78)
- **security**: Unicode homoglyph bypass — NFKC normalization + 35-entry confusable character map (Cyrillic/Greek to Latin) applied before all security checks; prevents injection evasion via visually similar characters (#56)
- **search**: API URLs no longer frozen at import time — lazy resolvers `_resolve_exa_api_url()` and `_resolve_firecrawl_api_url()` respect runtime config changes (#73)
- **enhancer**: `enhance_for_models()` now produces distinct per-model search context formatting (markdown for GPT, XML for Claude, numbered list for generic) instead of baking the first model's format into all outputs (#74)
- **cli**: `aipea check` exits 0 when optional API keys are missing (warnings), exits 1 only on connectivity failures (errors) (#41)
- **cli**: Doctor connectivity section uses consistent PASS/WARN/FAIL format via `_DoctorChecks` helper (#42)
- **knowledge**: FTS index entries now cleaned up when nodes are deleted via `delete_node()` or pruned via `prune_low_relevance()` — prevents orphaned FTS data accumulation (#57, #58)
- **knowledge**: `search_semantic()` now updates `access_count` and `last_accessed` for retrieved nodes, matching `search()` behavior (#61)
- **knowledge**: `_sync_fts_index` now rebuilds when FTS count exceeds node count (orphan cleanup), not just when fewer (#69)
- **knowledge**: `add_knowledge` upsert no longer overwrites user-tuned `relevance_score` during re-seed (#70)
- **enhancer**: `ValueError` from Ollama prompt length validation now caught in `_try_ollama_enhancement()` — gracefully falls back to template-based enhancement instead of crashing (#59)
- **engine**: `ValueError` from Ollama prompt length validation now caught in `OfflineTierProcessor.process()` — defense-in-depth (#59)
- **enhancer**: `OFFLINE_MODELS` set now includes all Ollama Tier 1 models (`gemma3:1b`, `gemma3:270m`, `phi3:mini`) (#71)
- **enhancer**: Clarification overlap filter changed from word-level to whole-string containment — analyzer suggestions no longer incorrectly filtered by common English words (#62)
- **cli**: `seed-kb` command now respects configured `AIPEA_DB_PATH` when `--db` is not explicitly provided (#60)
- **cli**: `_doctor_knowledge_base` now uses context manager for `OfflineKnowledgeBase` — prevents connection leak on exception (#63)
- **cli**: `.env` permissions check now tests all 6 group/other bits (was only testing read) (#66)
- **cli**: `.gitignore` check uses line-by-line parsing instead of substring match — no longer false-positives on `.env.example` (#67, #72-configure)
- **cli**: Connectivity tests read API URLs from environment variables instead of hardcoding defaults (#68)
- **search**: `ExaSearchProvider.search()` now guards against empty/whitespace queries (matching Firecrawl) (#65)
- **strategies**: `task_decomposition` split regex now includes `plus` and `as well as` conjunctions (matching count regex) (#64)
- **config**: `_escape_config_value` now escapes TOML-illegal control characters (U+0000-U+0008, U+000B-U+000C, U+000E-U+001F, U+007F) (#72)
- 51 regression tests added across waves 14-16 (752 total, 91.79% coverage)
- All deferred bugs from waves 1-15 resolved

## [1.3.0] - 2026-03-13

### Added
- **enhancer**: Degradation feedback in `enhancement_notes` — reports when offline KB is missing ("run 'aipea seed-kb'"), when no search providers are configured ("aipea configure"), and when Ollama is unavailable ("using template-based enhancement")
- **cli**: Provider descriptions with signup URLs in `aipea configure` (Exa, Firecrawl) and skip hints showing API keys are optional
- **cli**: "Next Steps" panel after `aipea configure` with context-aware guidance
- **cli**: "Recommendations" panel after `aipea doctor` summary with actionable next steps
- **cli**: Platform-specific Ollama install hints in doctor (macOS: brew, Linux: curl, other: URL)
- **README**: "Getting Started" section with 3 paths (Minimal, Search Providers, Ollama) emphasizing zero-config baseline
- **strategies**: New `strategies.py` module — named enhancement strategies with 6 technique functions (specification_extraction, constraint_identification, hypothesis_clarification, metric_definition, task_decomposition, objective_hierarchy_construction) and 6 strategy presets (general, technical, research, creative, analytical, strategic) [P2a roadmap]
- **quality**: New `quality.py` module — heuristic quality assessor scoring clarity, specificity, information density, and instruction quality improvements between original and enhanced prompts [P3a roadmap]
- **enhancer**: `clarifications: list[str]` field on `EnhancementResult` — advisory clarifying questions for ambiguous queries (max 3), generated from ambiguity score, entity count, and complexity signals [P1 roadmap]
- **enhancer**: `quality_score: QualityScore | None` field on `EnhancementResult` — automatic quality assessment of each enhancement
- **enhancer**: `strategy: str | None` parameter on `enhance()` and `enhance_prompt()` — allows explicit strategy selection
- **knowledge**: `search_semantic()` method on `OfflineKnowledgeBase` — BM25-ranked full-text search using FTS5 [P2b roadmap]
- **config**: 4 new configuration fields: `ollama_host`, `db_path`, `storage_tier`, `default_compliance` — all following the standard env var > .env > TOML > default priority chain
- **config**: 6 new environment variables: `AIPEA_OLLAMA_HOST`, `AIPEA_DB_PATH`, `AIPEA_STORAGE_TIER`, `AIPEA_DEFAULT_COMPLIANCE`, `AIPEA_EXA_API_URL`, `AIPEA_FIRECRAWL_API_URL`
- **knowledge**: FTS5 full-text search with query-aware matching and automatic fallback to relevance-score ordering
- **security**: `GLOBAL_FORBIDDEN_MODELS` class variable on `ComplianceHandler` — blocks `gpt-4o` and `gpt-4o-mini` in ALL compliance modes
- **enhancer**: Thread-safe `_stats_lock` protecting all statistics mutations
- **enhancer**: FEDRAMP stub warning when FEDRAMP compliance mode is selected
- **engine**: Warning logs when non-default `max_tokens`/`temperature` passed to `OllamaOfflineClient.generate()`
- 76 new tests (698 total, 91.42% coverage)

### Changed
- **cli**: `_ollama_install_hint()` helper extracted for DRY platform-specific install commands (3 call sites)
- **_types**: `QUERY_TYPE_PATTERNS` and `get_model_family()` centralized as single source of truth (was duplicated in analyzer.py, engine.py, enhancer.py, search.py)
- **analyzer**: `QueryRouter` methods promoted from private to public: `calculate_complexity()`, `detect_temporal_needs()`, `identify_domain()`, `calculate_confidence()`
- **enhancer**: Complexity scoring now uses actual `analysis.complexity` score instead of tier-based mapping
- **enhancer**: Domain defaults changed: OPERATIONAL and STRATEGIC now map to `GENERAL` (was `LOGISTICS` and `MILITARY`)
- **enhancer**: Offline context retrieval now prefers `search_semantic()` (BM25) over `search()` with automatic fallback
- **knowledge**: `OfflineKnowledgeBase.search()` now returns `KnowledgeSearchResult` instead of `list[KnowledgeNode]`
- **knowledge**: Constructor accepts `AIPEA_DB_PATH` env var for database path
- **engine**: `TierProcessor` ABC docstring documents planned Tactical/Strategic subclasses
- **engine**: `formulate_search_aware_prompt()` and `_process_with_templates()` apply strategy technique chains
- **search**: `EXA_API_URL` and `FIRECRAWL_API_URL` now configurable via environment variables
- Logger calls across knowledge.py, search.py, engine.py converted from f-strings to lazy %-formatting (36 sites)
- Narrowed broad `except Exception` blocks to specific exception types (15 sites)
- Added input validation on public API entry points (5 sites)

### Removed
- **engine**: `CLAUDE_CODE_AVAILABLE` placeholder flag (dead code, SDK does not exist)
- **_types**: `ProcessingTier.confidence_threshold` property (dead code, never used)

## [1.2.0] - 2026-03-13

### Added
- **enhancer**: Ollama LLM integration in offline enhancement path — `_try_ollama_enhancement()` uses local SLMs when available, falls back to templates gracefully
- **enhancer**: Cached `OfflineTierProcessor` instance to avoid per-call 18-regex recompilation
- **enhancer**: `include_search` and `format_for_model` optional params on `enhance()` and `enhance_prompt()` — consumers can now skip search context or model-specific formatting independently
- **enhancer**: `_scan_search_results()` filters web search results for prompt injection before inclusion in enhanced prompts (defense-in-depth)
- **enhancer**: `_gather_context_for_enhance()` extracted from `enhance()` to reduce cyclomatic complexity
- **knowledge**: `SEED_KNOWLEDGE` expanded from 13 to 20 entries across 7 domains — added MILITARY (2: COMSEC, tactical decision frameworks), LOGISTICS (1: field sustainment), COMMUNICATIONS (2: network architecture, secure messaging), MEDICAL (1: clinical decision support), GENERAL (1: data privacy by design)
- **knowledge**: `seed_knowledge_base()` helper for populating offline KB
- **cli**: `aipea seed-kb` command to populate knowledge base with seed data
- **cli**: `_doctor_ollama()` diagnostic section — checks Ollama availability, model count, best model
- **cli**: `_doctor_knowledge_base()` diagnostic section — checks KB node count, domain summary
- **engine**: `gemma3:1b` (815MB, 1B params) added to `OfflineModel` enum and Tier 1 preference order
- 89 new tests (622 total, 91.97% coverage)

### Changed
- **enhancer**: Offline tier now attempts Ollama LLM enhancement before falling back to template-only mode
- **engine**: `get_best_available_model()` preference order updated: phi3:mini > gemma3:1b > gemma3:270m
- **engine**: `_get_prompt_template()` no longer accepts `model_type` parameter — content-only enrichment, no behavioral directives
- **engine**: `create_model_specific_prompt()` simplified to return base prompt with optional search context (no behavioral wrapping)
- **engine**: Search context framing changed from "Relevant Search Context:" to provenance-aware "[Supplementary Context from Web Search — not part of the user's original query...]"

### Removed
- **engine**: `TacticalTierProcessor` class (~150 lines) — dead code, never called by enhancer
- **engine**: `StrategicTierProcessor` class (~200 lines) — dead code, never called by enhancer
- **engine**: `PromptEngine.enhance_query()` method (~30 lines) — unused router for deleted tier processors
- **engine**: Model behavioral directives ("You excel at...") from prompt templates — preprocessor should enrich content, not prescribe response style

### Fixed
- **enhancer**: `TYPE_CHECKING` import for `OfflineTierProcessor` resolves Pyright attribute access diagnostic
- **security**: FEDRAMP compliance mode now logs explicit warning that it is an unsupported stub with config-only behavior (no data residency, no FIPS, no continuous monitoring)
- **enhancer**: Wire 5 unused `_`-prefixed parameters in `_gather_online_context`, `_create_passthrough_result`, and `_create_blocked_result` — `security_context` now logged for audit trail, `model_id`/`scan_result`/`compliance_mode` enrich `enhancement_notes` with structured metadata
- **governance**: Complete 3 TODO placeholders in `ai/system-register.yaml` (EU AI Act classification) and `ai/model-card.yaml` (fairness probes, red team summary)

## [1.1.0] - 2026-03-09

### Added
- **enhancer**: `enhance_prompt()` convenience function now accepts `compliance_mode` and `force_offline` params (D1)
- **security**: `quick_scan` exported from root `__init__.py` — `from aipea import quick_scan` now works (D9)
- **search**: `SearchContext` exported from root `__init__.py` as public API
- **search**: Backward-compatibility properties on `SearchContext` (`search_timestamp`, `sources`, `confidence_score`, `query_type`)
- **config**: `AIPEAConfig` dataclass and `load_config()` with priority chain: env vars > `.env` > `~/.aipea/config.toml` > defaults
- **cli**: 4 CLI commands via `aipea[cli]` extra: `configure`, `check`, `doctor`, `info`
- **cli**: `python -m aipea` entry point via `__main__.py`
- **cli**: `aipea configure --global` saves to `~/.aipea/config.toml`
- **cli**: `aipea check --connectivity` tests API key validity
- **cli**: `aipea doctor` runs full diagnostic (Python, deps, config, security, connectivity)
- **search**: Config file fallback in `_get_api_key()` and `_resolve_http_timeout()` helpers
- 196 new tests (533 total, 90.24% coverage)

### Changed
- **engine**: Unified dual `SearchContext` classes — legacy class deleted from `engine.py`, re-exports `aipea.search.SearchContext` (D5)
- **enhancer**: Removed `SearchContext.from_aipea_context()` conversion — passes AIPEA SearchContext directly to PromptEngine (D5)
- **spec**: Section 5.1 updated with full 5-param `enhance_prompt()` signature (D1)
- **spec**: New Section 8.2 documents configuration system priority chain (D8)
- **spec**: Section 11.1 `quick_scan` no longer marked as `(not in __all__)` (D9)
- **ci**: All GitHub Actions SHA-pinned for supply chain security
- **ci**: trivy-action bumped to 0.34.0 (CVE-2026-26189 fix)
- **ci**: Checkov migrated from `-q` to `--compact`, CKV_GHA_7 skipped (false positive)
- **ci**: mutmut migrated to v3.x config-based `[tool.mutmut]` in pyproject.toml
- **ci**: Added `permissions: contents: read` to compliance-nightly and scaffold-checks workflows
- **ci**: Added CodeQL analysis, dependency-review, Dependabot, CODEOWNERS, PR template

### Fixed
- 46 bugs across 12 bug-hunt waves + quality gates (see `KNOWN_ISSUES.md` for details)
- Quote injection in `save_dotenv()` and `save_toml_config()` config writers
- Dotenv parser unescape for `\"` and `\\` in double-quoted values
- `enhance()` offline tier enforcement when `force_offline=True` (#38)
- `float()` coercion guards for all dataclass `__post_init__` isnan checks (#39, #43)
- Newline/CR escaping in `save_dotenv`/`save_toml_config` (#40)
- Conversation separator injection bypass via leading whitespace (#51)
- `save_dotenv` silently destroying non-AIPEA keys in `.env` files (#52)
- `aipea check --connectivity` exit code not reflecting failures (#53)
- `_escape_markdown` missing `#`, `*`, `_`, `~` escaping for rogue header injection (#54)
- `_escape_plaintext` only escaping first line of multi-line text (#55)

## [1.0.0] - 2026-02-14

### Added
- Initial release — extracted from Agora IV production (v4.1.49)
- **security**: PII/PHI detection, classification markers, injection prevention, HIPAA/Tactical compliance
- **analyzer**: Query complexity scoring, domain detection, temporal awareness, tier routing
- **search**: Multi-provider orchestration (Exa, Firecrawl, Context7) with strategy selection
- **knowledge**: Offline SQLite knowledge base with domain-aware retrieval and storage tiers
- **engine**: Model-specific prompt formatting, Ollama client, tier-based processing
- **enhancer**: High-level facade (`enhance_prompt`) coordinating the full pipeline
- **_types**: Shared enums (ProcessingTier, QueryType, SearchStrategy)
- **models**: Data models (QueryAnalysis)
- 337 tests passing, 92.28% coverage
- CI via GitHub Actions (lint, type check, test)
- Strict mypy and Ruff configuration
- SPECIFICATION.md (complete system specification)

### Origin
- 6 production modules (5,923 LOC) extracted from Agora IV into 9 standalone modules (6,192 LOC)
- Original Agora IV files replaced with thin re-export shims (338 LOC) for backward compatibility
- Initially vendored into Agora IV at `vendor/aipea/` for zero-downtime migration (replaced by PyPI install in v1.3.0+)
