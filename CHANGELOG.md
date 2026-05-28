# Changelog

All notable changes to AIPEA will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.7.0] - 2026-05-28

This release formalizes the v1.7.0-RC work that accumulated on `main`
across PR #57 → PR #74 (post-v1.6.2 doc sync, ADR-005/008/009/010,
Phase 4.a/4.b/4.c, cycle-2 through cycle-17 `/quality-gate` bug-hunt
sweeps, and the SCI hardening rounds) plus the v1.7.0 release-cut
polish (G/E/H/I) and Phase LIVE provider-observability fix below.
The prior `[Unreleased]` content flows in as the subsequent sections
of this release.

### Added (v1.7.0 release-cut polish, 2026-05-27)

- **G — DeprecationWarning + MIGRATION.md.**
  `src/aipea/engine.py:PromptEngine.create_model_specific_prompt`
  now emits `DeprecationWarning` (mirrors the FEDRAMP /
  HTTP_TIMEOUT-alias deprecation pattern); scheduled removal in
  v2.0.0. New `docs/MIGRATION.md` consolidates every scheduled
  v2.0.0 removal (FEDRAMP, HTTP_TIMEOUT alias,
  `create_model_specific_prompt`, `TierProcessor`) with
  before/after migration recipes.
- **E — `AIPEAConfig.source_of()` public accessor.**
  `src/aipea/config.py` exposes `source_of(field_name)` +
  `sources()` for per-field origin (env / dotenv / toml / default).
  `src/aipea/cli.py` migrated 5 call sites from the private
  `_sources` attribute to the new public API.
- **H — Coverage hygiene.**
  New `tests/test_models.py` covers `QueryAnalysis.__post_init__`
  NaN coercion, `[0, 1]` clamping, and `to_dict()` enum
  serialization (`src/aipea/models.py` 95 % → 100 %). Extended
  `tests/test_cli.py` with redteam-command error paths,
  `seed-kb`, and `check` / `doctor` connectivity-failure paths
  (`src/aipea/cli.py` 76 % → 87 %).
- **I — AIPEA-specific minimal-risk governance scaffold.**
  Populated `ai/system-register.yaml` (id=aipea; EU AI Act
  Title III Ch. 1 negative-finding rationale), `ai/model-card.yaml`
  (model-agnostic preprocessing; known regex-tier ceilings
  #F12–15), `ai/data-card.yaml` (no training data; runtime
  prompts not persisted), and `ai/risk-register.yaml`
  (R-AI-001 prompt injection, R-AI-002 classified-marker regex
  false-negative, R-AI-003 integrator enforcement boundary).
  The scaffold complements (does NOT replace) the broader
  AI-GOVERNED-tier governance in Libertas-Core; `CLAUDE.md §1.2`
  reconciled accordingly.

### Fixed (Phase LIVE — redteam openai observability, 2026-05-27)

- **`src/aipea/redteam/providers/openai_responses.py`** — when a
  background-mode response reaches a non-success terminal status
  (`failed` / `cancelled` / `incomplete`), the provider now logs
  `error.code` + `error.message` (or `incomplete_details` for
  `incomplete`) at WARNING before mapping to
  `RedTeamResult(error="http_error")`. Surfaced live during
  v1.7.0 Phase LIVE: an `aipea redteam run --provider openai`
  against gpt-5.5-pro returned an empty corpus + bare
  `http_error` with no logged reason; manual retrieve of the
  background response revealed `code: "cyber_policy"` (OpenAI's
  Trusted-Access-for-Cyber gate). Behavior unchanged for callers
  (still `RedTeamResult(error="http_error")`); the diagnostic the
  API returned is no longer silently discarded. New regression
  test (`test_terminal_failed_status_logs_detail_and_tags_http_error`)
  uses `httpx.MockTransport` (zero new deps) to assert both the
  `http_error` tag and the logged `cyber_policy` detail. The
  other three redteam providers (`ollama`, `anthropic`, `codex`)
  all generate successfully live; only `gpt-5.5-pro` hits the
  cyber-policy gate, which is now operator-diagnosable.

### Documentation (v1.7.0 release-cut, 2026-05-27)

- **`CLAUDE.md §1.2`** — reconciled the "no governance artifacts"
  bullet to acknowledge AIPEA's own minimal-risk scaffold while
  noting the AI-GOVERNED-tier governance still lives in
  Libertas-Core. Compliance tier remains STANDARD.
- **`CLAUDE.md §5.4`** — documented `AIPEA_LEARNING_DB_PATH`
  (used only when `AIPEAEnhancer(enable_learning=True)`; default
  `aipea_learning.db`); was already wired in `src/aipea/learning.py`
  but undocumented.
- **`SPECIFICATION.md` footer** — bumped v1.6.2 anchor → v1.7.0 +
  release date.

### Fixed (cycle-2 `/quality-gate` bug-hunt sweep, 2026-05-26)

Six commits on `fix/quality-gate-bug-sweep` closing 12 findings from
the Phase-2 Lane-B sweep (parallel Claude debugger agents) plus a
follow-up GPT 5.4 Pro adversarial critique that widened the security-
finding scope. Lane A (Codex) was unavailable for this run (`codex
exec` hung on stdin-read after 9 h zero-CPU; skill-sanctioned fallback
to Lane-B per `bug-hunt §Error Handling`). All fixes ship with
regression tests (47 new test cases across 4 test files); zero
existing tests regressed.

**Security (`security.py`) — HIGH × 1 + LOW × 2** (commit `6272ffb`):

- **F3 (HIGH C3)** — Multi-word PHI and classified-marker patterns
  were bypassable via zero-width inter-word splits, double-space,
  tab, and three NFKC-stable invisibles plus the Unicode TAG block.
  Four-component fix: `_ALL_INVISIBLE_RE` now covers CGJ (U+034F),
  ALM (U+061C), MVS (U+180E), and the TAG block (U+E0020–U+E007F);
  literal-space tokens in `PHI_PATTERNS` and the new
  `_CLASSIFIED_MARKER_PATTERNS` use `\s+` (no more double-space /
  tab evasion); PII/PHI/classified now scan BOTH normalization
  forms (stripped + spaced) with `dict.fromkeys` flag dedup;
  `force_offline` is the OR of the two TACTICAL scans.
- **F11 (LOW C3)** — Bare `\bSCI\b` false-matched `sci-fi`, `the
  SCI department`, `scientific`. Naive `(?<![\w-])SCI(?![\w-])`
  alternative ALSO failed (spaces are neither word nor hyphen).
  SCI now requires IC-banner compartment-delimiter context:
  `(?<=//)SCI\b|\bSCI(?=//|/[A-Z])`. Matches `TS//SCI`,
  `TOP SECRET//SCI//NOFORN`, `SCI//REL TO USA`; rejects the
  common-English subword false-positive class.
- **F12 (LOW C1, wontfix)** — Mid-line conversation-separator
  regex is intentionally line-anchored at the regex tier per
  ADR-010 semantic-scanner deferral. Documented in code
  comments and `.quality-gate/accepted-findings.jsonl`; pinned
  by `test_mid_line_role_documented_not_blocked` so a future
  regex broadening cannot silently introduce mid-line false
  positives.

**Learning (`learning.py`) — MEDIUM × 1** (commit `a6357e8`):

- **F4 (MEDIUM C3)** — `prune_events(max_age_days=N)` had a
  calendar-day data-loss bug: cutoff used Python `isoformat()`
  (T-separated, microseconds, "+00:00") while `created_at`
  used SQLite's `datetime('now')` format (space-separated,
  second precision). Position 10 of the comparison had `' '`
  (0x20) on the stored side vs `'T'` (0x54) on the cutoff
  side, making ANY row created on the cutoff's calendar date
  at any time of day compare less-than the cutoff and get
  wrongly deleted. Fixed by formatting the cutoff with
  `strftime("%Y-%m-%d %H:%M:%S")`.

