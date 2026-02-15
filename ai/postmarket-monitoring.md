<!-- EU AI Act Art. 72 | FedRAMP CA-7 | SOC 2 CC4.x | ISO 42001 Improvement | NIST AI RMF MANAGE -->
# Post-Market Monitoring Plan (Template)

## Objectives
- Detect performance regressions, safety incidents, bias, and data drifts post-deployment.

## Indicators & Thresholds
- Accuracy delta > X% vs. baseline
- Increase in PII leak flags
- Prompt-jailbreak success rate > threshold
- Drift metrics > threshold

## Activities
- Weekly metrics review; monthly deep dives
- Quarterly red-team exercises
- Feedback intake from users & support

## Serious Incident Process (EU AI Act context)

### Definition of Serious Incident
A serious incident is any event or malfunction that directly or indirectly leads to, or is reasonably likely to lead to, any of the following:

1. **Safety violation** — Physical harm, property damage, or environmental harm caused by or attributable to AI system behavior
2. **PII / data exposure** — Unauthorized disclosure of personal data or special-category data through model outputs, logs, or side channels
3. **Discrimination detected** — Systematic bias in outputs that results in unlawful discrimination against individuals or groups (per EU AI Act Art. 9, Art. 10 fairness requirements)
4. **Accuracy degradation causing harm** — Model performance falling below defined thresholds in a way that leads to incorrect decisions affecting health, safety, or fundamental rights
5. **Loss of human oversight** — System operating autonomously in a context that requires human-in-the-loop or human-on-the-loop controls (per oversight-plan.md)

### Example Incidents (calibration for consuming projects)
- Model recommends a harmful action that bypasses safety filters and reaches a user
- Batch inference job exposes PII from training data in production outputs
- Fairness probe detects >20% performance disparity across protected groups
- Automated decision system denies services without required human review
- Adversarial prompt successfully exfiltrates system instructions or user data

### Notification Timeline (per EU AI Act Art. 73)
| Step | Timeline | Action |
|------|----------|--------|
| Detection & triage | Immediate | Classify severity; activate incident response |
| Internal escalation | Within 4 hours | Notify AI Risk Officer, Legal, CISO |
| Authority notification (EU) | Immediately upon establishing causal link; no later than 15 days after awareness (Art. 73(1)) | Report to relevant national competent authority via designated channel |
| GDPR breach notification (if PII involved) | Within 72 hours (GDPR Art. 33) | Notify supervisory authority if personal data breach |
| Affected parties | Without undue delay | Notify affected users/deployers as required |
| Follow-up report | Within 30 days | Submit detailed root cause analysis and corrective actions |

### Report Content Requirements
Each serious incident report must include:
- AI system identification (name, version, `system-register.yaml` ID)
- Description of the incident and circumstances
- Corrective actions taken or planned
- Impact assessment (persons affected, severity)
- Link to relevant log events (see `technical_file/logs/`)

## Continuous Improvement
- Feed findings back into risk register and model/data updates.
