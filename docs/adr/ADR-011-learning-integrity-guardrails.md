# ADR-011: Adaptive Learning Integrity Guardrails (ALIG)

- **Status**: Proposed
- **Date**: 2026-05-28
- **Author**: @joshuakirby (with Claude + GPT-5.5-pro xhigh design dialogue)
- **Extends**: [ADR-003](./ADR-003-compliance-aware-adaptive-learning.md) (Compliance-Aware Adaptive Learning), [ADR-004](./ADR-004-taint-aware-feedback-averaging.md) (Taint-Aware Feedback Averaging)
- **Depends on**: [ADR-010](./ADR-010-llm-semantic-scan-tier.md) (Semantic Scan Tier — the future certified-tier confidence/identity source)

## Context

ADR-004 protects the adaptive-learning engine's strategy-selection averages with a
**binary taint gate**: feedback whose originating query fired a compliance-taint
scanner flag is recorded for audit but excluded from `strategy_performance`
averaging. Two structural gaps remain — and they are the one place AIPEA can hold
ground that Presidio / LLM Guard / NeMo Guardrails do not:

1. **Blind-spot inheritance.** The taint signal comes from the regex
   `SecurityScanner`, whose own published metrics show ~9–30% recall on extended
   injection corpora (`docs/metrics.md`). Poison-feedback that rides an injection
   the regex misses also evades the taint gate and reaches the average.
2. **No bound, no observability.** Even feedback that never trips a flag can move
   the running mean without limit, and the engine offers no guarantee on how far a
   budget-limited adversary can shift `get_best_strategy`, nor any signal that a
   manipulation attempt is underway.

A three-round adversarial design dialogue (Claude ↔ GPT-5.5-pro, `xhigh`, 2026-05-28)
converged on a reframing and a decisive correction:

- **Reframing.** The defensible contribution is **not** a new robust-aggregation
  algorithm. It is an **operational finite-sample influence certificate** for the
  *discrete argmax* strategy selection, with the security-scanner output treated as
  learning-integrity metadata.
- **Decisive correction.** A "certificate" counts **aggregation units / edits, not
  human users**. Without request-binding, per-source caps, and stable identity, a
  bound on "k edits" is not a bound on "k users" — one user can place one unit on
  the winner and one on a rival. Therefore **`certified` must be impossible by
  default**; the first release ships *diagnostic-only*.

### External references

Certified poisoning robustness is established art, but **neural-network-training**
focused — none targets a low-dimensional discrete strategy selector:

- Steinhardt, Koh & Liang, *Certified Defenses for Data Poisoning Attacks* (2017);
  Deep Partition Aggregation (Levine & Feizi, 2020); FullCert (Lorenz et al., 2024);
  EnsembleCert / exact label-poisoning certification (2026, arXiv:2604.11416).

The **budget-bounded adversary + bounded reward** framing is the standard formalism
in the bandit / RLHF feedback-poisoning literature:

- Rangi et al., *Saving Stochastic Bandits from Poisoning Attacks via Limited Data
  Verification* (arXiv:2102.07711) — the "limited verification / trusted holdout"
  pattern ALIG adopts for lock-in recovery.
- Yang, Lyu, Liu & Lai, *Human Feedback Attack on Online RLHF: Attack and Robust
  Defense* (UC Davis, 2025) — robust defense against any attacker of bounded cost.
- Ghasemi & Crowley, *Learning When to Trust in Contextual Social Bandits* (2026,
  arXiv:2603.13356) — per-evaluator "Trust Boundary"; validates treating scanner
  output as trust metadata.

**Sybil-tolerance, not Sybil-resistance**, is the honest standard for feedback
aggregation in a library that cannot mint identities:

- Tran et al., *SumUp: Sybil-Resilient Online Content Voting* (NSDI 2009) — bound
  bogus influence by a structural budget.
- Nasrulin et al., *MeritRank* (2022, arXiv:2207.09950) — limit, don't eliminate,
  attacker benefit via decay.

**Competitive gap.** Adaptive security filters are emerging (e.g.
`sovereign-shield-adaptive`, "patent pending", whose `report()` loop is itself an
*unguarded* poisoning surface), but no guardrail library certifies the integrity of
its own learning loop. That is ALIG's open niche.

## Decision

Introduce **Adaptive Learning Integrity Guardrails (ALIG)**: bound feedback
influence over strategy selection and expose the bound as an auditable certificate.
ADR-004's binary gate becomes a special case.

### Certificate status state machine (certified-default-deny)

```
NOT_CERTIFIABLE         ← cell contains unbound/legacy feedback, or no stable
                          source identity is asserted.            [future default]
INSUFFICIENT_DATA       ← no strategy meets min_samples.
RAW_EVENT_EDIT_DIAGNOSTIC ← exact event-level edit bound; honest, but NOT a
                          user/source/Sybil guarantee.            [v1.8.0 ceiling]
CERTIFIED               ← request-bound, per-source-capped UNITS + stable
                          identity + unit aggregation.            [v1.9.0+]
```

`CERTIFIED` is **mechanically disabled** in v1.8.0 (`CERTIFIED_STATUS_ENABLED is
False`); no public config, env var, or test hook may flip it, and there is no code
path that constructs it. `get_best_strategy` must treat **only** `CERTIFIED` as
adaptation-authorizing, so v1.8.0 never switches strategy on the diagnostic — it is
observability + safe-by-construction, consistent with AIPEA's near-zero adoption.

