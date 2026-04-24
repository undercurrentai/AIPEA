# ADR-005: Response to PR #52 Adversarial VC Review (2026-04-24)

- **Status**: Accepted
- **Date**: 2026-04-24
- **Deciders**: @joshuakirby
- **Responds to**: [`docs/claude/audits/vc-adversarial-review-2026-04-24.md`](../claude/audits/vc-adversarial-review-2026-04-24.md)
- **Extends**: [ADR-002](ADR-002-fedramp-removal.md) (decline-and-deprecate
  precedent); prior self-authored adversarial review
  ([`investor-review-adversarial-2026-04-11.md`](../claude/audits/investor-review-adversarial-2026-04-11.md))

---

## Context

[PR #52](https://github.com/undercurrentai/AIPEA/pull/52) added a
349-line **external adversarial VC review** of AIPEA v1.6.x to
`docs/claude/audits/vc-adversarial-review-2026-04-24.md`. The review
reframed AIPEA as an **open-core gateway** into paid products
(Agora IV, AEGIS), argued that the relevant diligence questions shift
to funnel/adoption/conversion metrics not visible in the repository,
and delivered a detailed 4-phase "path forward" path (§10) with 23
specific recommendations ranging across engineering, BD, and
governance work.

The review was merged verbatim per the AIPEA "adversarial reviews
retained in full" convention (cf.
[`investor-review-adversarial-2026-04-11.md`](../claude/audits/investor-review-adversarial-2026-04-11.md))
on 2026-04-24 at squash `f92d253`, with a maintainer editorial banner
flagging two stale metrics (67→238 commits; ~810→1,282 tests)
without editing the reviewer's voice.

Unlike the 2026-04-11 adversarial review — which was self-authored and
handled via Wave A-C engineering work (CHANGELOG + TODO.md entries) —
PR #52 is a **governance-decision artifact** that warrants a formal
architectural decision record. The reviewer proposed changes that
would materially alter AIPEA's stated design principles
(stdlib+httpx core; MIT; detection-not-enforcement), and the
"considered and declined" decisions need a durable home so future
reviewers and investors can see that objections were engaged, not
ignored.

This ADR documents the triage, the locked user decisions, the
sequenced execution, and — in the §12 appendix — per-question
responses to the 12 diligence questions in the review's §7.

The intended outcome is a single auditable decision record covering
all 23 findings, tied to the v1.6.2 / v1.7.0 / v1.8.0 / v2.0.0
release roadmap, with explicit **Revisit triggers** on every declined
item so no decision is relitigated silently.

---

## Decision

**Summary**: 23 review findings triaged across 4 tracks and sequenced
into the approved v2.0.0 roadmap.

| Track | Count | Disposition |
|---|---|---|
| **A — Accept** (engineering-actionable in-repo) | 13 | Sequenced v1.6.2 → v1.7.0 → v1.8.0 |
| **B — BD / Strategic** (maintainer / team ownership) | 7 | Budget gates + decision deadlines documented |
| **C — Decline** (with Revisit triggers) | 2 | C.1 DistilBERT classifier swap; C.2 opt-out telemetry |
| **D — Defer** (accept framing; v3.0+ window) | 1 | Federated learning endpoint |

Full plan authored at
`~/.claude/plans/pr52-vc-adversarial-response-2026-04-24.md` (807
lines, user-approved 2026-04-24).

### Triage matrix

