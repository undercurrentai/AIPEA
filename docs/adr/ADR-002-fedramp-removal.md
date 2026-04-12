# ADR-002: Remove FedRAMP from AIPEA's Declared Compliance Surface

**Status**: Accepted
**Date**: 2026-04-11
**Deciders**: @joshuakirby
**Supersedes**: N/A
**References**:
- [`docs/claude/audits/investor-review-2026-04-11.md`](../claude/audits/investor-review-2026-04-11.md) §P5b (Path B recommended)
- [`docs/claude/audits/investor-review-adversarial-2026-04-11.md`](../claude/audits/investor-review-adversarial-2026-04-11.md) §4 (compliance theater)
- [`docs/ROADMAP.md`](../ROADMAP.md) §P5b

---

## Context

AIPEA has historically exposed a `ComplianceMode.FEDRAMP` enum value and referenced "FedRAMP support" in its README, `CLAUDE.md`, `SPECIFICATION.md`, and roadmap docs. The code in `src/aipea/security.py` was honest — the `FEDRAMP` branch of `ComplianceHandler._configure_mode` was explicitly labeled as *"UNSUPPORTED STUB — configuration only, no behavioral enforcement"* with a runtime `logger.warning` on every use. The documentation surface, however, did not match that honesty: a reviewer skimming the README would reasonably conclude that AIPEA implements FedRAMP controls.

The 2026-04-11 adversarial due-diligence review formalized this gap as its §4 "compliance theater" finding and ranked it as a High-severity risk:

> The FedRAMP stub being honestly labeled in the code is refreshing — but the same label does not appear in the README or investor-facing docs. That gap is where risk lives.

Contemporaneously, AIPEA has:

- **Zero FedRAMP design partners**. No customer or prospect has requested FedRAMP support.
- **Zero engineering budget allocated**. Real FedRAMP enforcement would require: data-residency validation, FedRAMP-authorized provider integration, FIPS 140-2 encryption verification, continuous monitoring, immutable audit trail storage, a third-party 3PAO assessment, and an ATO. Months of work minimum, and zero of it is in flight.
- **No business case** for investing that work speculatively. FedRAMP sales cycles are long and expensive; they only make sense with a named customer in the pipeline.

The positive investor review (`investor-review-2026-04-11.md` §P5b) framed the choice as a fork:

- **Path A** — find a design-partner org that needs FedRAMP, scope minimum-viable enforcement built *with their input*, ship as v1.4.0.
- **Path B** — remove `FEDRAMP` from `ComplianceMode`, strike it from the README, write an ADR explaining why.

## Decision

**Adopt Path B: remove the declared FedRAMP compliance surface from AIPEA.**

Specifically:

1. **Narrative removal (immediate, this PR):**
   - Strip FedRAMP from marketing-adjacent documentation: `README.md`, `CLAUDE.md`, `SPECIFICATION.md`, `TODO.md`, `SECURITY.md`, `ROADMAP.md`.
   - Mark `docs/ROADMAP.md` §P5b as resolved.
   - Historical documents (`CHANGELOG.md` prior entries, `docs/claude/audits/*`, `docs/design-reference/*` pre-extraction design files) are **not** rewritten — they are a frozen record of what was believed at a given point in time.
   - Governance template files under `docs/compliance/*.md` reference FedRAMP as a *control framework* (e.g. `FedRAMP CM-2/3`) rather than an AIPEA feature, and are **not** modified.

2. **Soft code deprecation (immediate, this PR):**
   - `ComplianceMode.FEDRAMP` enum value is retained for API compatibility — removing it would be a breaking public API change per AIPEA's SemVer discipline and would ride a `v2.0.0` release, which is not scheduled.
   - `ComplianceHandler.__init__` now emits `warnings.warn(..., DeprecationWarning)` (in addition to its existing `logger.warning`) whenever a `ComplianceHandler` is constructed with `ComplianceMode.FEDRAMP`.
   - `AIPEAEnhancer` similarly emits a `DeprecationWarning` at construction time when `compliance_mode == ComplianceMode.FEDRAMP`.
   - The `AIPEA_DEFAULT_COMPLIANCE=fedramp` environment variable continues to parse (for API compat) but triggers the same deprecation warning.
   - The existing enum docstring is updated to cross-reference this ADR.

3. **Hard removal (future, v2.0.0):**
   - The enum value `ComplianceMode.FEDRAMP`, the `ComplianceHandler._configure_mode` branch, the `enhancer.py` warning block, and the `"fedramp"` entry in `config.py`'s `valid_values` set are all scheduled for deletion in the v2.0.0 breaking-changes window. This ADR serves as the deprecation notice.

