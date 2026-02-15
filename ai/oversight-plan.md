<!-- EU AI Act Art. 14 | FedRAMP IR-4 | SOC 2 CC7.x | ISO 42001 Leadership | NIST AI RMF GOVERN -->
# Human Oversight Plan (Template)

## Roles & Responsibilities
- **Human Oversight Lead:** <name/email>
- **Escalation Contacts:** <oncall/security/legal>
- **Competence Requirements:** SMEs trained on system limits, privacy, and safety controls.

## Oversight Mode
- **Mode:** human-on-the-loop (define tasks where human approval is required)
- **Interventions:** escalate on low confidence; block on PII flag; manual review for sensitive intents.

## Triggers & Stop Conditions
- Confidence < threshold; safety policy violation; anomalous drift; repeated user complaints.

## Procedures
1. Review flagged sessions in monitoring dashboard.
2. Decide: allow, block, escalate, or retrain.
3. Document decision in ticketing system; link to log/event IDs.

## Training
- Initial training for reviewers; refresh every 6 months.

## Record-keeping
- Retain oversight decisions and rationale for ≥1 year; link to audit logs.