### Exact finite-sample bounds

For a strategy cell with clipped scores in `[ℓ,u]`, sum `S`, count `n`, and `q =
min(k,n)`, the worst-case mean after `k` adversarial edits is exact and cheap:

- **insertion** (the realistic feedback-poisoning adversary): `L=(S+kℓ)/(n+k)`,
  `U=(S+ku)/(n+k)`
- **replacement** (store-tamper): `L=(S−Σtop_q+qℓ)/n`, `U=(S−Σbot_q+qu)/n`
- **deletion** (store-tamper): `min/max` over `0≤d≤min(k,n−1)` of `(S∓Σedge_d)/(n−d)`,
  with selected-strategy ineligibility (`n−d<min_samples`) treated as a selection loss.

The **diagnostic radius** is the largest budget `K` such that for every approved
rival `r` (including *latent* `n=0` rivals an insertion adversary could make
eligible) and every split `a+b=K`: `L_selected(a) > U_r(b)`. `_selection_holds` is
monotone in `K` and `holds(0)` is always True, so the radius is found by binary
search. **Sanity check** (range `[0,1]`): A=ten `0.8`, B=ten `0.7` ⇒ radius 1
(`0.72 > 0.70`, `0.80 > 0.73`); at split `(1,1)` for K=2, `0.72 < 0.73`.

### Implementation (this ADR ships increment 1)

`src/aipea/learning_integrity.py` — a **pure-stdlib** module (zero `aipea` imports,
mirroring `security.py`/`knowledge.py`): `compute_influence_certificate(...) ->
InfluenceCertificate`, the `CertificateStatus` / `PerturbationModel` enums, the
hard gate, and `DIAGNOSTIC_CAVEAT`. Verified by `tests/test_learning_integrity.py`:
hypothesis property tests (an independent brute-force verifier confirms the
certificate is conservative and tight, over all three perturbation models) plus the
dialogue's concrete cases and the no-`CERTIFIED` invariant. Not yet exported or
wired into the enhancer (subsequent increments).

### Mandatory safety invariant

Learned selection may choose only among **approved enhancement strategies**; it must
**never** gate whether a mandatory security check (PII/injection scan) runs. This
holds structurally today (the scan precedes selection in `enhancer.enhance()`); a
later increment locks it with a regression test.

### Deferred increments (with their gates)

- **Inc. 2 (public-API change → ASK):** export the engine; add a read-only
  `AIPEAEnhancer.selection_diagnostic(query_type)`.
- **Inc. 3 (public API + new persistence → ASK):** the Phase-0 trust boundary —
  `record_end_user_feedback(request_id, score, ...)` + an ephemeral, compliance-
  gated `ServedRequest` authorization table (secrets-generated single-use IDs,
  keyed-HMAC source hashes, TTL purge, per-tenant quota) mirroring ADR-003 gating;
  legacy `record_feedback` requires `trust_assertion="trusted_server_side"`;
  fail-closed selection to an admin-pinned baseline + `adaptation_blocked` telemetry
  (denial-of-adaptation mitigation).
- **Inc. 4 (v1.9.0 → ASK):** unlock `CERTIFIED` — source-window unit aggregation,
  HMAC identity, `certified_k` (units) and `certified_sources`.

## Alternatives Considered

| Option | Pros | Cons | Why Not |
|--------|------|------|---------|
| Full "PRAL" (robust aggregation + continuous taint weighting + CUSUM detection as headline) | Ambitious | Overclaims novelty; CUSUM brittle under nonstationarity; premature at n≈0 | Dialogue rejected the overclaim |
| Headline a new robust estimator | — | Robust aggregation is known art (SKL, DPA, bandit/RLHF defenses) | Not novel; the contribution is the systems transplant |
| `w = 1 − risk_score` continuous taint weighting | Uses semantic signal | Detector scores aren't calibrated malice probabilities; FPs correlate with minority languages / security research (fairness hazard); weakens today's safe exclusion | Deferred; taint stays quarantine/budget metadata |
| Keep ADR-004 binary exclusion only | Simplest | No bound, no observability, blind-spot inheritance | The status quo this ADR improves on |
| Ship `certified` immediately (Option A) | One release | Without request-binding the bound is theater; larger first release; overclaim risk | Chose Option B diagnostic-only |

## Consequences

### Positive

- An auditable, exact, cheap influence bound over strategy selection — a capability
  no comparable guardrail library exposes.
- Honest by construction: v1.8.0 cannot emit a `certified` claim it can't back.
- Zero new runtime dependencies (engine is stdlib-only; `hypothesis` is dev-only).
- Reuses the zero-dependency-core idiom and ADR-003/004 compliance lineage.

### Negative

- Public-API surface and new persistence (the `ServedRequest` table) grow in later
  increments, each behind an ASK gate.
- Fail-closed selection introduces a denial-of-adaptation surface, mitigated (not
  eliminated) by admin-pinned baselines + telemetry.
- At current adoption the engine mostly returns the sticky default; the near-term
  value is the certificate API + safe design, not behavioral learning.

### Neutral

- The `CERTIFIED` enum value exists but is unreachable until v1.9.0; it documents the
  state machine and reserves the forward-compatible surface.
- `RAW_EVENT_EDIT_DIAGNOSTIC` always carries `DIAGNOSTIC_CAVEAT` in its
  `assumptions`, so the event-vs-user boundary travels with every result.
