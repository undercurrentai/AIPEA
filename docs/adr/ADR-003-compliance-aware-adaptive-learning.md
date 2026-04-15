# ADR-003: Compliance-Aware Adaptive Learning Engine

- **Status**: Accepted
- **Date**: 2026-04-14
- **Author**: @joshuakirby (with Claude design partnership)

## Context

The `AdaptiveLearningEngine` (shipped in v1.4.0, PR #31) persists user
feedback signals to SQLite with no awareness of the active `ComplianceMode`.
This blocks regulated-industry adoption of the learning feature:

- **TACTICAL mode** (military/defense, air-gapped): any persistence of
  operational feedback patterns is a compliance event, even without raw query
  text. Strategy performance aggregates can leak operational patterns.
- **HIPAA mode** (healthcare): the HIPAA minimum necessary standard (45 CFR
  164.502(b)) now explicitly applies to AI systems per 2024 HHS OCR guidance.
  Feedback persistence must be opt-in with documented justification.
- **Unbounded growth**: no retention, TTL, or pruning exists in `learning.py`.
- **Audit gap**: no compliance context recorded per feedback event.

### External References

- NIST AI RMF 1.0 (AI 100-1): data minimization as a core
  privacy-enhancement characteristic
- HIPAA minimum necessary standard (45 CFR 164.502(b)): limits PHI access to
  the minimum amount necessary for the intended purpose
- HHS OCR 2024 guidance: classifies AI systems as "workforce members" under
  HIPAA
- NIST Cyber AI Profile (NISTIR 8596, Dec 2025 draft): GOVERN function
  requires audit trail transparency

## Decision

Introduce a `LearningPolicy` frozen dataclass that controls compliance-aware
behaviour at the `AdaptiveLearningEngine` level (data layer), not at the
`AIPEAEnhancer` facade. The engine is self-protecting even when used directly.

### Compliance Gates

| Mode | Behaviour | Override? |
|------|-----------|-----------|
| **TACTICAL** | Hard-locked never-record | No. Invariant. |
| **HIPAA** | Default-deny | Opt-in via `LearningPolicy(allow_hipaa_recording=True)` |
| **GENERAL** | Records as before (v1.4.0 behaviour) | N/A |
| **FEDRAMP** (deprecated) | Follows GENERAL | N/A |

### Retention

Configurable via `LearningPolicy(retention_days=N, max_events=N)` with
explicit `prune_events()` calls. Pruning is not automatic — integrators
control when and how retention limits are enforced.

### Auditability

A `compliance_mode` TEXT column is added to `learning_events`. Every recorded
event is tagged with the compliance context under which it was persisted.
Schema migration uses `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` with
graceful degradation on failure.

## Alternatives Considered

| Option | Pros | Cons | Why Not |
|--------|------|------|---------|
| Status quo | Zero effort | Regulatory risk | Non-starter |
| Binary on/off by mode | Simple | Loses HIPAA value prop | Too restrictive |
| External policy engine | Extensible | Over-engineered | YAGNI |

## Consequences

### Positive

- Regulated integrators can safely enable `enable_learning=True` with
  documented opt-in.
- TACTICAL environments are hard-protected against any feedback persistence.
- Retention is bounded and configurable.
- All feedback events are tagged with compliance context for audit.
- Fully backwards compatible: no existing call site or test breaks.

### Negative

- New import edge: `learning.py -> security.py` (safe; no cycle risk since
  `security.py` has zero aipea imports).
- `LearningPolicy` adds 1 export to the public API surface.
- HIPAA integrators must explicitly opt in or lose learning (this is the
  intended safe default).