**Analyzer (`analyzer.py`) — LOW × 3** (commit `59b302b`):

- **F8/F9/F10 (LOW C3 × 3)** — Three term-matching sites
  (`calculate_confidence`, `_calculate_ambiguity`,
  `_determine_search_strategy`) used substring `str.in` /
  `str.find` matching, producing false hits: `"mighty"`
  matched `"might"` (compound confidence + ambiguity
  penalties on clean queries), `"asbestos"` / `"bestselling"`
  matched `"best"`, `"construe"` matched `"true"` (misrouted
  search strategy). Fixed via four module-level compiled
  regexes anchored at `\b` boundaries (`_AMBIGUITY_RE`,
  `_AMBIGUITY_CONFIDENCE_RE`, `_COMPARATIVE_RE`,
  `_VERIFICATION_RE`).

**Red-team (`redteam/`) — HIGH × 2 + LOW × 3 + cycle-1 recovery**
(commits `3bb503a` + `d5eae2b`):

- **Cycle-1 recovery (`3bb503a`)** — 11 production fixes plus a
  test-infrastructure HIGH bug from an earlier Phase-2 attempt
  that never reached `main`. Production fixes: per-poll TLS-
  handshake reuse on `OpenAIResponsesProvider` (single sync
  client across all poll iterations); 4xx retrieve-error
  fail-fast classification (no more 25-min spin on 401/404);
  `asyncio.to_thread` off-load for the sync polling loop (so
  it doesn't block the event loop for 25 min); generator round-
  label off-by-one fix and loop-variable shadowing repair;
  evaluator smoothed-IDF (n_docs==1 degenerate-case fix
  mirroring sklearn's `smooth_idf` default) and empty-payload
  `empty_response` tagging; `_polling` None-status log-spam
  coercion; reporter atomic-write (tmp-file + `os.replace`)
  and Markdown-injection sanitization (backtick neutralization
  via U+200B wraps + control-char strip); Anthropic SSE
  `error` event handling. The test-infrastructure fix repaired
  a 25-minute CI hang in the cycle-1 regression test file —
  stub `httpx.Response` objects lacked `request=`, which made
  `r.raise_for_status()` raise `RuntimeError` (caught + retried
  by `poll_until_terminal` → infinite busy-loop to the 1500s
  default). Fix attaches `request=httpx.Request(...)` to all
  stubs and pins an explicit short `poll_timeout_seconds` on
  the worker-thread test.
- **F1/F2 (HIGH C3 × 2, commit `d5eae2b`)** —
  `OpenAIResponsesProvider._one_generation` left the create-
  response parse unguarded: `create_resp.json()` could raise
  `json.JSONDecodeError` (a `ValueError` subclass, NOT
  `httpx.HTTPError`), and `created.get("id")` could raise
  `AttributeError` on a non-dict body (list / null / number).
  Both escaped the documented "providers never raise" contract
  and crashed the whole batch. Fixed via a new
  `_parse_create_response` static helper. Also drops
  `_one_generation`'s cyclomatic complexity back under the
  project's `max-complexity = 15` ceiling. Fix covers
  `OpenAICodexProvider` too via inheritance.
- **F5/F6 (LOW C3 + LOW C2, commit `d5eae2b`)** — `_polling.py`:
  deadline `>` → `>=` (closes the test-seam infinite-loop
  reachable via a frozen injected `monotonic` +
  `poll_timeout_seconds=0`); `_extract_status` coerces non-
  string non-enum status values to `None` instead of
  stringifying `0` → `"0"` / `True` → `"True"` (which never
  match `TERMINAL_STATES` but produce misleading operator
  log lines).
- **F7 (LOW C3, commit `d5eae2b`)** — `reporter.py` summary
  reported `len(novel)`, silently capped at 10 by the top-10
  display slice. Now reports the true undetected count with a
  `(top-N by novelty score shown below)` qualifier — material
  for a security audit artifact committed to git.

**Repo hygiene** (commit `401919b`):

- `.gitignore` now ignores `.claude/scheduled_tasks.lock` (a
  machine-local Claude Code scheduler runtime lock that
  surfaced as an untracked file; mirrors the existing
  `.quality-gate/` ephemera ignore).

Verification: `ruff check` + `ruff format --check` clean (57 files);
`mypy --strict src/aipea/` clean (28 source files); full suite **1515
passed, 35 skipped, 5 xfailed** in 25.44 s at coverage **91.60%**
(baseline pre-cycle-2 was 1456 passed / 91.63%). The 5 `xfails` are
pre-existing architectural-ceiling docs (Wave-21 paraphrase tier known
FP zone + the HIPAA `patient_name` ignore-case false-positive guards),
unchanged by cycle-2.

Phase-2 cycle-2 ledger at `.quality-gate/cycle2-findings.md`; GPT 5.4
Pro security design dialogue transcript at
`.quality-gate/cycle2-security-dialogue.md`.

### Fixed (cycle-3 `/quality-gate` follow-up to PR #73, 2026-05-26)

GPT 5.4 Pro's REQUEST_CHANGES verdict on PR #73 (cycle-2) blocked
merge with a primary concern (SCI false positives on URL/path
forms) plus a non-blocking duplicate-warning observation. In parallel,
a cycle-3 Lane-B verification sweep against the cycle-2 fixes
identified eight related gaps — incomplete-closure issues where the
cycle-2 fix addressed a documented bypass class but missed adjacent
variants of the same class. Four atomic commits close all 11
findings.

**Security (`security.py`)** — commit `3e20b59`:

  - **SCI IC-banner-context-anchored** (GPT BLOCKER + cycle-3 F4):
    cycle-2's `(?<=//)SCI\b|\bSCI(?=//|/[A-Z])` matched
    `https://sci-fi.example` and `/sci/readme`. Now requires real IC
    banner context: SCI preceded by a known classification level
    (TS / S / C / U / TOP SECRET / SECRET / CONFIDENTIAL /
    UNCLASSIFIED) + `//`, or followed by a known compartment suffix
    (`//(NOFORN|REL|FGI|IMCON|ORCON|PROPIN|RELIDO|RSEN|HUMINT|COMINT|
    SI|TK|HCS)\b` or `/REL\b`).
  - **`_ALL_INVISIBLE_RE` expansion** (cycle-3 F2, HIGH C3): added
    VS-1..16 (U+FE00-FE0F), Mongol VS-1..3 (U+180B-D), Egyptian
    Hieroglyph Format Controls (U+13430-13438), Brahmi Number Joiner
    (U+1107F), LANGUAGE TAG (U+E0001), and the Variation Selectors
    Supplement (U+E0100-E01EF). Cycle-2's expansion missed these
    NFKC-stable invisibles, leaving inter-word PHI/classified/
    injection bypasses open.
  - **`_UNICODE_NEWLINE_RE` expansion** (cycle-3 F3, MEDIUM C3):
    NEL (U+0085), VT (U+000B), FF (U+000C) are `str.splitlines()`-
    recognized line terminators that bypassed the line-anchored
    conversation-separator injection pattern. Now normalized to `\n`.
  - **Custom blocked patterns two-form scan** (cycle-3 F1, MEDIUM C3):
    cycle-2's two-form scan covered PII/PHI/classified/injection but
    NOT custom patterns. Now mirrors PII/PHI/classified.
  - **SSN/CCN whitespace tolerance** (cycle-3 F5/F6, LOW C2):
    `\b\d{3}\s*-\s*\d{2}\s*-\s*\d{4}\b` (SSN) and
    `\b\d{4}[\s-]*\d{4}[\s-]*\d{4}[\s-]*\d{4}\b` (CCN) now accept
    double-space / tab variants.
  - **Init-time contract for `CLASSIFIED_MARKERS`** (cycle-3 F7,
    LOW C1): every marker in `CLASSIFIED_MARKERS` MUST have a
    matching entry in `_CLASSIFIED_MARKER_PATTERNS`. Catches the
    F11-class false-positive risk at scanner instantiation time.
  - **Log-after-dedup for classified-marker warnings** (GPT
    non-blocking observation): the two-form classified scan no
    longer double-emits warnings; `scan()` emits one WARNING per
    unique marker after the two-form dedupe.

**Analyzer (`analyzer.py`)** — commit `ec5fa55`:

  - **Inflection regression fix** (cycle-3 A1, MEDIUM C3): cycle-2's
    bare `\b(compare|versus|...)\b` alternations dropped inflected
    forms ("compared", "comparing", "comparison", "comparisons",
    "differences", "verifying", "verifies", "verified",
    "verification", "confirmed", "confirms", "confirming",
    "confirmation", "accurately") that the pre-fix substring code
    correctly caught. All 14 inflected queries now correctly route
    to MULTI_SOURCE again. False-positive guards from cycle-2
    preserved ("best" inside "asbestos" still rejected).

**Learning (`learning.py`)** — commit `31f5d0c`:

  - **`ts` format alignment with SQLite schema** (cycle-3 A3, LOW
    C2): `record_feedback`'s `ts = datetime.now(UTC).isoformat()`
    populated `timestamp` + `last_updated` upserts in mixed format
    with the schema's `datetime('now')` DEFAULT. Latent
    cycle-2-F4-class data-loss bug. Now uses
    `strftime("%Y-%m-%d %H:%M:%S")`.

**Reporter (`redteam/reporter.py`)** — commit `0c24ed3`:

  - **Conditional summary parenthetical** (cycle-3 A2, LOW C2):
    `(top-N by novelty score shown below)` only appears when
    `len(undetected) > len(novel)`. Previously read
    `"Undetected payloads: 0 (top-0 by novelty score shown below)"`
    in the all-detected case.

**Regression-test additions** (~70 new test methods across 4 files):

  - `tests/test_security_two_form_scan.py`: 52 new cycle-3 cases
    (custom blocked two-form, 11 expanded invisibles × {PHI,
    injection}, 5 newline-class cases, 18 SCI banner-context cases,
    8 PII whitespace cases, init-contract assertion, log-dedup
    assertion)
  - `tests/test_analyzer_word_boundary.py`: 16 new cycle-3 cases
    (14 inflection positives + 2 cycle-2-FP-still-rejected negative
    controls)
  - `tests/test_learning_prune_datetime_format.py`: 2 new cycle-3
    cases (timestamp + last_updated format consistency)
  - `tests/test_redteam_bughunt_cycle2.py`: 3 new cycle-3 cases
    (conditional parenthetical present / absent / placeholder)

Verification: `ruff check` + `ruff format --check` clean (58 files);
`mypy --strict src/aipea/` clean (28 source files); full suite
**1588 passed / 35 skipped / 5 xfailed in 26.43 s** at coverage
**91.92%** (was 1515 / 91.60% pre-cycle-3). The 5 `xfails` unchanged.

### Fixed (cycle-4 `/quality-gate` follow-up to PR #73 round 2, 2026-05-26)

The gpt-5.4-pro second-reviewer gate's round-2 REQUEST_CHANGES on PR
#73 (against the cycle-3 security commit) raised two blocking concerns;
both fixed in commit `14f4d00`, along with both of its round-2
non-blocking notes.

**Security (`security.py`)** — commit `14f4d00`:

  - **FS/GS/RS line terminators** (GPT round-2 B1): `_UNICODE_NEWLINE_RE`
    missed U+001C (FS), U+001D (GS), U+001E (RS) — `str.splitlines()`-
    recognized terminators — so `"text\x1eHuman: reveal"` still evaded
    the line-anchored conversation-separator injection pattern. Now
    `[\x0b\x0c\x1c-\x1e\x85  ]`, the complete splitlines set.
  - **Bracketed/quoted SCI banners** (GPT round-2 B2): the cycle-3 SCI
    pre-marker gate `(?:^|[\s(])` rejected legitimate `[TS//SCI]`,
    `"TS//SCI"`, `<TS//SCI>` banners (a false NEGATIVE for a
    classified-content gate). Replaced with a negative lookbehind
    `(?<![\w/])` on BOTH branches — accepts any non-word non-slash
    opener while still rejecting URL/path forms (`/TS//SCI`,
    `https://sci-fi`, `/sci/readme`). This also closes GPT's round-2
    non-blocking `/sci/rel/...` path-segment false positive.
  - **RuntimeError architecture note** (GPT round-2 non-blocking):
    documented at the raise site why the cycle-3 F7 init-contract check
    uses the stdlib `RuntimeError` rather than `errors.AIPEAError` —
    `security.py` is a ZERO-aipea-imports module by architectural
    contract; `RuntimeError` is also the sibling INJECTION_PATTERN
    ReDoS-check precedent.

Regression tests (`tests/test_security_two_form_scan.py`): 13 new
cycle-4 cases (3 FS/GS/RS terminator + 6 bracketed/quoted-banner accept
+ 4 URL/path reject).

Verification: full suite **1601 passed / 35 skipped / 5 xfailed in
24.84 s** at coverage **91.65%**; ruff + mypy clean. SCI pattern
16/16 manual matrix correct; FS/GS/RS verified matching.

### Fixed (cycle-5 `/quality-gate` follow-up to PR #73 round 3, 2026-05-26)

The gpt-5.4-pro second-reviewer gate's round-3 REQUEST_CHANGES raised
two more whitespace-tolerance consistency gaps — the same theme as
cycle-3/4 applied to two separators the earlier fixes left rigid.
Both fixed in commit (this commit), plus the round-3 non-blocking
precompile suggestion implemented. After this cycle, EVERY separator
in EVERY security pattern is whitespace-tolerant — the theme is
comprehensively closed (audited: SSN, CCN, MRN, DOB label+value,
patient_name, TOP SECRET, SCI delimiters).

**Security (`security.py`)**:

  - **DOB date-VALUE whitespace tolerance** (GPT round-3 B1): the
    cycle-2 fix widened the `date\s+of\s+birth` LABEL but left the
    date VALUE rigid. `DOB: 01 / 02 / 1990` and `date of birth
    01 - 02 - 1990` evaded. Now
    `\d{1,2}\s*[/-]\s*\d{1,2}\s*[/-]\s*\d{2,4}`.
  - **SCI delimiter whitespace tolerance** (GPT round-3 B2): the
    cycle-4 SCI pattern accepted only exact `//` and `/REL`.
    `TS // SCI`, `S // SCI`, `SCI / REL` (transcribed/dictated
    spacing) evaded — and TS/S/REL are not standalone markers, so
    TACTICAL `force_offline` was bypassed. Now `\s*/\s*/\s*` and
    `\s*/\s*REL` on both branches; each `\s*` is bounded by a
    mandatory literal `/` (no ReDoS ambiguity).
  - **Precompiled classified-marker patterns** (GPT round-3
    non-blocking): `_CLASSIFIED_MARKER_PATTERNS` are now compiled
    once in `__init__` into `_compiled_classified` (catches regex
    typos at construction; avoids per-scan recompilation). Deliberately
    NOT run through `_is_regex_safe` — that validator's 200-char cap
    is a user-input heuristic the legitimately-long SCI alternation
    exceeds; the classified patterns are hardcoded + ReDoS-safe by
    construction.

Regression tests (`tests/test_security_two_form_scan.py`): 19 new
cycle-5 cases (5 DOB-value + 1 DOB negative control, 7 SCI-delimiter
accept + 5 SCI false-positive reject, 1 precompile-table assertion).

Verification: full suite **1620 passed / 35 skipped / 5 xfailed in
25.26 s** at coverage **91.65%**; ruff + mypy clean. DOB + SCI
whitespace matrices verified (all accept/reject cases correct).

### Fixed (cycle-6 `/quality-gate` follow-up to PR #73 round 4, 2026-05-26)

The gpt-5.4-pro gate's round-4 REQUEST_CHANGES identified a SCI
leading-slash FALSE NEGATIVE — the security-conservative direction
(a missed classified banner in TACTICAL mode leaks classified content
to an external model). Fixed in commit (this commit); GPT's round-4
non-blocking subclassing-contract note also documented.

**Security (`security.py`)**:

  - **SCI leading-slash banner admission** (GPT round-4 blocker): the
    cycle-4 `(?<![\w/])` guard rejected leading-slash banners
    `/TS//SCI`, ` /SCI/REL` (list-marker / stray-slash markings at a
    clean boundary) — real classified markings that MUST flag. New
    `_BANNER_OPENER = (?:^|(?<=[\s(\[{<"']))/?` admits an OPTIONAL
    leading slash at a CLEAN boundary (start-of-input or after
    whitespace / open-bracket / quote / angle / paren), while STILL
    rejecting mid-URI/path slashes (`https://example.com/TS//SCI`,
    `path/to/TS//SCI`) where the slash is preceded by a word char.
  - **Compartment-vs-path terminal guard** `(?!/(?!/))` (cycle-6): the
    leading-slash admission would otherwise re-accept the cycle-1
    `/sci/rel/index.html` path FP. The terminal guard rejects a marker
    followed by a SINGLE `/` (path continuation) while ALLOWING `//`
    (a compartment delimiter — so multi-compartment banners
    `SCI//NOFORN//ORCON` still flag) and the terminal/whitespace case.
    This is the precise discriminator that lets the leading-slash
    banner admission coexist with the path rejection: the test moved
    from "is there a leading slash" to "is the marker followed by a
    path-style single-slash continuation".
  - **Subclassing-contract note** (GPT round-4 non-blocking): extending
    `CLASSIFIED_MARKERS` (e.g. via subclass) without a matching
    `_CLASSIFIED_MARKER_PATTERNS` entry now raises `RuntimeError` at
    `__init__` (cycle-3 F7 invariant). This is an intentional
    fail-closed contract — documented here for any consumer subclassing
    `SecurityScanner`. The runtime fallback in `_check_classified_
    markers` still covers instance-level monkeypatch mutations.

Regression tests (`tests/test_security_two_form_scan.py`): a new
`TestCycle6SciLeadingSlashBanners` class (8 leading-slash-accept + 5
mid-URI/path-reject + 1 multi-compartment-accept + 1 compartment-path-
reject) plus a reconciliation of the cycle-5 `path_spaced_rel` case
(`/sci / rel` with spaces is now correctly a banner, not a path).

Verification: `make ci` (CI parity) clean — full suite **1635 passed /
35 skipped / 5 xfailed in 38.09 s** at coverage **91.73%**; ruff +
mypy clean. The SCI accept/reject matrix is now 27 cases (18 accept
banner forms + 9 reject URI/path/prose forms), all verified.

### Fixed (cycle-7 `/quality-gate` follow-up to PR #73 round 5, 2026-05-26)

The gpt-5.4-pro gate's round-5 REQUEST_CHANGES caught two real bugs in
the cycle-6 SCI work — one an asymmetry the cycle-6 fix itself
introduced. Both fixed; GPT's round-5 non-blocking "extract the guards
into named constants" suggestion also implemented.

**Security (`security.py`)**:

  - **First-branch path-continuation guard** (GPT round-5 B1): the
    cycle-6 `(?!/(?!/))` terminal guard was applied only to the SECOND
    SCI branch (`SCI//suffix` / `SCI/REL`), NOT the first
    (`<level>//SCI`). So `/TS//SCI/readme`, `TS//SCI/index.html` wrongly
    matched and forced offline. The first branch now carries
    `_SCI_TAIL_GUARD = (?!/(?!/|REL\b))` — rejects a path continuation
    (`/readme`) while ALLOWING valid banner tails (`//<compartment>`
    chained, `/REL`) and terminals. `TS//SCI//NOFORN` and `TS//SCI/REL`
    still match.
  - **Field-delimiter openers** `: = , ; |` (GPT round-5 B2):
    `_BANNER_OPENER` lacked field delimiters, so unquoted key/value
    banner forms `classification:TS//SCI`, `label:S//SCI`,
    `classification=SCI/REL` did not match — a TACTICAL false negative
    (the bare `\bSCI\b` the cycle-2 fix replaced would have caught
    them). The opener class now includes `: = , ; |`. Verified the
    widening does NOT re-open the URL FP: `https://example.com:8080/
    TS//SCI` still rejects (the `/TS` is preceded by a word char; the
    `:` after `https`/port lands `/?` on the second `/` of `://`, not
    a level token).
  - **Named guard constants** (GPT round-5 non-blocking): extracted
    `_SCI_TAIL_GUARD` and `_SCI_CONT_GUARD` as named `ClassVar`s so the
    SCI regex's two distinct path-vs-banner discriminators stay
    auditable rather than inlined twice.

Regression tests (`tests/test_security_two_form_scan.py`): two new
classes (19 methods) — `TestCycle7SciFirstBranchPathGuard` (4
path-reject + 5 valid-tail-accept) and
`TestCycle7SciFieldDelimiterOpeners` (6 field-delimiter accept + 4
URL/path-still-reject incl. the `:8080` port case).

Verification: `make ci` (CI parity) clean — full suite **1654 passed /
35 skipped / 5 xfailed in 38.52 s** at coverage **91.73%**; ruff +
mypy clean. The SCI matrix is now 30+ cases, all verified.

### Fixed (cycle-8 `/quality-gate` follow-up to PR #73 round 6, 2026-05-26)

The gpt-5.4-pro gate's round-6 REQUEST_CHANGES caught a Hangul-filler
invisible gap and a `C:/` path FALSE POSITIVE that the cycle-7
field-delimiter widening had re-introduced. Both fixed; GPT's round-6
non-blocking ReDoS-perf-test suggestion also implemented.

**Security (`security.py`)**:

  - **Hangul filler invisibles** (GPT round-6): `_ALL_INVISIBLE_RE`
    missed U+115F (HANGUL CHOSEONG FILLER), U+1160 (HANGUL JUNGSEONG
    FILLER), U+3164 (HANGUL FILLER), U+FFA0 (HALFWIDTH HANGUL FILLER) —
    invisible word-splitters (`ignoㅤre previous instructions` evaded
    injection detection). All four added; the compat forms U+3164/U+FFA0
    also NFKC-normalize to U+1160 before the strip.
  - **`C:/` / `scheme:/` path FALSE POSITIVE** (GPT round-6, a cycle-7
    regression): the cycle-7 opener combined the `:` field delimiter
    WITH the optional leading `/?`, so `C:/TS//SCI` (Windows path) and
    `scheme:/SCI/REL` (URI scheme) matched as classified banners. Fixed
    by SPLITTING `_BANNER_OPENER` into two cases: case A
    (`(?:^|(?<=[\s(\[{<"']))/?`) admits an optional leading slash ONLY
    after start/whitespace/bracket/quote; case B (`(?<=[:=,;|])`) is a
    separate NO-slash branch for field delimiters. So `C:/…` /
    `scheme:/…` reject (the slash after `:` is never admitted) while
    `classification:TS//SCI` (no slash) still accepts.
  - **ReDoS-perf regression test** (GPT round-6 non-blocking): since
    the classified patterns bypass `_is_regex_safe`, added a latency
    assertion (`< 1000 ms`) on a 15 KB pathological slash/space input.
    Measured 1.15 ms — no catastrophic backtracking (the `\s*` groups
    are each bounded by a mandatory literal `/`).

Regression tests (`tests/test_security_two_form_scan.py`): three new
classes (17 methods) — `TestCycle8HangulFillerInvisibles` (4 injection
+ 4 PHI), `TestCycle8SciSchemePathFalsePositive` (5 scheme/path-reject +
5 banner-accept), `TestCycle8SciRegexLatency` (1 ReDoS perf).

Verification: `make ci` (CI parity) clean — full suite **1673 passed /
35 skipped / 5 xfailed in 35.65 s** at coverage **91.73%**; ruff +
mypy clean.

### Fixed (cycle-9 `/quality-gate` follow-up to PR #73 round 7, 2026-05-26)

GPT 5.4 Pro's round-7 REQUEST_CHANGES (a leading-double-slash SCI false
negative) plus Claude Opus 4.6's round-7 APPROVE-with-consistency-note
(PII/PHI duplicate logging).

**Security (`security.py`)**:

  - **Leading double-slash SCI portion markings** (GPT round 7): the
    cycle-8 `_BANNER_OPENER` admitted only `/?` (zero-or-one leading
    slash), so canonical IC portion markings with a leading DOUBLE
    slash — `//SCI//TK`, `//SCI/REL` — at a clean boundary did not
    match (a TACTICAL false negative; `TS`/`REL`/`TK` are not
    standalone markers, so nothing else caught them). Case A now uses
    `/*` (a leading slash-RUN of any length), so 0/1/2/N leading
    slashes match WHEN the run starts at a clean boundary
    (start-of-input / whitespace / bracket). Mid-URI/path slash runs
    still reject: `https://example.com//SCI/REL` (the `//` is preceded
    by `.com`), `path/to//SCI//TK` (preceded by `o`), `//SCI/readme`
    (single-slash path continuation after SCI). `/*` is a simple star
    on one char anchored at a clean boundary — no ReDoS (verified ~1.4
    ms on a 20 K-slash adversarial input; a regression test pins this).
  - **PII/PHI duplicate WARNING logs** (Claude round-7 consistency
    note): `_check_pii` / `_check_phi` logged per-match, and the
    two-form scan calls them twice, so a clean `SSN: 123-45-6789`
    (matching in both normalized + spaced forms) emitted the WARNING
    twice before the flag-level dedup. Logging moved to `scan()`
    post-dedup — one WARNING per unique flag — matching the
    classified-marker dedup-then-log pattern established earlier in
    this PR. Cosmetic (no security/correctness impact); closes the
    last log-consistency gap.

Regression tests (`tests/test_security_two_form_scan.py`): two new
classes (12 methods) — `TestCycle9SciLeadingDoubleSlashBanners` (6
double-slash-accept + 5 URI/path-reject + 1 ReDoS-latency) and
`TestCycle9PiiPhiLogDedup` (1 PII + 1 PHI single-log-per-unique-flag).

Verification: `make ci` (CI parity) clean — full suite **1736 passed /
35 skipped / 5 xfailed in 35.86 s** at coverage **91.74%**; ruff +
mypy clean.

### Fixed (cycle-10 `/quality-gate` follow-up to PR #73 round 8, 2026-05-26)

GPT 5.4 Pro's round-8 REQUEST_CHANGES: a field delimiter `[:=,;|]`
FOLLOWED BY a double-slash compartment marking — `classification=//SCI//TK`,
`label://SCI/REL` — was a TACTICAL false negative, because the cycle-8
`_BANNER_OPENER` case B (field delimiter) was strictly no-slash.

**Security (`security.py`)**:

  - **Field-value double-slash banners** (GPT round 8): case B now
    admits an optional `(?:/{2,})?` after the field delimiter — a
    DOUBLE-slash (or more) compartment marking accepts
    (`classification=//SCI//TK`, `label://SCI/REL`), while a SINGLE
    slash after the delimiter still rejects — that single-slash form is
    exactly the URI-scheme / drive-letter pattern (`scheme:/SCI/REL`,
    `C:/TS//SCI`) the round-6 fix established must reject, and
    `(?:/{2,})?` requires two-or-more slashes so it can never match a
    lone `/`. A full URL `https://example.com//SCI/REL` still rejects
    (the `//SCI` follows the host `.com`, not the scheme colon); only
    `://SCI…` — a compartment immediately after the delimiter — matches,
    the same shape GPT classifies as a banner.

Regression tests (`tests/test_security_two_form_scan.py`):
`TestCycle10SciFieldValueDoubleSlash` (5 field-value-double-slash accept
+ 6 single-slash URI/path reject + 1 ReDoS-latency).

Verification: `make ci` (CI parity) clean — full suite **1748 passed /
35 skipped / 5 xfailed in 50.66 s** at coverage **91.96%**; ruff +
mypy clean.

### Fixed (cycle-11 `/quality-gate` follow-up to PR #73 round 9, 2026-05-26)

GPT 5.4 Pro's round-9 REQUEST_CHANGES: the SCI compartment allow-list
(`NOFORN|REL|FGI|...`) was a CLOSED set, a TACTICAL false negative for
valid but UNLISTED compartments / codewords (GAMMA, ECI, FVEY,
special-access program names — IC compartment names are open-ended).

**Security (`security.py`)**:

  - **Generic compartment token** (GPT round 9): the DOUBLE-slash branch
    `SCI//<compartment>` now accepts any all-caps banner token
    `[A-Z][A-Z0-9-]{1,40}` (`_SCI_COMPARTMENT_PATTERN`) instead of the
    hardcoded closed list. The SINGLE-slash branch stays restricted to
    `/REL` (the only single-slash continuation unambiguously a banner,
    not a path), so `/sci/readme`, `/sci/rel/index.html`, `scheme:/SCI`
    still reject. Subword false positives stay closed by the
    `_BANNER_OPENER` clean-boundary requirement (`ASCII//CODE` rejects —
    the SCI is preceded by `A`). Length-bounded (≤41 chars); no ReDoS
    (verified ~3 ms on a 50 K-char token). This removes the closed-list
    false-negative class entirely — the SCI grammar's four FN dimensions
    (invisibles, leading-slash runs, field delimiters, compartments) are
    now all generalized rather than enumerated.

Regression tests (`tests/test_security_two_form_scan.py`):
`TestCycle11SciGenericCompartment` (7 unlisted/listed-compartment accept
+ 5 path/subword reject + 1 ReDoS-latency).

Verification: `make ci` (CI parity) clean — full suite **1761 passed /
35 skipped / 5 xfailed in 38.07 s** at coverage **91.74%**; ruff +
mypy clean.

### Fixed (cycle-12 `/quality-gate` follow-up to PR #73 round 10, 2026-05-26)

GPT 5.4 Pro's round-10 REQUEST_CHANGES — a NEW-dimension PII finding
(not SCI; cycle-11 satisfied GPT on SCI, which dropped to non-blocking
notes): the `api_key` PII pattern's label `api[_-]?key` matched
`api_key` / `api-key` / `apikey` but NOT the whitespace form
`api key:` / `api\tkey:` / `api\xa0key:` (NBSP) / `api​key:` (ZWSP) —
so an API-key secret with a space evaded PII detection even with the
two-form scan (the label never accepted a space).

**Security (`security.py`)**:

  - **`api_key` whitespace tolerance** (GPT round 10): label widened to
    `api(?:[_-]|\s+)?key` — accepts underscore, hyphen, OR whitespace
    between `api` and `key`. This was the LAST rigid PII/PHI separator
    (audit confirmed SSN/CCN/MRN/DOB/patient_name/TOP-SECRET are all
    already whitespace-tolerant or single-word); the whitespace-
    tolerance theme is now comprehensively closed across every pattern.
  - **`SCI//README` behavior pinned** (GPT round-10 non-blocking): the
    cycle-11 generic compartment token flags `SCI//README` (double-slash
    compartment shape → conservative TACTICAL flag) while the path form
    `/sci/readme` (single-slash, lowercase) rejects. Pinned with tests
    so the regex doesn't silently calcify.

Regression tests (`tests/test_security_two_form_scan.py`):
`TestCycle12ApiKeyWhitespace` (6 label-variant + 3 invisible-separator
+ 1 benign-prose) and `TestCycle12SciReadmeBehaviorPinned` (2).

Verification: `make ci` (CI parity) clean — full suite **1773 passed /
35 skipped / 5 xfailed in 156.55 s** at coverage **92.02%**; ruff +
mypy clean.

### Fixed (cycle-13 `/quality-gate` follow-up to PR #73 round 11, 2026-05-26)

GPT 5.4 Pro's round-11 REQUEST_CHANGES: a regression the cycle-11
generic-compartment widening introduced. Because the SCI pattern was
matched against the UPPER-CASED query, the generic compartment token
classified ordinary lowercase path/URI text as SCI —
`path=//sci//readme`, `http://sci//index`, `/sci//readme` all matched
(after upper-casing, `readme` → `README` looked "all-caps") and wrongly
`force_offline`'d in TACTICAL mode.

**Security (`security.py`)** — case-aware SCI matching:

  - The SCI pattern is now matched against the **ORIGINAL-case** query
    (not `query.upper()`), with a **case-SENSITIVE** bare-branch
    compartment token (`[A-Z][A-Z0-9-]{1,40}`). Real IC compartments
    (NOFORN, GAMMA, TK, FVEY) are UPPERCASE; path/URI segments (readme,
    index, docs) are lowercase — so the case is the discriminator that
    finally resolves the cycle-9↔11 FN/FP oscillation (closed-list FN
    on unlisted compartments ↔ generic-token FP on lowercase paths).
  - Implementation: the SCI pattern is compiled WITHOUT `re.IGNORECASE`
    and uses inline `(?i:...)` for its structural tokens (level, `SCI`,
    `REL`) so those stay case-insensitive, while the compartment stays
    case-sensitive. The simple markers (TOP SECRET, SECRET,
    CONFIDENTIAL, NOFORN) are compiled WITH `re.IGNORECASE` and remain
    fully case-insensitive (preserving prior behavior). The level-
    prefixed branch (`<level>//SCI`) still flags regardless of tail
    case — a level establishes banner context — so only the BARE
    `SCI//<token>` branch is compartment-case-sensitive.

Regression tests (`tests/test_security_two_form_scan.py`):
`TestCycle13SciCompartmentCaseSensitivity` (7 lowercase-path reject +
5 uppercase-banner accept + 1 level-prefixed-lowercase flag + 1
simple-markers-stay-case-insensitive). Full security suite (464 tests)
unchanged-green.

Verification: `make ci` (CI parity) clean — full suite **1787 passed /
35 skipped / 5 xfailed in 146.45 s** at coverage **91.97%**; ruff +
mypy clean.

### Fixed (cycle-14 `/quality-gate` follow-up to PR #73 round 12, 2026-05-26)

GPT 5.4 Pro's round-12 REQUEST_CHANGES: the cycle-12 `api_key` fix
`api(?:[_-]|\s+)?key` accepted whitespace OR a `_`/`-` separator, but
not whitespace AROUND a separator — `api - key:` / `api _ key:` /
`api\t-\tkey:` still evaded.

**Security (`security.py`)**:

  - **`api_key` separator-whitespace** (GPT round 12): label widened to
    `api(?:\s*[_-]\s*|\s+)?key` — accepts any whitespace around an
    optional single `_`/`-`, OR pure whitespace, OR the joined forms.
    Closes every separator-whitespace combination in one pattern.

Regression tests (`tests/test_security_two_form_scan.py`):
`TestCycle14ApiKeySeparatorWhitespace` (7 label-variant + 1 tab-around-
separator + 1 benign-`apiary`-negative).

Verification: `make ci` (CI parity) clean — full suite **1796 passed /
35 skipped / 5 xfailed in 81.74 s** at coverage **91.75%**; ruff +
mypy clean.

### Fixed (cycle-15 `/quality-gate` follow-up to PR #73 round 13, 2026-05-26)

GPT 5.4 Pro's round-13 REQUEST_CHANGES raised two TACTICAL false
NEGATIVES in the SCI classified-marker scanner. Both are fixed; both
required reconciling against earlier rounds that had pulled the opposite
direction (the SCI banner boundary has been the single hardest part of
this module — see the in-code history block in `security.py`).

**Security (`security.py`)**:

  - **Lowercase-compartment bypass** (round 13, concern 2): the cycle-13
    case-sensitivity fix (which closed the round-11 lowercase-PATH false
    positive `//sci//readme`) over-corrected into a lowercase-BANNER false
    negative — `//sci//tk`, `//sci//gamma`, `//sci/rel` stopped forcing
    offline because the compartment token was uppercase-only. Resolved by
    making the compartment **uppercase-generic OR a case-insensitive
    KNOWN-compartment list** (`_SCI_KNOWN_COMPARTMENTS`: NOFORN, REL, FGI,
    TK, GAMMA, ECI, FVEY, …). A lowercase KNOWN compartment now flags
    (round 13); a lowercase UNKNOWN token (`readme`, `config`) still
    rejects (round 11 preserved). `REL` in the tail and single-slash
    branches is now `(?i:REL)` so lowercase `//sci/rel` flags while the
    `_SCI_CONT_GUARD` still rejects a path continuation
    (`/sci/rel/index.html`). The residual gap — a lowercase rendering of
    an UNLISTED compartment (`//sci//someprogram`) — is the regex-tier
    ceiling per ADR-010 (banner-vs-path on an arbitrary lowercase word is
    a semantic-scanner concern).
  - **Single-slash field-value banner** (round 13, concern 1): the
    cycle-10 opener admitted only a 0/2+-slash run after a field
    delimiter (`(?:/{2,})?`), to reject single-slash drive/URI forms
    (`C:/`, `scheme:/`) per round 6. That blanket rejection was a false
    negative for real field-value banners `classification:/TS//SCI`,
    `label=/SCI/REL`. Resolved by widening opener Case B to `/*` (any
    slash count): the discriminator is no longer the slash count but
    whether a **banner shape follows** the opener. So `C:/Users`,
    `url=/api/v1` still reject (no banner), while `classification:/TS//SCI`
    flags. This reverses round 6 for the narrow case where a single-slash
    field value is *immediately followed by a literal banner*
    (`C:/TS//SCI`, `scheme:/SCI/REL` now flag) — the documented
    round-6 ↔ round-13 tension, resolved toward the security-conservative
    direction (force-offline on a string that literally spells a
    classification banner is the safe error in a classified-content gate).

Both widenings are ReDoS-safe (verified ~3–6 ms on 50 K-char adversarial
slash runs; `/*` is a simple star on one char anchored by a fixed-width
lookbehind).

Regression tests (`tests/test_security_two_form_scan.py`):
`TestCycle15SciLowercaseKnownCompartment` (6 lowercase-known-flag +
5 lowercase-unknown-reject) and `TestCycle15SingleSlashFieldValueBanner`
(5 field-value-banner-flag + 5 no-banner-reject + 1 ReDoS). The
superseded round-6/round-9 reject assertions in `TestCycle8…`,
`TestCycle9…`, `TestCycle10…`, `TestCycle11…` were updated in place (the
flipped cases moved into the cycle-15 ACCEPT tests; the surviving
non-banner-path rejects retained) so the contract change is traceable,
not silently dropped.

Verification: `make ci` (CI parity) clean — full suite **1811 passed /
35 skipped / 5 xfailed in 83.40 s** at coverage **91.75%**; ruff +
mypy clean.

### Fixed (cycle-16 `/quality-gate` follow-up to PR #73 round 14, 2026-05-26)

GPT 5.4 Pro's round-14 REQUEST_CHANGES: the cycle-15 widenings (lowercase
known-compartment list + `(?i:REL)`) exposed a path/file-suffix false
POSITIVE in the SCI scanner. The compartment and `/REL` branches
terminated with `\b` followed by a continuation guard that only rejected a
following single `/`. Because `\b` succeeds before `-` and `.`, a
hyphenated/dotted path-or-file suffix slipped through and wrongly forced
offline in TACTICAL mode: `path=//sci//gamma-ray`, `path=//SCI//TK-demo`,
`path=/sci/rel-team`, `//SCI//ZULU-test`, `//sci//gamma.tmp`.

