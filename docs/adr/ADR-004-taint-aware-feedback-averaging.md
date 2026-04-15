# ADR-004: Taint-Aware Feedback Averaging

- **Status**: Accepted
- **Date**: 2026-04-15
- **Accepted**: 2026-04-14
- **Author**: @joshuakirby (with Claude design partnership)
- **Extends**: [ADR-003](./ADR-003-compliance-aware-adaptive-learning.md) (Compliance-Aware Adaptive Learning Engine)

## Context

ADR-003 closed the persistence-under-compliance-mode half of the
`AdaptiveLearningEngine` threat model: TACTICAL is hard-locked, HIPAA is
default-deny with explicit opt-in, and every recorded event carries its
`compliance_mode` for audit. The feedback-poisoning half remains open.

Specifically: the engine today accepts feedback for any query the caller's
scanner classified as injection-bearing, PHI-bearing, PII-bearing, or
classified-marker-bearing. Such feedback contributes equally to
`strategy_performance.avg_score` as clean feedback. Three concrete
consequences:

1. **Stateful feedback poisoning.** A caller in GENERAL mode can drive a
   chosen strategy's score in either direction by submitting crafted
   queries with injection payloads and corresponding feedback. The scanner
   detects the injection; AIPEA is detection-only by design, so the
   enhancement still executes; `record_feedback` is unaware of the flag;
   the average shifts. OWASP LLM Top 10 2026 and NIST 2026 name this
   class of surface ("stateful attacks") as an emerging frontier.

2. **Silent averaging corruption under HIPAA opt-in.** A HIPAA integrator
   who sets `allow_hipaa_recording=True` today cannot distinguish "my
   strategy really performs this well on clinical queries" from "my
   strategy's score includes feedback derived from PHI-flagged
   interactions that may not reflect the real workflow."

3. **Audit gap.** Events recorded today carry `compliance_mode` but not the
   scanner flags that fired on their originating query. A post-hoc audit
   cannot answer "which recorded events were associated with
   compliance-flagged input?"

All three problems share one fix: make the engine aware of the scanner's
output at record time.

### External References

- OWASP LLM Top 10 2026 — stateful attack surface guidance on
  persistence-layer threats (memory poisoning, cross-session hijacking)
  in adaptive AI systems.
- NIST AI RMF 1.0 (AI 100-1), GOVERN and MEASURE functions — continuous
  monitoring of training-data integrity.
- NISTIR 8596 (Cyber AI Profile, Dec 2025 draft) — audit trail
  completeness requirements.
- HIPAA Audit Controls (45 CFR §164.312(b)) — tamper-evident records of
  inputs to AI-driven decisions.

## Decision

Extend the ADR-003 architecture with a taint-awareness invariant.

### Policy field

Add one field to `LearningPolicy`:

```python
exclude_tainted_from_averaging: bool = True  # default-safe
```

When true (the default), feedback associated with a query that fired a
compliance-taint scanner flag is recorded to `learning_events` for audit
but does **not** update `strategy_performance`.

### Schema additions (additive migration)

Two new columns on `learning_events`:

- `taint_flags TEXT` — JSON array of the compliance-taint scanner flags
  that fired on the originating query (e.g.,
  `["phi_detected:patient_name","injection_attempt"]`). `NULL` or `"[]"`
  for clean events.
- `excluded_from_averaging INTEGER NOT NULL DEFAULT 0` — 1 iff this event
  was not aggregated into `strategy_performance`.

Migration mirrors ADR-003's pattern: `PRAGMA table_info` + conditional
`ALTER TABLE ADD COLUMN`, with graceful degradation on failure.

### Gate logic

Extend `AdaptiveLearningEngine.record_feedback` with a keyword-only
`scan_flags: Sequence[str] = ()` parameter. The engine computes

```python
taint = [
    f for f in scan_flags
    if any(f.startswith(p) for p in _COMPLIANCE_TAINT_PREFIXES)
]
```

using canonical flag-prefix constants lifted into `security.py`. If
`taint` is non-empty and `policy.exclude_tainted_from_averaging` is true,
the engine writes the event with `excluded_from_averaging=1` and
`taint_flags=json.dumps(taint)` but does not execute the
`strategy_performance` upsert.

### Canonical flag-prefix constants

Lift the existing bare-string flag prefixes in `security.py`
(`phi_detected:`, `pii_detected:`, `classified_marker:`,
`injection_attempt`, `custom_blocked:`) into module-level constants and
group the compliance-taint subset in `_COMPLIANCE_TAINT_PREFIXES`. The
bare strings at existing call sites can be migrated in a separate cleanup
PR; the new constants are additive exports.

### Threading

`EnhancementResult` gains one optional field:

```python
scan_result: ScanResult | None = None
```

populated by `AIPEAEnhancer.enhance()` alongside the existing
`security_context` population. `AIPEAEnhancer.record_feedback` threads
`result.scan_result.flags` into the engine call. Callers who construct
`EnhancementResult` by hand are unaffected.

### Typed return: `LearningRecordResult`

Replace the `None` return on `record_feedback` / `arecord_feedback`:

```python
@dataclass(frozen=True)
class LearningRecordResult:
    recorded: bool
    excluded_from_averaging: bool
    reason: str | None
    taint_flags: tuple[str, ...] = ()
```

`AIPEAEnhancer.record_feedback` logs `info` when `excluded_from_averaging`
is true and can surface the decision via `enhancement_notes` on the next
enhancement call for the same caller.

## Alternatives Considered

| Option | Pros | Cons | Why Not |
|--------|------|------|---------|
| Refuse to record tainted events entirely | Strongest stance; no taint ever reaches disk | Loses the audit signal; security teams cannot answer "did tainted queries reach us?" | Audit requirements from NISTIR 8596 favor recording-with-exclusion over silent discard |
| Scrub the flags before recording | Smaller schema | No scrubbing is needed — flags are compliance-safe prefix strings, not raw content; scrubbing removes useful signal | Non-problem; AIPEA stores no raw text and flag strings are already constants |
| Compute taint at the wrapper, not the engine | Slightly simpler engine | Any future caller that bypasses the wrapper violates the invariant; library boundary must enforce | ADR-003 precedent: invariant lives at the engine |
| Store flags as comma-separated string | Marginally simpler than JSON | Loses reparse fidelity when a flag suffix contains commas (e.g., `custom_blocked:foo,bar`) | Negligible simplicity win against a real parse bug class |

## Consequences

### Positive

- Closes the stateful-feedback-poisoning vector called out by OWASP LLM
  Top 10 2026.
- Makes `strategy_performance` averages robust to compromised inputs by
  construction.
- Preserves the full audit record (tainted events still land in
  `learning_events`, tagged).
- Callers can introspect skip/exclusion decisions via the new typed
  return.
- Zero new runtime dependencies (still stdlib + httpx only).
- Fully backward compatible: callers who pass no `scan_flags` get the
  legacy behavior (empty taint → normal averaging).

### Negative

- Two new schema columns; additive migration carries a small compatibility
  risk, handled by the graceful-degradation precedent from ADR-003.
- `EnhancementResult` gains one new field; public API surface grows by one
  attribute.
- `LearningRecordResult` + 5 `FLAG_*` constants add 6 exports
  (44 → 50 public symbols); a minor version bump per SemVer is appropriate.

### Neutral

- Flag-prefix constants are added but legacy bare-string call sites are
  left intact; a separate cleanup can migrate them later without blocking
  this ADR.
- The policy default `exclude_tainted_from_averaging=True` is opinionated;
  integrators who want tainted feedback included can opt in explicitly.
