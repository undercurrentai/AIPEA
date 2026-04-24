# TODO — AIPEA

Canonical tracker for all pending work. Replaces scattered items from ROADMAP.md,
NEXT_STEPS.md, KNOWN_ISSUES.md, SPECIFICATION.md, and discovery findings.

Last updated: 2026-04-24 (v1.6.2 content fully merged to `main`;
awaiting PyPI release cut).

> **Architect's release plan**: see `~/.claude/plans/you-are-the-senior-dynamic-micali.md`
> for the approved v1.6.2 → v1.7.0 → v1.8.0 → v2.0.0rc1 → v2.0.0 roadmap.
> **PR #52 adversarial VC review response plan**: see
> `~/.claude/plans/pr52-vc-adversarial-response-2026-04-24.md` for the
> 23-finding triage matrix, user decisions (2026-04-24), and sequenced
> execution against v1.6.2 / v1.7.0 / v1.8.0.
>
> **Release-label note**: PR #53 was authored with a `docs(v1.6.3):`
> commit prefix, which was the PR-level working name used during
> drafting. At release-cut time, the content ships as part of the
> single **v1.6.2** PyPI release alongside PR #51 and PR #52 content
> — no separate v1.6.3 release is planned. References to "v1.6.3"
> elsewhere in this file or the response plan refer to that
> PR-working-label, not a distinct PyPI version.

---

## PR #52 Adversarial VC Review — Response (2026-04-24)

PR #52 merged 2026-04-24 at squash `f92d253`. Response plan approved the
same day. The 23 review findings are triaged 13 Accept / 7 BD / 2 Decline
/ 1 Defer. Execution sequenced:

- [x] **Phase 1**: Merge PR #52 with editorial banner.
  ✅ 2026-04-24, squash `f92d253`.
- [x] **Phase 2**: Telemetry dashboard (pepy.tech + GitHub badges in
  `docs/metrics.md`, honest-gaps section, README linkage, pinned-
  Discussion #54). ✅ 2026-04-24, PR #53 squash `712b182`. Ships with
  v1.6.2 PyPI release.
- [x] **Phase 3**: Second-committer scope-of-work v0.
  ✅ 2026-04-24, drafted at `~/.claude/plans/aipea-second-committer-sow-v0.md`
  (not committed). 6 open questions in §12 need maintainer + counsel
  review before v1 candidate distribution. Target: signed contract by
  2026-06-30; contractor start 2026-07-15.
- [x] **Phase 4.a**: [`docs/adr/ADR-005-pr52-vc-adversarial-review-response.md`](docs/adr/ADR-005-pr52-vc-adversarial-review-response.md)
  — shipped 2026-04-24 (authored for v1.7.0 but landed early alongside
  v1.6.2 release cycle). §12 per-diligence-question appendix folded
  into the ADR.
- [ ] **Phase 4.b**: Claims-audit sweep across README / SECURITY.md /
  SPECIFICATION.md / CLAUDE.md / aegis-adapter.md / agora-adapter.md
  (v1.7.0). Triple-AI gate will fire on this PR.
- [ ] **Phase 4.c**: Adversarial benchmark suite in `tests/adversarial/`
  + non-gating nightly CI (v1.7.0).

**Manual follow-ups (outside repo-editable scope)**:
- Pin GitHub Discussion #54 via the UI (GraphQL `pinDiscussion`
  mutation is not exposed; one-click UI action: Discussion #54 →
  "..." → "Pin discussion" → "Chevron Up").
- Review SOW v0 §12 open questions; produce v1 for candidate
  distribution.

Declined (with full rationale + Revisit triggers in [ADR-005 §C.1/C.2](docs/adr/ADR-005-pr52-vc-adversarial-review-response.md)):
- DistilBERT-scale classifier swap (review §5.1 / §10 Phase 1) — violates
  stdlib + httpx core; collapses AEGIS step-up.
- Opt-out install telemetry (review §10 Phase 0) — privacy-hostile;
  `pypistats` + GitHub Insights give same signal free.

Deferred:
- Independent pentest ($25-40K, review §5.4) — until post-v1.7.0 claims
  audit completes.
- Clinical reviewer for PHI tranche ($2-5K, review §10 Phase 1) — v1.8.0
  PHI catalog expansion ships behind opt-in flag pending sign-off.