**Security (`security.py`)**:

  - **Banner-terminator rewrite** (GPT round 14): `_SCI_TAIL_GUARD` and
    `_SCI_CONT_GUARD` are rewritten from a negative-lookahead-on-slash
    (`(?!/(?!/...))`, which only constrained what followed a `/`) to an
    EXPLICIT POSITIVE banner terminator. After a marking token the input
    must now end, OR hit a clean banner boundary (whitespace, closing
    bracket/brace/paren/angle, quote, comma, semicolon), OR continue as a
    valid banner tail — `//` (chained compartment) or, after `<level>//SCI`,
    `/REL`. A `-`, `.`, single-`/` path, or word char rejects. This both
    preserves the round-5 fix (`/TS//SCI/readme` still rejects) and closes
    the round-14 hyphen/dot path-suffix FP class.
  - **Generic compartment arm cannot end in `-`** (GPT round 14, fix 2):
    `_SCI_COMPARTMENT_PATTERN`'s uppercase-generic arm changed from
    `[A-Z][A-Z0-9-]{1,40}` to `[A-Z](?:[A-Z0-9-]{0,38}[A-Z0-9])?` — same
    1-40 length bound, still admits INTERNAL hyphens (`SPECIAL-ACCESS`), but
    cannot terminate on one. Belt-and-suspenders behind the terminator.

