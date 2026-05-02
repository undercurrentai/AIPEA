# AIPEA / AEGIS / Agora IV — Positioning

> Honors the ADR-005 §12 Q5 commitment to formalize the open-core
> step-up that distinguishes AIPEA (free, MIT) from the paid products
> built on top of it. ≤500 words. Audience: prospective adopters,
> investors, and contributors who need a clean one-sentence answer to
> "what does each layer actually do?"

---

## One-line summary

**AIPEA detects. AEGIS enforces and governs. Agora IV orchestrates.**

Three layers, three distinct jobs, three distinct surface areas. Each
layer is independently usable; the value compounds when stacked.

---

## Layer 1 — AIPEA (this repo): detection substrate

**License**: MIT.
**Distribution**: PyPI (`pip install aipea`).
**Scope**: input inspection, query analysis, model-specific prompt
formatting, multi-provider search orchestration, offline knowledge
retrieval.

**What AIPEA does**:
- Scans prompts for prompt-injection patterns, PII / PHI / classified
  markers (per the active `ComplianceMode`).
- Returns a `ScanResult` whose `flags`, `is_blocked`, and
  `force_offline` fields the integrator's application layer reads.
- Configures advisory metadata (`audit_retention_days`,
  `encryption_required`, `phi_redaction_enabled`) that integrators
  consume.
- Validates the LLM model identifier against per-mode allowlists
  (substring match) plus a global forbidden list.

**What AIPEA does NOT do** (per `SPECIFICATION.md §3.1.3` and
`SECURITY.md §Compliance Modes`):
- Persist any audit log.
- Encrypt anything at rest or in transit.
- Redact PHI; flag-only.
- Block network egress; `force_offline=True` is an advisory flag the
  integrator's infrastructure must honor.
- Execute Business Associate Agreements.
- Provide SOC 2 / HIPAA / FedRAMP certification.

This boundary is intentional: AIPEA is a **detection substrate**, not
a regulatory compliance product.

---

## Layer 2 — AEGIS: enforcement + governance

**Distribution**: [`undercurrentai/aegis-governance`](https://github.com/undercurrentai/aegis-governance)
(Tier-1 commercial product; $10K-$15K ACV per Undercurrent Holdings'
public product matrix).
**Scope**: enforcement actions, policy administration, audit-trail
persistence, governance workflows, regulatory-evidence generation.

**What AEGIS adds on top of AIPEA detection**:
- **Enforcement**: redaction, blocking, role-based policy gates on
  AIPEA's `flags`.
- **Audit-trail persistence**: tamper-evident storage of scan results
  + decision logs to a compliant backend.
- **Governance workflows**: human-review escalation, policy-violation
  dashboards, regulatory-reporting templates (NIST AI RMF, EU AI
  Act).
- **Compliance certification scaffolding**: BAA execution support,
  SOC 2 Type II audit artifacts, FedRAMP-Moderate readiness checklist.

**Integration**: AEGIS depends on AIPEA as an optional dependency. The
adapter at `aegis-governance/src/integration/aipea_bridge.py`
preprocesses claims through `aipea.enhance_prompt()`, then maps the
result fields onto AEGIS's gate-evaluation contract.

---

## Layer 3 — Agora IV: multi-model orchestration

**Distribution**: [`undercurrentai/agora-iv`](https://github.com/undercurrentai/agora-iv)
(Tier-2 commercial product).
**Scope**: multi-LLM coordination, dialogical-clarification flows,
cross-model verdict aggregation.

**What Agora IV adds on top of AIPEA detection (and optionally AEGIS
enforcement)**:
- **Multi-model coordination**: Power-Communal Wisdom (PCW) protocol —
  N parallel LLMs vote on a single query; consensus or escalation
  per configurable threshold.
- **Dialogical clarification**: detects ambiguous queries (via AIPEA's
  `QueryAnalyzer`) and surfaces clarification prompts to users.
- **Strategy library**: 6 named enhancement strategies
  (specification-extraction, hypothesis-clarification, etc.) selected
  per query.

**Integration**: Agora IV consumes AIPEA via shim re-exports preserving
its 2,187+ test suite without import-path churn. AEGIS sits between
Agora IV's models and the user when enterprise governance is required.

---

## Why this stack

Each layer can be adopted independently. The cleanest mental model is:

| Layer | Cost | License | Ships in |
|---|---|---|---|
| **AIPEA** (detection) | free | MIT | PyPI: `aipea` |
| **AEGIS** (enforcement + governance) | $10K-$15K ACV | proprietary | repo: `undercurrentai/aegis-governance` |
| **Agora IV** (multi-model orchestration) | tiered | proprietary | repo: `undercurrentai/agora-iv` |

Adopters who need only detection install AIPEA and consume the
`ScanResult`. Adopters who need enforcement or audit-trail buy AEGIS.
Adopters who need multi-model coordination buy Agora IV.

The value pivot, from an open-core perspective: AIPEA is *deliberately
easy to rebuild* (~10,662 LOC, stdlib + httpx, MIT). The moat lives in
AEGIS and Agora IV — the layers AIPEA was designed to make
unnecessary-to-rebuild **above the detection substrate**.

---

*Authored 2026-05-02 to close [ADR-005 §12 Q5](adr/ADR-005-pr52-vc-adversarial-review-response.md)
and PR #52 review §7.5 diligence question. Updates ship in
[CHANGELOG.md](../CHANGELOG.md) when material claims change. See
[SPECIFICATION.md §3.1.3](../SPECIFICATION.md) for the
ComplianceHandler enforcement contract and
[SECURITY.md §Compliance Modes](../SECURITY.md) for the honest-scope
disclosure.*