- Federated learning endpoint (review §10 Phase 2) — v3.0+ architectural
  change; not v1.x scope.

---

## Release Roadmap (approved 2026-04-23)

| Release | Target | State | Scope |
|---|---|---|---|
| **v1.6.2** | 2026-05-09 | **on `main`; awaiting PyPI cut** | Doc sync + 3 code cleanups (HTTP_TIMEOUT DeprecationWarning, DRY URL resolver; rolling-avg was a false positive) + `benchmarks/` delete + P5e trio + PR #52 adversarial-review merge + v1.6.3-labeled telemetry dashboard (PR #53). All shipped to `main` via PRs #51 + #52 + #53 on 2026-04-24. |
| **v1.7.0** | 2026-06-15 | queued | `AIPEAConfig.source_of()` + CLI migration. AEGIS adapter contract audit + AIPEA-side integration test. `DeprecationWarning` on `create_model_specific_prompt`. `MIGRATION.md` v0 draft. `tests/test_models.py`. **+ PR #52 Phase 4.a** (ADR-005 + §12 appendix) **+ Phase 4.b** (claims audit) **+ Phase 4.c** (adversarial benchmark suite). |
| **v1.8.0** | 2026-08-01 | queued | AgoraIV migration PRs (AgoraIV adopts `source_of()`, drops deprecated imports). PII catalog expansion (tranche 1: phone, email, street-address, bank-account, IPv4-private). PHI catalog expansion (tranche 2: medication names, ICD-10, CPT, DEA) — **behind opt-in flag pending clinical-reviewer sign-off** (Plan B #20 deferred). `docs/MAINTAINERS.md`. `.github/CODEOWNERS` updated with second committer. Final minor pre-rc1. |
| **v2.0.0rc1** | 2026-09-01 | queued | Remove `FEDRAMP`, `HTTP_TIMEOUT` alias, `create_model_specific_prompt`. Inline `TierProcessor` ABC. Remove `phi_redaction_enabled` if v1.7.0 claims audit finds it unused. Finalize `MIGRATION.md`. |
| **v2.0.0** | 2026-10-22 | queued | GA (≥2 weeks rc1 soak, zero unresolved blockers, AgoraIV migrated off deprecated symbols). |

Rationale for the timing (full evidence in the plan file): NumPy NEP 23
floor is 1 year deprecation→removal; PEP 387 is 2 minor versions; SQLAlchemy
1.4→2.0 was 22 months. AIPEA's v1.3.4 FedRAMP deprecation is ≈2 weeks
old; 6 months + 2 minor releases is the minimum defensible window.

---

## Immediate (v1.6.2) — ON `main`, awaiting PyPI cut (target 2026-05-09)

All sub-items shipped via PRs #51 + #52 + #53 on 2026-04-24. Cutting the
release is a version-bump + tag operation — no remaining code work.

### A. Doc version sync — COMPLETE (2026-04-23 via `/docs-sync`)

All metadata headers synced to v1.6.1 state. These items from the prior
cycle are closed:

- [x] **`SPECIFICATION.md:2`** — bumped header to `Version 1.6.1 | 2026-04-22`
- [x] **`SPECIFICATION.md:1431-1432`** — footer bumped to `v1.6.1 released; PyPI 2026-04-23`
- [x] **`SPECIFICATION.md §7.4`** — already synced in v1.6.1 (line 933 + list of 10 patterns)
- [x] **`SPECIFICATION.md §10`** — rewrote roadmap pointer (TODO.md canonical; ROADMAP.md historical; P1-P5 corrected)
- [x] **`CLAUDE.md:2`** — bumped to `v1.6.1 | Updated: 2026-04-22`
- [x] **`CLAUDE.md:14`** — `last_audit: 2026-04-22`
- [x] **`CLAUDE.md:32`** — `Source LOC ~10,662 (as of v1.6.1, 2026-04-22)`
- [x] **`CLAUDE.md:482`** — References entry rewritten (P1-P4 → P1-P5 historical)
- [x] **`CONTRIBUTING.md:120`** — footer bumped to v1.6.1
- [x] **`SECURITY.md:102`** — Effective date bumped to v1.6.1
- [x] **`TODO.md:6` (this file) header** — updated
- [x] **`MEMORY.md`** — test/LOC counts verified; discovery-audit note added

**v1.6.2 re-sync** (after the release below ships): bump all v1.6.1 →
v1.6.2 headers, same pattern.

### B. Code-quality cleanups — COMPLETE (2026-04-24 via PR #51)

From `/discover` 2026-04-23; revised per the approved plan.

- [x] **[MEDIUM] `src/aipea/search.py`** — `HTTP_TIMEOUT` alias now emits
  `DeprecationWarning` via PEP 562 `__getattr__` AND respects runtime
  config changes (solves #81 as a side effect). AgoraIV's 14 references
  continue to work. Hard deletion scheduled v2.0.0rc1. 4 regression
  tests in `TestV162HTTPTimeoutDeprecation`.
- [x] **[MEDIUM] `src/aipea/search.py`** — `_resolve_provider_url(env_var,
  config_field)` helper extracted; `_resolve_exa_api_url` and
  `_resolve_firecrawl_api_url` delegate. No behavior change.
- [x] **[LOW] `src/aipea/enhancer.py:1334-1342`** — **FALSE POSITIVE**
  from `/discover`; code already correctly special-cases `count == 1`.
  No code change required; documented in CHANGELOG.

**Deferred to v1.7.0** (bundled with `source_of()` work below):
- `src/aipea/cli.py:84, 117, 129, 139, 309` — migrate `cfg._sources`
  reads to `source_of()` accessor.

### C. Dead-code deletion (Decision 2 — `benchmarks/`) — COMPLETE (PR #51)

- [x] **Deleted `benchmarks/`** — stubs removed; accompanying cleanup:
  `tools/ci/enforce_perf_gate.py` deleted, `Makefile` `perf:` target +
  `.PHONY` entry removed, `tools/ci/generate_scorecard.py` LINTERS
  tuple entry removed.

### D. Commercial validation surface (Decision 5 — P5e trio) — COMPLETE (PR #51 + #53)

Shipped alongside v1.6.2; non-engineering-blocking but investor-visible.

- [x] **`docs/adopters.md`** — Agora IV + AEGIS named adopters with
  integration patterns and production signals.
- [x] **`docs/metrics.md`** — initial version in PR #51, enriched in
  PR #53 with live pepy.tech + GitHub-native badges, honest-gaps
  section with explicit zero-counts (funnel conversion, external
  contributors, design partners, external PRs), opt-out install
  telemetry declined-by-policy note.
- [x] **`case-studies/agora-iv-v1.md`** — 10-week Wave 18/19/20
  narrative with three highlighted security fixes and honest-limits
  section.
- [x] **`README.md`** — "Adoption & metrics" block linking the trio
  (shipped PR #53).
- [x] **GitHub Discussion #54** — "Are you using AIPEA? Tell us how —
  no NDA required" adopter-outreach thread opened 2026-04-24.
  **Manual follow-up**: pin via GitHub UI.

**Parked (BD work, not engineering)**:
- P5e item (4) — design-partner outreach to HIPAA / TACTICAL-defense /
  general-SaaS orgs. Needs BD capacity decision; not for AIPEA repo to
  execute unilaterally.

---

## Short-term (v1.7.0) — target 2026-06-15

### E. `AIPEAConfig.source_of()` public accessor (Decision 3)

- [ ] **Add `source_of(field: str) -> str` method** in `src/aipea/config.py`
  — keep `_sources` private; expose provenance via additive public method.
  Pattern-match dynaconf / pydantic-settings convention.
- [ ] **Migrate 5 CLI sites** at `src/aipea/cli.py:84, 117, 129, 139, 309`
  from `cfg._sources.get(...)` to `cfg.source_of(...)`.
- [ ] **Add `tests/test_config.py::test_source_of_public_accessor`** —
  public accessor contract; existing `_sources` tests remain as
  internal-invariant coverage.
- [ ] **ADR-007** (optional but encouraged) — formalize public/private
  boundary decision in an ADR so v2.0.0+ can't accidentally expose more
  internals. (ADR-005 and ADR-006 are reserved for PR #52 VC-response
  and v2.0 deprecation batch respectively per 2026-04-24 decision.)

### F. AEGIS adapter contract audit (Decision 4 — pivotal reframing)

The AEGIS adapter at `aegis-governance/src/integration/aipea_bridge.py`
**already exists** (verified via direct filesystem check:
committed, pytest-9-tested, included in CDK `cdk.out/` for deployment).
AIPEA's job is not to build the adapter — it's to lock in the API
contract the adapter consumes.

- [ ] **Contract audit**: enumerate AIPEA public symbols imported by
  `aipea_bridge.py`; confirm every one is in `__init__.py` `__all__`.
  ASK-first (per CLAUDE.md §2.2) for any additions.
- [ ] **`tests/test_aegis_integration.py`** — NEW. Graceful `pytest.skip`
  when `aegis-governance` isn't installed; exercises the
  `preprocess_claim` → `enhance_prompt` round-trip end-to-end.
- [ ] **Rewrite `docs/integration/aegis-adapter.md`** — from "planned
  adapter spec" framing to "existing integration consumer guide" framing.
  Field-mapping matrix, compatibility note ("tested against
  aegis-governance v1.1.0+").

### G. Deprecation warnings for v2.0.0 removals

- [ ] **`src/aipea/engine.py` — `create_model_specific_prompt`** — add
  `DeprecationWarning` on call; point to `formulate_search_aware_prompt`
  as replacement. 4 AgoraIV legacy-migrated tests will see the warning;
  v1.8.0 migration PR upstream into AgoraIV addresses those.
- [ ] **`docs/MIGRATION.md` v0 draft** — NEW. Section per removal
  (FedRAMP, HTTP_TIMEOUT, create_model_specific_prompt, TierProcessor).
  Finalized at v2.0.0rc1.

### H. Test-coverage hygiene

- [ ] **`tests/test_models.py`** — edge-case tests for `QueryAnalysis`
  dataclass (to_dict serialization, boundary values, None handling).
  Long-deferred; closes the v1.4.0-cycle item and the 2026-04-22 review
  finding.
- [ ] **Exception chaining audit** — standardize `raise X from e` in
  `engine.py`. `engine.py:371` bare `raise` is **intentional** (re-raises
  active exception per 2026-04-22 review); audit remaining sites only.
- [ ] **CLI coverage → 85%+** — currently 78%; ~67 untested error-path
  lines in `configure` / `doctor` / `seed-kb`.

### I. Governance templates (populate real values)

- [ ] **`ai/system-register.yaml`** — replace `id: example-llm` →
  `id: aipea`, `owner: team-ml@example.com` → `owner: @joshuakirby`,
  `last_reviewed: "YYYY-MM-DD"` → actual date.
- [ ] **`ai/model-card.yaml`** — replace `name: example-llm` →
  `name: aipea-v1.7.0` (AIPEA's own preprocessing model, not a 3rd-party
  LLM).
- [ ] **`ai/risk-register.yaml`** — populate both `review_date:` fields
  (lines 22, 41) with real quarterly dates.

### J-bis. PR #52 Phase 4 (ships with v1.7.0)

Per the approved PR #52 response plan. Each is its own PR; triple-AI
gate fires on 4.b (claims audit touches security.py indirectly via
source-link anchors) and 4.c (CI workflow change).

- [ ] **Phase 4.a** — `docs/adr/ADR-005-pr52-vc-adversarial-review-response.md`
  (≤250 lines, triage matrix + user decisions + critical path) +
  append `## 12. Maintainer Response (2026-04-24)` section to the
  merged VC review walking §7's 12 diligence questions.
- [ ] **Phase 4.b** — Claims-audit sweep across README / SECURITY.md /
  SPECIFICATION.md / CLAUDE.md / `docs/integration/aegis-adapter.md` /
  `docs/integration/agora-adapter.md` against `src/aipea/security.py`.
  Rewrite narrower-than-code claims; retract unbacked ones; add
  source-code link anchors. Emit `DeprecationWarning` on any surface
  that claims enforcement the code doesn't provide. File ADR-006 for
  the v2.0 deprecation batch (per 2026-04-24 numbering decision).
- [ ] **Phase 4.c** — `tests/adversarial/` corpus suite (OWASP LLM Top
  10 + LLM-Attacks AdvBench subset + Garak subset; MIT-compatible
  licenses only) + `.github/workflows/adversarial.yml` (nightly
  non-gating at first); baseline hit-rate published to
  `docs/metrics.md` **including losses**.

---

## Medium-term (v1.8.0 → v2.0.0rc1 → v2.0.0)

### J. v1.8.0 — target 2026-08-01

- [ ] **AgoraIV migration PRs** — contribute upstream PRs to AgoraIV
  swapping the 14 `HTTP_TIMEOUT` references and 4
  `create_model_specific_prompt` shim references to non-deprecated APIs.
  Unblocks rc1 without breaking AgoraIV CI.
- [ ] **PII catalog expansion (tranche 1)** — add `phone_us`, `email`,
  `street_address` (US), `bank_account` (with routing-context
  proximity), `ipv4_private` (RFC 1918). Regression tests under
  `TestV180PiiCatalogExpansion`. Addresses PR #52 review §5.2 finding
  #3. File **ADR-008** for rationale (additive, not a removal — so
  not part of ADR-006 v2.0 deprecation batch).
- [ ] **PHI catalog expansion (tranche 2)** — add `medication_name`
  (top-500 generic+brand, FDA Orange Book MIT-compat extract),
  `icd10_code`, `cpt_code`, `dea_number` (with checksum). **Behind
  opt-in flag pending clinical-reviewer sign-off** — clinical
  reviewer contract deferred per 2026-04-24 user decision; ships
  with "pending clinical review" CHANGELOG marker. Regression tests
  under `TestV180PhiCatalogExpansion`. Addresses PR #52 review §5.2
  finding #4.
- [ ] **`docs/MAINTAINERS.md`** — NEW. Module ownership table,
  response SLAs, escalation paths, PR-review rotation. Co-authored
  with the contracted second committer once onboarded.
- [ ] **`.github/CODEOWNERS`** — update to list the contracted second
  committer as human backup reviewer on security-critical paths.
  Depends on Plan B #16 contract signed by 2026-06-30.
- [ ] **Final-pass quality gates** — any lingering minor work picked up
  between v1.7.0 and rc1.

### K. v2.0.0rc1 — target 2026-09-01

See §Declined/v2.0.0 removal scheduled below — this is the "do it" release
for those items.

### L. v2.0.0 — target 2026-10-22 (GA)

- [ ] **Standalone Service Mode** *(stretch)* — REST API wrapping the
  library (`SPECIFICATION.md §8.4`). Architectural addition, not a
  removal; optional for v2.0.0, fine to push to v2.1.0 if scope tight.
- [ ] **BDI Reasoning (P4, conditional)** — only if AIPEA evolves into
  an autonomous agent participating in multi-agent orchestration. See
  `docs/ROADMAP.md §P4`. Not blocking v2.0.0 ship.

---

## Declined / v2.0.0 removal scheduled (rc1 = 2026-09-01)

Hard removals batched for the v2.0.0 breaking-changes window. All four
items have documented deprecation cycles before removal (v1.3.4/v1.6.2/
v1.7.0 → v2.0.0rc1).

- [x] ~~**FedRAMP enforcement**~~ — declined 2026-04-11 (Path B, ADR-002);
  deprecated v1.3.4; **hard removal v2.0.0rc1**.
- [ ] **`PromptEngine.create_model_specific_prompt` removal** — zero
  production callers in AIPEA; 4 AgoraIV legacy-migrated-test references
  migrated in v1.8.0. Deprecation added v1.7.0; hard removal v2.0.0rc1.
  6 unit tests in `test_engine.py` drop.
- [ ] **`TierProcessor` ABC inlining** — single concrete impl,
  zero-blast-radius (ABC not exported); no deprecation needed. Inline at
  v2.0.0rc1 (~68 LOC net delete).
- [ ] **`search.py:114-116 HTTP_TIMEOUT` alias removal** — 14 AgoraIV
  references migrated in v1.8.0. Deprecation added v1.6.2; hard removal
  v2.0.0rc1.
- [ ] **`phi_redaction_enabled` boolean field removal** — per PR #52
  review §5.3 finding #6, no code consumes this flag. v1.7.0 Phase 4.b
  claims audit confirms; if unused, remove at v2.0.0rc1. If some caller
  reads it, document semantics and keep.

---

## Open Questions — CLOSED

All five resolved 2026-04-23. See `~/.claude/plans/you-are-the-senior-dynamic-micali.md`
for the decision and evidence on each.

- [x] ~~**v2.0.0 window — when?**~~ → **Decision 1**: target 2026-10-22; rc1
  2026-09-01. See Release Roadmap above.
- [x] ~~**`benchmarks/` — live or orphaned?**~~ → **Decision 2**: delete
  in v1.6.2. No pytest-benchmark activation. Absolute-bound smoke tests
  only if post-v2.0.0 need emerges. See Immediate §C.
- [x] ~~**CLI `cfg._sources` — private contract or oversight?**~~ →
  **Decision 3**: oversight; add public `source_of()` in v1.7.0, keep
  `_sources` private. See Short-term §E.
- [x] ~~**AEGIS API stability — adapter unblocked?**~~ → **Decision 4**:
  adapter **already exists** in `aegis-governance/src/integration/aipea_bridge.py`;
  AIPEA work is contract audit + integration test, not greenfield. See
  Short-term §F.
- [x] ~~**P5e commercial validation — any movement?**~~ → **Decision 5**:
  no movement; ship unilateral trio in v1.6.2 (adopters.md, metrics.md,
  case-studies/agora-iv-v1.md); design-partner outreach parked as BD
  team-discussion. See Immediate §D.

---

## Opportunities (nice-to-haves)

### Testing & CI

- [ ] **Mutation testing (`make mut`) in CI** — `[tool.mutmut]` block
  exists in `pyproject.toml:110-111` but no `make mut` target and no CI
  job. Ratchet mutation-score floor up 1% per release. See
  `docs/ROADMAP.md §P5d` half 1. No new dependency needed.
- [x] ~~**Benchmark regression detection (`make perf`) in CI**~~ —
  CLOSED 2026-04-23 per Decision 2; see Immediate §C.
- [ ] **SBOM generation in `publish.yml`** — closer to table stakes for
  a "REGULATED + AI-GOVERNED" compliance-tier claim than a nice-to-have,
  per `/discover` 2026-04-23.

### Automation

- [ ] **Automated doc version syncing** — pre-release script or git hook
  keyed on `pyproject.toml` version changes that rewrites version + date
  headers in `SPECIFICATION.md`, `CLAUDE.md`, `TODO.md`, MEMORY.md.
  Prevents the post-release staleness pattern Immediate §A is fixing
  manually today. (New from `/discover` 2026-04-23.)
- [ ] **Auto-update `MEMORY.md` on release** — post-release hook that
  writes new metrics (test count, coverage %, LOC) into
  `~/.claude/projects/.../memory/MEMORY.md`. Currently memory drifts
  (MEMORY.md said "1247 tests"; actual is 1,282). (New from `/discover`
  2026-04-23.)

### Marketing / recruiting

- [ ] **Public AEGIS-gate post / `docs/ai-gate.md`** — the triple-AI
  second-reviewer gate (gpt-5.4-pro + Codex + Claude Opus 4.6) is a
  genuinely differentiated feature. Blog post or canonical doc would
  double as recruiting material. Non-engineering. (New from `/discover`
  2026-04-23.)
- [ ] **PyCon / AI-security conference talk submission for v2.0.0 window**
  — narrative: "a single-maintainer security library going from extraction
  to v2.0 via automated triple-AI review." Content overlaps with
  MIGRATION.md + case-studies/. Target submission window: Q3 2026.

### Refactors

- [ ] **Float validation dedup** — extract `_clamp_score()` helper.
- [ ] **`QueryRouter.route()` complexity reduction**.
- [x] ~~Dynamic coverage badge (Codecov/Coveralls) to replace static shield~~ — done 2026-04-09 via PR #9

---

## Completed (historical)

### v1.6.1 — Injection-Regex Hardening (2026-04-22 → PyPI 2026-04-23)

- [x] **PR #50** — block multi-word "ignore … instructions" injections.
  `INJECTION_PATTERNS` 8 → 10 entries covering the full
  instruction-override family (stacked cues, role cues, `all`-form,
  directional sibling) without overmatching benign prose.
  `test_readonly_directory` now skip-guarded when runner is uid 0 (root
  bypasses POSIX DAC). 22 new regression tests in
  `TestInstructionOverrideInjectionFamily` (1,282 tests collected,
  93.46% coverage). Filed by PR #49 audit
  (`docs/claude/audits/review-2026-04-22.md`). Merged via
  `gh pr merge --admin` after three GPT 5.4 Pro review rounds (Codex +
  Claude Opus passed earlier).

### v1.6.0 — Taint-Aware Feedback Averaging (2026-04-15)

- [x] **PR #44** — taint-aware feedback averaging (ADR-004);
  `LearningRecordResult`, `FLAG_*` constants,
  `ScanResult.has_compliance_taint()`, `EnhancementResult.scan_result`,
  taint-gated `record_feedback`. 50 exports, 1,206 tests, 93.31%
  coverage.

### v1.5.0 — Compliance-Aware Learning (2026-04-15)

- [x] **PR #40** — `LearningPolicy` dataclass, TACTICAL/HIPAA/GENERAL
  gating, `prune_events()`, ADR-003. 44 exports, 1,190 tests, 93.39%
  coverage.

### Waves A–C / D1 (2026-04-11/13)

Consolidated response to two investor reviews (positive + adversarial)
of AIPEA v1.3.2. Full plan: `docs/ROADMAP.md` §P5. Detailed history:
`~/.claude/plans/reactive-growing-lark.md`.

- [x] **Wave A** (PRs #14, #20): v1.3.3 shipped to PyPI (13 security
  fixes incl. HIPAA compliance leak #96, ReDoS #107) + `SECURITY.md`
  added.
- [x] **Wave B** (PR #21): adversarial review committed, README honesty
  sweep, CLAUDE.md header disambiguation, CONTRIBUTING.md expanded
  (~8 → ~130 lines).
- [x] **Wave C1** (PRs #24, #26): triple-AI second-reviewer gate
  (gpt-5.4-pro + Codex gpt-5.3-codex + Claude Opus 4.6) +
  `.github/CODEOWNERS`. Dry-run 1 verified (graceful failure); dry-run 2
  verified (GPT PASS 9m13s, Codex PASS 2m53s, Claude FAIL credit
  balance — since topped up). Evidence in
  `docs/claude/audits/ai-second-review-dry-run-2026-04-11.md` §5.
- [x] **Wave C2** (PR #22): FedRAMP deprecated via Path B +
  `docs/adr/ADR-002-fedramp-removal.md`.
- [x] **Wave C3** (PR #23): `src/aipea/errors.py` (AIPEAError + 5
  subclasses), `cli.py` broad catches tightened, 23 regression tests.
- [x] **Wave D1** (PR #31, 2026-04-13): Adaptive Learning Engine
  (`src/aipea/learning.py`). SQLite-backed strategy performance
  tracking, `EnhancementResult.strategy_used` field, `record_feedback()`
  API, `enable_learning` opt-in. 24 tests + 15 live tests (PR #32).
  Verdict enforcement added to AI second-reviewer gate
  (`REQUEST_CHANGES` blocks merge). All actions SHA-pinned.

### v1.3.x patch (pre-Wave-A)

- [x] **README badge stale** (2026-04-09) — resolved by dynamic coverage
  badge (PR #9).
- [x] ~~**Dead import**: remove unused `import subprocess as _sp` in
  `cli.py:348`~~ — NOT dead; used at lines 361 and 378.
- [x] **ReDoS self-validation** — `INJECTION_PATTERNS` now
  self-validated against `_is_regex_safe()` at `SecurityScanner.__init__`.
- [x] **Ollama stdout robustness** — defensive try-except around
  `ollama list` stdout parsing in `engine.py`.

---

## Deferred Bugs (from bug-hunt waves)

All deferred entries from waves 16-17 were resolved in **Wave 18
(2026-04-10)**, and waves 19-20 closed out a further 20 findings with
zero deferrals plus multiple ultrathink audit extensions. Full details
in [KNOWN_ISSUES.md](KNOWN_ISSUES.md) § "Wave 20 Fixes",
§ "Wave 19 Fixes", § "Wave 19 Ultrathink Audit Extensions",
§ "Wave 18 Fixes", and § "Intentional Design Decisions".

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

---

*See [docs/ROADMAP.md](docs/ROADMAP.md) for historical design rationale
on P1-P5 features. Active work tracked in this file; architect's release
plan at `~/.claude/plans/you-are-the-senior-dynamic-micali.md`.*