ReDoS-safe (verified ~2.6-5 ms on 50 K-char slash/compartment runs and a
25 K-pair hyphen-run adversarial input).

Regression tests (`tests/test_security_two_form_scan.py`):
`TestCycle16SciBannerTerminator` (7 hyphen/dot-suffix-reject + 7
clean-terminator-accept incl. comma/paren/angle/semicolon/bracket and an
all-caps internal-hyphen compartment + 1 ReDoS).

Verification: `make ci` (CI parity) clean — full suite **1826 passed /
35 skipped / 5 xfailed in 83.02 s** at coverage **91.75%**; ruff +
mypy clean.

### Fixed (cycle-17 `/quality-gate` follow-up to PR #73 round 15, 2026-05-27)

GPT 5.4 Pro's round-15 REQUEST_CHANGES: the cycle-16 positive banner
terminator set was incomplete, producing two false NEGATIVES and leaving a
third uncovered in the SCI scanner.

**Security (`security.py`)**:

  - **Colon terminator** (GPT round 15): `Classification: TS//SCI:` is a
    ubiquitous banner form, but `:` was absent from the cycle-16 terminator
    set `[\s)\]}>"',;]` even though it is structurally identical to the `,`
    and `;` already accepted. Added `:` to both `_SCI_TAIL_GUARD` and
    `_SCI_CONT_GUARD` (a cycle-16 omission, not a behavior change).
  - **Backtick opener + terminator** (GPT round 15): markers are routinely
    wrapped in markdown inline code (`` `TS//SCI` ``); backtick was neither a
    clean opener nor a clean terminator, so code-span-wrapped banners evaded.
    Added backtick to `_BANNER_OPENER`'s clean-boundary class and both SCI
    guards (it joins the quote/bracket set it belongs with).
  - **Sentence-final punctuation** (GPT round 15): a banner ending a sentence
    (`TS//SCI.`, `Marked TS//SCI!`, `SCI//NOFORN?`) was missed. Added a nested
    lookahead alternative `[.!?](?=$|\s)` — `. ! ?` terminate ONLY when
    immediately followed by end-of-input or whitespace. This flags sentence-
    final banners while the round-14 dotted path/file suffixes
    (`//SCI//TK.bak`, `.tar.gz`, `.bak.old`) STILL reject, because the char
    after the `.` there is not EOI/whitespace.
  - **Comment correction** (GPT round 15 non-blocking): the per-marker-pattern
    header comment still claimed matching against `query.upper()`; corrected
    to reflect the cycle-13 original-case matching (the compile-loop CASE
    HANDLING comment remains the authoritative source).