| # | Review section | Finding / recommendation | Track | Phase | Status |
|---|---|---|---|---|---|
| 1 | §5.1 | Signature-based injection detection; add adversarial corpus | **A** | v1.7.0 Phase 4.c | queued |
| 2 | §5.1 | Swap regex injection layer for DistilBERT-scale classifier | **C.1** | declined | Revisit trigger below |
| 3 | §5.2 | PII catalog narrow; add phone / email / address / account / IPv4-private | **A** | v1.8.0 tranche 1 | queued (ADR-008) |
| 4 | §5.2 | PHI catalog narrow; add medication / ICD-10 / CPT / DEA | **A** | v1.8.0 tranche 2 | queued (opt-in flag pending clinical review) |
| 5 | §5.3 | HIPAA mode marketing-vs-code gap; claims audit | **A** | v1.7.0 Phase 4.b | queued |
| 6 | §5.3 | `phi_redaction_enabled` consumed by nothing — wire or remove | **A** | v1.7.0 Phase 4.b + v2.0.0rc1 | queued |
| 7 | §5.3 | TACTICAL mode advisory-only; document | **A** | v1.7.0 Phase 4.b | queued |
| 8 | §5.4 | Independent pentest (narrow scope) | **B** | 2026-07 reconsider | deferred |
| 9 | §5.4 | SOC 2 Type II | **B** | gated on #8 + first paying design partner | deferred |
| 10 | §5.4 | GitHub Private Vulnerability Reporting | **A** | v1.7.0 | queued |
| 11 | §7.1 | PyPI download trajectory dashboard | **A** | v1.6.2 | ✅ shipped (docs/metrics.md live badges) |
| 12 | §7.2 | Dependent-repo count visibility | **A** | v1.6.2 | ✅ shipped (docs/metrics.md link) |
| 13 | §7.3 | GitHub Discussions / community signal | **A** | v1.6.2 | ✅ shipped (Discussion #54 opened) |
| 14 | §7.4 | Funnel conversion instrumentation (AEGIS / Agora IV side) | **B** | v1.8.0+ | deferred (external dep) |
| 15 | §7.5 | Step-up articulation: "AIPEA detects / AEGIS enforces / Agora IV orchestrates" | **A** | v1.7.0 Phase 4.a | queued |
| 16 | §7.10 | Bus factor = 1: second committer | **A** partial + **B** full | v1.7.0 CODEOWNERS docs + Phase 3 SOW | SOW v0 drafted 2026-04-24; contract-gated |
| 17 | §7.11 | Agora IV / AEGIS diligence | **B** | out of AIPEA scope | out-of-band |
| 18 | §10 Phase 0 | Opt-out install pings telemetry | **C.2** | declined | Revisit trigger below |
| 19 | §10 Phase 1 | Adversarial benchmark suite (corpus + nightly CI) | **A** | v1.7.0 Phase 4.c | queued |
| 20 | §10 Phase 1 | Clinical reviewer for PHI taxonomy | **B** | deferred | v1.8.0 opt-in-flagged until funded |
| 21 | §10 Phase 1 | 3 named design partners (healthcare / fintech / defense) | **B** | BD capacity decision | deferred |
| 22 | §10 Phase 2 | Federated learning endpoint | **D** | v3.0+ | deferred |
| 23 | §10 Phase 2 | AEGIS = enforcement layer on AIPEA detection | **B** | AEGIS repo | out-of-scope here |

### User decisions (locked 2026-04-24)

1. **Merge PR #52 verbatim + editorial banner** — DONE at squash
   `f92d253`.
2. **Author is self** (`ThermoclineLeviathan` = maintainer alt
   account / Claude.ai session). §12 appendix tone is
   **collegial-internal**, not publishable-rebuttal.
3. **Pentest budget**: NOT authorized now. Reconsider post-v1.7.0
   Phase 4.b claims audit (~2026-07). Rationale: aligned marketing
   first, paid attestation second.
4. **Clinical reviewer budget**: NOT authorized now. v1.8.0 PHI
   tranche ships **behind opt-in flag** with "pending clinical
   review" CHANGELOG marker.
5. **Second committer contract**: **AUTHORIZED** ~$40K/yr, ~0.25
   FTE. SOW v0 drafted at
   `~/.claude/plans/aipea-second-committer-sow-v0.md` (personal;
   not committed). 6 open questions in §12 pending maintainer +
   counsel review before v1.
6. **ADR numbering**: **ADR-005 = this file** (VC response);
   **ADR-006 = v2.0.0 deprecation batch** (v1.7.0 Phase 4.b);
   ADR-007 reserved for optional `AIPEAConfig.source_of()` public
   contract formalization; ADR-008 reserved for v1.8.0 PII/PHI
   catalog expansion.

### Revised release roadmap

Per approved plan
`~/.claude/plans/you-are-the-senior-dynamic-micali.md`:

| Release | Target | Scope |
|---|---|---|
| **v1.6.2** | 2026-04-24 ✅ shipped | HTTP_TIMEOUT deprecation, P5e trio, telemetry, benchmarks delete, PR #52 merge |
| **v1.7.0** | 2026-06-15 | `source_of()` + AEGIS contract audit + `DeprecationWarning` on `create_model_specific_prompt` + `MIGRATION.md` v0 + `test_models.py` + PR #52 Phase 4.a (this ADR) + 4.b (claims audit, ADR-006) + 4.c (adversarial corpus) |
| **v1.8.0** | 2026-08-01 | AgoraIV migration PRs + PII tranche 1 + PHI tranche 2 (opt-in-flagged) + `MAINTAINERS.md` + CODEOWNERS update |
| **v2.0.0rc1** | 2026-09-01 | Remove FedRAMP, HTTP_TIMEOUT alias, `create_model_specific_prompt`. Inline `TierProcessor` ABC. Finalize `MIGRATION.md`. Remove `phi_redaction_enabled` if v1.7.0 audit finds unused |
| **v2.0.0** | 2026-10-22 | GA |

Rationale for 2026-10-22 target: NumPy NEP 23 (≥1 year); PEP 387 (2
minor versions); SQLAlchemy 1.4→2.0 (22 months). AIPEA's FedRAMP
deprecation landed in v1.3.4 (2026-04-11); 6 months + 2 minor releases
is the minimum defensible window.

---

## Declined (with Revisit triggers — MADR "Declined" pattern)

### C.1: DistilBERT-scale classifier swap

- **Proposed by**: PR #52 §5.1 + §10 Phase 1
- **Verbatim**: "Swap regex injection layer for a fine-tuned small
  classifier (DistilBERT-scale, ONNX-exported). Keep regex as
  fallback. Single most leveraged technical change: adversarial
  robustness moves from 'patch-and-pray' to 'trainable.'"
- **Decision**: **Declined.**
- **Rationale**:
  1. **Core dependency principle**. `CLAUDE.md §1.1` / §3.3 and
     `pyproject.toml` constrain the core to `stdlib + httpx`.
     `transformers` + `onnxruntime` pulls ~1 GB of transitive
     dependencies (torch-equivalent weight via ONNX), dwarfing
     AIPEA's 10,662 LOC and breaking the "audit the whole thing
     in an afternoon" pitch that the review itself credits (§6).
  2. **Supply-chain attack surface**. Pre-trained model weights
     are a canonical supply-chain vector — precisely the thing a
     security-focused library must minimize. `stdlib + httpx` is
     auditable; an ONNX checkpoint is not.
  3. **Determinism**. Regex matches are byte-exact, deterministic,
     reviewable. Classifier outputs depend on tokenizer version,
     ONNX runtime version, hardware (INT8 vs FP32), and batch
     size. AIPEA's audit trail becomes materially noisier.
  4. **Substitute solution**. The review's real concern —
     "signature-based detection; one paraphrase bypasses it" —
     is addressed by **accepting findings #1 and #19**
     (adversarial benchmark corpus + nightly CI). New regex
     patterns ship when the benchmark shows paraphrase gaps; no
     classifier required.
  5. **Open-core positioning**. Per the review's own §3 open-core
     reframing: AEGIS can ship ML-classifier enforcement as a
     paid-tier feature on top of AIPEA's detection substrate.
     Putting the classifier in AIPEA **collapses the step-up** the
     review argues is load-bearing.
- **Counter-proposal (accepted)**: Ship adversarial benchmark
  (finding #19; v1.7.0 Phase 4.c) + pattern library updates in AIPEA;
  ML-classifier enforcement as AEGIS paid-tier feature.
- **Revisit trigger**: A design partner funds the classifier work
  AND commits to maintaining it as `pip install aipea[ml]` optional
  extra (additive, non-default). Never into core. Non-trivial
  alternative: if adversarial-benchmark hit-rate shows paraphrase
  robustness gaps that regex patterns cannot close within two v1.x
  minor releases, reopen as v2.1+ candidate.

### C.2: Opt-out install pings / telemetry

- **Proposed by**: PR #52 §10 Phase 0
- **Verbatim**: "Instrument OSS telemetry. Opt-out install pings,
  PyPI download dashboard, GitHub traffic tracking. The gateway
  thesis is unfalsifiable without this data."
- **Decision**: **Declined** (the opt-out install-pings subcomponent;
  the dashboard + traffic-tracking subcomponents are **accepted** as
  findings #11/#12/#13).
- **Rationale**:
  1. **Privacy erosion**. "Opt-out" telemetry on a security-focused
     library is hostile to the exact customers AIPEA targets
     (regulated environments; TACTICAL / air-gapped deployments).
     A library that claims to respect classified-marker scanning
     must not phone home by default.
  2. **Existing free signal**. `pypistats.org` and GitHub Insights
     provide download trajectory and dependent-repo counts without
     any client-side instrumentation. Per findings #11/#12,
     `docs/metrics.md` now surfaces these.
  3. **Brand consistency**. `SECURITY.md` is emphatically honest
     about what AIPEA does and does not enforce; adding install
     pings contradicts that voice.
- **Counter-proposal (accepted)**: Opt-in GitHub Discussion for
  adopters (#54, shipped 2026-04-24) captures the same signal from
  users who want to be counted, without the privacy cost.
- **Revisit trigger**: A paying enterprise design partner requires
  attested install telemetry for their own audit purposes AND
  provides a privacy-respecting-defaults specification (e.g.,
  anonymized aggregate-only, differential privacy, opt-in-by-default
  with verifiable audit trail). Reopen as v2.1+ candidate at that
  point.

---

## Deferred

- **Federated learning endpoint** (review §10 Phase 2 — finding #22):
  v3.0+ architectural change. Not v1.x scope. Would require
  privacy infrastructure (differential privacy, opt-in trust model)
  beyond AIPEA's current design surface. Revisit if a v3.0 roadmap
  emerges.
- **Independent pentest** (review §5.4 — finding #8): deferred until
  post-v1.7.0 claims audit completes (~2026-07). Rationale:
  pentesting against aligned marketing is recoverable; pentesting
  against out-of-sync marketing generates findings that become
  career incidents.
- **Clinical reviewer for PHI taxonomy** (review §10 Phase 1 — finding
  #20): deferred. v1.8.0 PHI tranche ships **behind opt-in flag** with
  "pending clinical review" CHANGELOG marker. Once budget is
  authorized, clinical reviewer signs off and flag becomes default-on
  in a subsequent minor release.
- **3 named design partners** (review §10 Phase 1 — finding #21):
  BD capacity decision, not engineering. AIPEA repo cannot unilaterally
  execute outreach. Tracked as Plan B item pending BD capacity review.

---

## Consequences

### Easier

- v1.7.0 engineering work has a **ratified decision framework**; no
  re-debate on declined items.
- Future adversarial reviews land against a **known triage
  structure** (13 A / 7 B / 2 C / 1 D pattern) — reviewers get
  faster, more consistent responses.
- `docs/metrics.md` "Signals we currently do NOT publish" section
  normalizes honest-small-numbers disclosure; protects against
  future FedRAMP-style overclaim cycles.
- AEGIS step-up (detection → enforcement → orchestration)
  articulated in `docs/positioning.md` (v1.7.0) gives BD / investor
  conversations a crisp narrative to point at.

### Harder

- Seven Plan B items (pentest, SOC 2, design partners, second
  committer, clinical reviewer, funnel instrumentation, Agora/AEGIS
  diligence) block on BD/external capacity. AIPEA cannot unilaterally
  close these; the critical-path item is the **second committer**
  (budget authorized 2026-04-24; contract signed by 2026-06-30
  target).
- Declined items stay discoverable via Revisit triggers, but still
  require future maintainers to actively re-evaluate if the triggers
  fire. Not "set and forget."

### Neutral

- Declined items do not disappear from the conversation — Revisit
  triggers make them discoverable, queryable, and re-opened under
  documented conditions. Reviewers cannot claim "ignored"; only
  "considered and declined under conditions X/Y/Z."
- §12 appendix metric-state will drift as Plan B items progress
  (pentest signs, SOC 2 starts, second committer joins). Major
  revisions land in CHANGELOG; minor cadence-updates happen inline
  in this ADR without new release events.

---

## References

- PR #52: [`undercurrentai/AIPEA#52`](https://github.com/undercurrentai/AIPEA/pull/52)
- PR #52 merge commit: `f92d253` (2026-04-24)
- Response plan (approved 2026-04-24):
  `~/.claude/plans/pr52-vc-adversarial-response-2026-04-24.md`
- Prior adversarial review:
  [`investor-review-adversarial-2026-04-11.md`](../claude/audits/investor-review-adversarial-2026-04-11.md)
- [ADR-002](ADR-002-fedramp-removal.md) — decline-and-deprecate
  precedent (Path B framing reused here)
- [ADR-004](ADR-004-taint-aware-feedback-averaging.md) — triage /
  schema structure reused
- [OpenTofu C&D response (2024-04-11)](https://opentofu.org/blog/our-response-to-hashicorps-cease-and-desist/) —
  tone exemplar: quote verbatim + evidence-first rebuttal + clinical
  prose + forward momentum
- MADR "Declined decision + Revisit trigger" pattern (Archyl 2026
  ADR guide)
- PEP 387 / NumPy NEP 23 / SQLAlchemy 1.4→2.0 (deprecation-window
  norms underlying v2.0.0 2026-10-22 target)

---

## §12. Maintainer Response to Diligence Questions (Appendix)

**Voice**: collegial-internal per 2026-04-24 user decision #2.
Per-question status against the live repo, anchored to 2026-04-24
unless otherwise noted. Substantive changes as Plan B items progress
land in CHANGELOG; minor metric drift is expected.

### Q1: PyPI download trajectory?

- **Live dashboard**: [`pepy.tech/project/aipea`](https://pepy.tech/project/aipea)
  + [`pypistats.org/packages/aipea`](https://pypistats.org/packages/aipea).
  Embedded badges in `docs/metrics.md`.
- **As of 2026-04-24**: 10 PyPI releases over ~10 weeks (v1.0.0
  2026-02-14 → v1.6.2 2026-04-24). Absolute download counts are
  small (consistent with B2B library, not consumer); trajectory will
  be meaningful by v1.7.0 ship (~2026-06-15) once 2+ months of
  post-public-flip data accumulates.
- **Not committing to a growth number** — unmeasured growth is not
  growth.

### Q2: External dependents?

- **Live view**: [`github.com/undercurrentai/AIPEA/network/dependents`](https://github.com/undercurrentai/AIPEA/network/dependents)
- **As of 2026-04-24**: 0 external dependents. All consumers are
  internal Undercurrent Holdings products (Agora IV, AEGIS). Listed
  transparently in `docs/adopters.md`.
- **Mitigation pending**: Plan A findings #11-#13 (telemetry +
  Discussion #54) surface the project so external adoption can
  accrue.

### Q3: Community signal (stars / forks / issues / external PRs)?

- **Stars / forks / watchers**: live badges in `docs/metrics.md`
  (GitHub-native).
- **External issues filed**: 0 at 2026-04-24.
- **External PRs merged**: 0. All 57 merged PRs attributed to the
  maintainer.
- **GitHub Discussions**: enabled 2026-04-23. Pinned
  adopter-outreach thread:
  [Discussion #54](https://github.com/undercurrentai/AIPEA/discussions/54).
- **Public Q&A / Slack / Discord**: none yet.

### Q4: Funnel conversion from AIPEA → Agora IV / AEGIS paid seats?

- **Honest: unmeasured.** AEGIS-side and Agora IV-side instrumentation
  would be required to attribute pipeline or closed revenue to AIPEA
  touchpoints. Plan B finding #14 owns the fix; target v1.8.0+
  depending on AEGIS / Agora roadmap.
- **Until measured**: the open-core gateway thesis is unfalsifiable.
  The review (§3.4) correctly flags this as the first diligence
  question an investor must answer, and this ADR does not claim
  otherwise.

### Q5: Step-up articulation — AIPEA vs. AEGIS vs. Agora IV?

- One-line summary: **AIPEA detects; AEGIS enforces + governs;
  Agora IV orchestrates multi-model coordination.**
- Formalized in `docs/positioning.md` shipping v1.7.0 Phase 4.a
  alongside this ADR.

### Q6: HIPAA mode marketing vs. code?

- Current behavior (`src/aipea/security.py:734-744`): HIPAA mode
  turns on 3 PHI regex categories, sets a BAA-covered model
  allowlist via substring match, and sets
  `phi_redaction_enabled = True` which **no code currently
  consumes** (finding #6; audit-and-fix in v1.7.0 Phase 4.b).
- **Detection + allowlist** is the honest claim. No redaction, no
  BAA execution, no SOC 2. `SECURITY.md` already discloses this.
- v1.7.0 Phase 4.b claims audit rewrites any marketing surface that
  currently overclaims. `phi_redaction_enabled` either wired to
  real behavior or removed at v2.0.0rc1.

### Q7: Other unbacked compliance claims besides FedRAMP?

- **Commitment**: v1.7.0 Phase 4.b walks every compliance claim in
  README.md / SECURITY.md / SPECIFICATION.md / CLAUDE.md /
  `docs/integration/aegis-adapter.md` / `docs/integration/agora-adapter.md`
  against `security.py`. Each claim gets either (a) a
  `security.py:LLL-MMM` source-link anchor, (b) a rewrite narrower
  than claimed, or (c) a `DeprecationWarning` scheduled on the ADR-002
  precedent.
- **Known candidate**: HIPAA mode as discussed in Q6.
- **Precedent**: ADR-002 (FedRAMP retraction, 2026-04-11) —
  established the retract-and-deprecate pattern. Any new retraction
  follows the same path.

### Q8: External audit timeline?

- **Pentest** ($25-40K, narrow scope: `security.py` +
  search-result-scanning path): **deferred** (user decision #3).
  Reconsider post-v1.7.0 Phase 4.b claims audit (~2026-07). Budget
  authorization required.
- **SOC 2 Type II**: 9-month clock; gated on pentest-clean + first
  paying design partner. Earliest realistic completion 2027-Q1.
- **Bug-bounty / Private Vulnerability Reporting**: **accepted**
  (finding #10). GitHub PVR enabled in v1.7.0 Phase 4.b; no cost.
- **Adversarial corpus benchmark**: **accepted** (findings #1 + #19).
  Ships v1.7.0 Phase 4.c (nightly CI, non-gating initially).
  Hit-rate published to `docs/metrics.md` **including losses**.

### Q9: Durable advantage vs. LangChain / LlamaIndex / Guardrails-AI / NeMo-Guardrails / AWS Bedrock Guardrails?

- **Honest (OSS layer)**: minimal differentiation; expected under
  the open-core thesis (review §3.2). Durable advantage must live
  in Agora IV / AEGIS, not AIPEA.
- **What AIPEA does distinctively well in its niche**: zero-deps-in-core
  (stdlib + httpx only); mypy strict; Unicode NFKC + 35-entry
  confusable map; 7-layer ReDoS safety validator; triple-AI
  security-review gate; taint-aware feedback averaging (ADR-004);
  compliance-aware adaptive learning (ADR-003).
- **Where it's thin**: ML-classifier injection detection (by choice,
  per C.1); pre-built jailbreak corpus (ships v1.7.0 Phase 4.c);
  broad PII/PHI catalogs (ships v1.8.0 tranches).

### Q10: Bus factor?

- **Current: 1.** `git shortlog -sn` shows effectively a single
  contributor.
- **Mitigation authorized 2026-04-24**: second-committer contract
  (~$40K/yr, ~0.25 FTE). SOW v0 drafted at
  `~/.claude/plans/aipea-second-committer-sow-v0.md` (personal);
  6 open questions (CLA, background check, confidentiality, renewal,
  IP, equity) pending maintainer + counsel review before v1.
- **Targets**: SOW v1 finalized 2026-05-07; candidate outreach
  2026-05-15; offer 2026-06-15; contractor start 2026-07-15;
  CODEOWNERS listed by v1.8.0 (2026-08-01).
- **Interim mitigation**: triple-AI second-reviewer gate on
  security-critical PRs (gpt-5.4-pro + Codex gpt-5.3-codex + Claude
  Opus 4.6). Augments, does not replace.

### Q11: Agora IV / AEGIS repos, revenue, retention, margin?

- **Out of AIPEA scope.** This ADR covers AIPEA's response to PR #52
  only. Diligence on Agora IV and AEGIS happens in their respective
  repositories and in out-of-band investor conversations with the
  maintainer.

### Q12: Metric anchoring in repo docs — live vs. documented?

- **All v1.6.2 metrics verified live at 2026-04-24**:
  - 1,282 tests collected (`pytest --collect-only`)
  - 93.46% coverage (Codecov, `make test`)
  - 10,662 source LOC (`wc -l src/aipea/*.py`)
  - 50 public exports (`__init__.py` `__all__` grep)
  - 10 PyPI releases (git tags v1.0.0 through v1.6.2)
- **Authoritative source**: `docs/metrics.md` §"Engineering-quality
  signals" table.
- **Historical point-in-time snapshots** (e.g., v1.5.0 "1,190 tests,
  93.39% coverage") are **intentionally preserved per `CLAUDE.md
  §Metric-Citing Docs` convention**: retroactively editing snapshot
  numbers would destroy audit trail. Reviewers should treat any
  date-stamped metric as frozen at that date; live metrics live in
  `docs/metrics.md`.

---

*ADR-005 v1 — authored 2026-04-24 alongside v1.7.0 Phase 4.a. §12
appendix may revise as Plan B items progress; major revisions land in
CHANGELOG. Supersedes the "forthcoming ADR-005" placeholders in
`TODO.md`, `CHANGELOG.md [Unreleased]`, `docs/metrics.md`, and the
`vc-adversarial-review-2026-04-24.md` editorial banner.*