4. **Re-introduction criteria:**
   - This decision is **reversible**. If a design partner with a FedRAMP ATO (or credible path to one) commits to the AIPEA integration and funds or budgets the enforcement work, Path A can be re-opened.
   - Re-introduction must include: a named customer and use case, a minimum-viable enforcement surface designed with their input, a security audit scope, and a realistic implementation schedule before any marketing language returns to the README.

## Consequences

### Positive

- **Honesty.** The stated compliance surface now matches the implemented compliance surface. A diligence reviewer reading the README cannot reach a false conclusion about FedRAMP support in three seconds of skimming.
- **Lowered regulatory liability.** AIPEA can no longer be marketed as "FedRAMP-ready" by accident. Integrators shipping to FedRAMP environments cannot rely on AIPEA's mode to satisfy any FedRAMP control.
- **Clearer roadmap.** Engineering effort that would have been spent maintaining the illusion of FedRAMP support can be redirected to features with actual demand (P3b Adaptive Learning, P5d mutation + performance gating, D4 adversarial red-team corpus).
- **Preserved optionality.** The enum value remains (for one more major version), so existing integrators — to the extent any exist — are not broken on upgrade. The deprecation warning gives them a visible migration signal.

### Negative

- **Narrows the regulated-AI wedge.** The positive investor review argued that AIPEA's strongest defensible moat is *offline/regulated* workloads. Removing FedRAMP narrows that story — the supported regulated modes are now HIPAA and TACTICAL only. This is acceptable because neither of those has a customer either, and an honest two-mode offering is more credible than an inflated four-mode one.
- **Deprecation warning will surface in any integrator that currently uses the mode.** This is intentional; the whole point is visible signaling. Accepting one cycle of upgrade noise in exchange for honest framing.
- **SemVer slip.** Hard removal of the enum value requires a v2.0.0 major bump on a future release. AIPEA has no v2.0.0 scheduled; this ADR effectively reserves one breaking change for it. That is a small cost on a young library.

### Neutral

- **HIPAA and TACTICAL modes are unchanged.** They remain detection + model-allowlist controls with runtime warnings — documented honestly in the Wave B (2026-04-11) README rewrite and in `SECURITY.md`. Nothing about their enforcement posture changes.
- **Governance templates (`docs/compliance/*.md`) are unchanged.** Those files reference FedRAMP as one of several control frameworks being mapped (alongside SOC 2, ISO 42001, NIST AI RMF). They describe *AIPEA's compliance-with-its-own-governance-standards* posture, not AIPEA's feature surface. Their FedRAMP references remain accurate.

## Alternatives Considered

### Alternative 1 — Path A: Build real FedRAMP enforcement

Rejected. No customer, no budget, no realistic path to an ATO without a design partner funding it. Building enforcement speculatively would be months of engineering work to serve zero paying users, with the meta-risk that we'd ship another form of compliance theater (the checkbox version, with real code but no third-party validation).

### Alternative 2 — Hard-remove the enum value immediately

Rejected for this release. Removing a public enum value is a breaking API change per SemVer. AIPEA's versioning discipline (`CLAUDE.md §11.1`) reserves major-version bumps for breaking changes. A v2.0.0 release requires coordination with any integrators (Agora IV, AEGIS, external PyPI users) and a deprecation window. Shipping the deprecation *now* and the removal *in v2.0.0* is the disciplined path.

### Alternative 3 — Silent soft-removal: just remove the README claim but leave the code unchanged

Rejected. The adversarial review specifically cited the gap between the documentation (quiet FedRAMP mention) and the code (honestly-labeled stub). Closing only the documentation side without any runtime signal means a *new* integrator in six months, looking only at the enum, would still reach the wrong conclusion. The deprecation warning is the mechanism that carries the honest signal forward.

### Alternative 4 — Keep FedRAMP, add an explicit disclaimer to every mention

Rejected. That was arguably the *pre-Wave-B* state: the README table Wave B added already says *"FEDRAMP — Unenforced configuration stub. The enum value exists; there is no behavioral enforcement. Does not implement FedRAMP controls."* But the mode is still being *offered* in the table, which invites the misunderstanding that AIPEA is a partial-FedRAMP solution. Removing the offer entirely is stronger.

## References

- Positive investor review: `docs/claude/audits/investor-review-2026-04-11.md` §P5b
- Adversarial investor review: `docs/claude/audits/investor-review-adversarial-2026-04-11.md` §4 ("Compliance theater")
- Roadmap item: `docs/ROADMAP.md` §P5b
- Original stub implementation: `src/aipea/security.py` `ComplianceHandler._configure_mode` (FEDRAMP branch)
- Consolidated response plan: `~/.claude/plans/reactive-growing-lark.md` Wave C2 (local)

---

*ADR-002 | AIPEA FedRAMP removal | 2026-04-11 | accepted*