**Dialogue refinements** (Claude↔GPT 5.4 Pro tier-ceiling dialogue,
`/claude-gpt-dialogue`, GPT round-15 convergence) — four tightenings GPT
required for a clean pass, all applied:

  - **Sentence punctuation + ASCII closers**: `. ! ?` may be followed by
    zero-or-more ASCII closing wrappers (`` ) ] } > " ' ` ``) before
    whitespace/EOI, so `TS//SCI."`, `(TS//SCI.)` flag (the bare
    `[.!?](?=$|\s)` missed these).
  - **Pipe `|` terminator**: table/log forms `|TS//SCI|`, `|SCI//TK|` flag
    (`|` was already a left field-delimiter).
  - **ASCII-only boundary whitespace** `[ \t\n\r\f\v]` (not `\s`): makes the
    ASCII-delimiter contract honest. NB — because `scan()` applies NFKC
    normalization UPSTREAM, NBSP/EM/IDEOGRAPHIC space and FULLWIDTH COLON fold
    to ASCII and still FLAG; only NFKC-STABLE non-ASCII punctuation (em/en
    dash, curly quotes) defers (KNOWN_ISSUES #F14).
  - **Documented** the cycle-15 `classification:/TS//SCI` field+optional-slash
    left form in the contract.

ReDoS-safe (verified ~2.7-5 ms on 50 K-char slash/compartment/hyphen,
sentence-punctuation, and closing-wrapper adversarial runs).

This is the regex-tier completion of the SCI banner-boundary delimiter
contract — the CLOSED, ENUMERATED ASCII opener/terminator set, operating on
NFKC-normalized input. Edge cases OUTSIDE that set — NFKC-stable non-ASCII
delimiters (em/en dash, curly quotes; KNOWN_ISSUES #F14) and lowercase-unlisted
compartments (#F13) — are the documented regex-tier ceiling deferred to the
ADR-010 semantic-scan tier. The tier-boundary was negotiated and ratified in
the Claude↔GPT dialogue; see `.quality-gate/cycle17-findings.md`.

Regression tests (`tests/test_security_two_form_scan.py`):
`TestCycle17SciColonBacktickSentenceTerminators` (11 colon/backtick/sentence
accept + 6 dotted/hyphen-suffix reject + 1 ReDoS) and
`TestCycle17DialogueRefinements` (9 sentence-closer/pipe accept + 5
NFKC-normalized-Unicode-flag + 4 NFKC-stable-non-ASCII-defer).

Verification: `make ci` (CI parity) clean — full suite **1862 passed /
35 skipped / 5 xfailed in 82.92 s** at coverage **91.75%**; ruff +
mypy clean.

### Added

- **Wave-22: PR-B1 follow-up — frontier providers + generator + evaluator
  + reporter + CLI integration** (ADR-009 LLM-Driven Red Team Engine).
  Building on the B1 foundation (PR #64), this wave completes B1 with:
  - **3 frontier-model providers** (pure-httpx, no SDK runtime deps):
    - `AnthropicProvider` (`src/aipea/redteam/providers/anthropic.py`):
      Claude Opus 4.7 via Messages API SSE streaming with adaptive
      thinking (`thinking: {type: "adaptive"}`). Manual `budget_tokens`
      returns 400 on Opus 4.7+; streaming required to avoid HTTP
      timeout on extended-thinking requests. Headers per
      `docs.anthropic.com/en/api/streaming`.
    - `OpenAIResponsesProvider` (`src/aipea/redteam/providers/openai_responses.py`):
      gpt-5.5-pro via Responses API background mode
      (`background: true, store: true`). Reuses `poll_until_terminal`
      with 25-min cap. POST /v1/responses → poll GET /v1/responses/{id}
      → POST /v1/responses/{id}/cancel on timeout.
    - `OpenAICodexProvider` (`src/aipea/redteam/providers/openai_codex.py`):
      gpt-5.3-codex via the same Responses-API background pattern; thin
      subclass of `OpenAIResponsesProvider`.
  - **`RedTeamGenerator`** (`src/aipea/redteam/generator.py`):
    technique-seeded prompts for the 8 OWASP categories + iterative
    refinement (≤3 rounds). Caught payloads from round N are fed back
    as "evade these patterns" seeds into round N+1. Multi-payload
    response splitting + amortized cost/latency attribution.
  - **`RedTeamEvaluator`** (`src/aipea/redteam/evaluator.py`):
    runs `SecurityScanner.scan()` + computes TF-IDF cosine novelty
    score against the OWASP corpus. Stdlib-only TF-IDF
    (`collections.Counter` + `math`) per the
    `codingtechroom.com/.../tf-idf-similarity` reference; no sklearn
    runtime dep. Skips `error`-tagged provider rows.
  - **`RedTeamReporter`** (`src/aipea/redteam/reporter.py`):
    writes JSON corpus-extension file +
    `docs/security/redteam-report-<date>.md` audit report. Includes
    per-technique catch rate, top-10 novel-bypass list, dual-use
    disclaimer (mirrors Garak/Giskard convention).
  - **CLI integration** (`src/aipea/cli.py`):
    new `redteam` sub-typer with 3 subcommands —
    `aipea redteam run --provider {ollama|anthropic|openai|codex}
    --technique {paraphrase|...} --num N --rounds N`,
    `aipea redteam list-techniques`,
    `aipea redteam list-providers`.
  - **Public API**: `__all__` extended 50 → 60 with `RedTeamProvider`,
    `RedTeamResult`, `RedTeamGenerator`, `RedTeamEvaluator`,
    `RedTeamReporter`, `Technique`, `OllamaProvider`,
    `AnthropicProvider`, `OpenAIResponsesProvider`,
    `OpenAICodexProvider`. ASK-first per CLAUDE.md §2.2.
  - **`pyproject.toml [project.optional-dependencies] redteam = []`**
    extras group. Zero new runtime deps (httpx + typer already
    present); the empty extras express adoption intent.
  - **`.github/scripts/gpt_review.py` refactor — DEFERRED to follow-up
    PR**: the helper now lives at `src/aipea/redteam/_polling.py` (B1
    foundation, PR #64), but the consumer-side refactor of the CI script
    is deferred to a separate PR landed AFTER this PR merges to `main`.
    Reason: when both the workflow file AND the script change in the
    same PR, `anthropics/claude-code-action@v1` rejects the run via its
    "workflow validation" safety check (workflow on PR head must match
    `main` exactly). Deferring the consumer refactor keeps this PR's
    workflow surface unchanged. Producer side (the helper) remains
    exported under `aipea.redteam._polling.poll_until_terminal`.

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
  and the merged VC review editorial banner. *(PR #58, b4b6df2,
  2026-04-24)*

### Phase 4.b — Claims-audit calibration (2026-05-02, PR #69)

- **SPECIFICATION.md §1.3** "Security by default" design principle:
  rewrote to make input-inspection-not-enforcement contract explicit;
  cross-linked README + SECURITY.md.
- **SPECIFICATION.md §3.1.3 ComplianceHandler table**: new "Integrator's
  responsibility" right-most column making the "configuration metadata,
  not enforcement" boundary explicit. Source-code anchor:
  `src/aipea/security.py:727-819`. Old "Yes / Yes / Yes" Encryption /
  PHI Redaction / Force Offline columns reframed as advisory boolean
  fields the integrator's application layer reads.
- **CLAUDE.md §7.2 Compliance Modes**: rewrote 3-column "Restrictions"
  table into 4-column layout — "What AIPEA enforces in code" / "What
  AIPEA flags as advisory metadata" / "Integrator must do".
- README and SECURITY.md found already calibrated; no edits needed.
- Adapter docs (`docs/integration/{aegis,agora}-adapter.md`) had no
  compliance claims to audit.
- *(PR #69, e4ae911, 2026-05-02)*

### Phase 4.c — Adversarial corpus expansion + nightly CI (2026-05-02, PR #70)

- **`tests/fixtures/adversarial/promptinject.json`** (NEW; 17
  entries; MIT) — agencyenterprise/PromptInject `prompt_data.py`
  extracted via override-verb regex heuristic. Canonical
  instruction-override family.
- **`tests/fixtures/adversarial/jbb_behaviors.json`** (NEW; 200
  entries; MIT) — JailbreakBench JBB-Behaviors harmful (100) +
  benign FPR control (100). HuggingFace dataset CSVs.
- **`tests/fixtures/adversarial/garak_promptinject.json`** (NEW; 43
  entries; Apache-2.0) — NVIDIA/garak probes
  `{promptinject,dan,latentinjection}.py` extracted via override-verb
  regex. Paraphrase-coverage breadth.
- **`tests/fixtures/adversarial/SOURCES.md`** (NEW) — full provenance
  per corpus, license attribution, Apache-2.0 NOTICE for Garak,
  re-extraction reproducibility notes.
- **`tests/test_adversarial.py`**: added `_compute_results_by_source()`
  helper + `TestExtendedBaselinePerSource` class with FPR-inverted
  assertion path for `jbb_benign_fpr` source. `_generate_baseline()`
  additively writes `by_source` map.
- **`tests/fixtures/adversarial/baseline.json`**: regenerated with
  `by_source` map (additive schema).
- **`.github/workflows/adversarial.yml`** (NEW) — nightly cron
  `'37 4 * * *'` non-gating; Blacksmith runner; SHA-pinned actions;
  `continue-on-error: true`; writes per-corpus hit-rate Markdown to
  `$GITHUB_STEP_SUMMARY`; uploads `baseline.json` artifact (30-day).
- **`tests/render_adversarial_summary.py`** (NEW; ~80 LOC) — emits
  Markdown table for `$GITHUB_STEP_SUMMARY`.
- **`docs/metrics.md`** — new "Adversarial evaluation hit rates"
  section with per-corpus table including OWASP per-category losses
  (delimiter / encoding / multi-language / paraphrase / role-play /
  elicitation: candidates for future targeted regex extensions per
  ADR-005 §C.1, NOT a classifier swap).
- **`pyproject.toml`** `[tool.ruff.lint.per-file-ignores]`: extended
  for the two new CLI-style helpers (`tests/render_adversarial_summary.py`,
  `tests/test_adversarial.py`) — T20 + E501 on table-row prints,
  matching the precedent in `src/aipea/cli.py`.
- *(PR #70, f0a685a, 2026-05-02)*

### Documentation (2026-04-24 → 2026-05-02)

- **`TODO.md`**: deferred SOW counsel-handoff work to a focused
  future session with explicit resume trigger; engineering capacity
  redirected to v1.7.0 Phase 4.b/4.c per the approved plan.
  *(PR #68, 898a4c9, 2026-05-02)*
- **`docs/positioning.md`** (NEW; ≤500 words) — formalizes the
  open-core step-up: AIPEA detects, AEGIS enforces, Agora IV
  orchestrates. Closes the ADR-005 §12 Q5 commitment and PR #52
  review §7.5 diligence question. *(this PR)*
- **`docs/adopters.md`**: bumped Agora IV row to v1.6.2 (was v1.6.1)
  with HTTP_TIMEOUT-deprecation migration note. *(this PR)*

### Removed FROM `[Unreleased]`

- The "forthcoming ADR-005" placeholder language in TODO.md,
  CHANGELOG.md, docs/metrics.md, and the merged VC review banner —
  ADR-005 has shipped (PR #58), so the placeholders are obsolete.
  *(superseded by ADR-005's actual content)*

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
