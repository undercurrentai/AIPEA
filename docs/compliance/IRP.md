<!-- FedRAMP IR-4/5/6, SI-4 | SOC 2 CC7.x | EU AI Act Art. 73 | ISO 42001 Support | NIST AI RMF MANAGE -->
# Incident Response Plan (IRP) — Template

> **Instructions**: Replace all `<placeholder>` values with your organization's actual data.
> Remove this instruction block before finalizing.

---

## 1. Objectives & Scope

- Detect, contain, eradicate, and recover from security and AI-safety incidents.
- Minimize business impact and ensure regulatory notification obligations are met.
- Maintain evidence chain for forensic analysis and compliance audits.

**In-scope systems**: `<List all production systems, services, and data stores>`

**Out-of-scope**: `<List any explicitly excluded systems with justification>`

---

## 2. Definitions

| Term | Definition |
|------|-----------|
| **Incident** | An event that compromises the confidentiality, integrity, or availability of information or systems |
| **AI Safety Incident** | Unintended AI behavior causing harm, bias, or safety boundary violation (EU AI Act Art. 73) |
| **Data Breach** | Unauthorized access to or disclosure of personal or sensitive data |
| **Near Miss** | An event that could have resulted in an incident but did not |

---

## 3. Team & Roles

| Role | Responsibility | Primary | Backup |
|------|---------------|---------|--------|
| **Incident Commander (IC)** | Overall coordination, severity decisions, stakeholder communication | `<name>` | `<name>` |
| **Engineering Lead** | Technical investigation, containment, eradication | `<name>` | `<name>` |
| **Security Lead** | Forensic analysis, evidence preservation, threat intelligence | `<name>` | `<name>` |
| **Communications Lead** | Internal/external comms, regulatory notification | `<name>` | `<name>` |
| **Legal Counsel** | Regulatory obligations, breach notification timing | `<name>` | `<name>` |
| **AI Safety Lead** | AI-specific incidents, model behavior analysis | `<name>` | `<name>` |

**Escalation path**: On-call engineer -> Engineering Lead -> Incident Commander -> Executive sponsor

**Contact list**: `<Link to secure, always-accessible contact directory>`

**FedRAMP Security Inbox (FSI)**: `<registered FSI email address>` — monitored 24/7 for PMO Emergency, Emergency Test, and Important messages. Response SLAs: 12hr (high-impact Emergency), 2 business days (moderate), 3 business days (low).

---

## 4. Severity Classification

| Severity | Definition | Response Time | Examples |
|----------|-----------|---------------|---------|
| **Sev-1 (Critical)** | Active data breach, complete service outage, AI safety boundary violation | 15 min to triage | Unauthorized data exfiltration, ransomware, AI generating harmful outputs in production |
| **Sev-2 (High)** | Partial service degradation with customer impact, suspected breach | 1 hour to triage | Key service down, anomalous access patterns, AI model drift exceeding thresholds |
| **Sev-3 (Medium)** | Limited impact, no data exposure, service degradation without customer impact | 4 hours to triage | Non-critical service failure, failed intrusion attempt, AI performance degradation |
| **Sev-4 (Low)** | Informational, no immediate impact | Next business day | Policy violation without exposure, vulnerability disclosure, near miss |

---

## 5. Procedures

### 5.1 Detection & Triage (Phase 1)

- [ ] Alert received and acknowledged
- [ ] Initial severity classification assigned
- [ ] Incident Commander notified (Sev-1/2: immediately; Sev-3/4: within response time)
- [ ] Incident ticket created with unique ID
- [ ] Communication channel established (e.g., dedicated Slack channel, bridge call)
- [ ] Initial scope assessment: affected systems, data, users

**Evidence to collect immediately**:
- Timestamps (UTC) of first detection
- Alert source and raw alert data
- Affected system identifiers (hostnames, IPs, service names)
- Initial indicators of compromise (IOCs)

### 5.2 Containment (Phase 2)

- [ ] Short-term containment actions identified and approved by IC
- [ ] Containment implemented (e.g., network isolation, credential rotation, service shutdown)
- [ ] Verify containment is effective — confirm threat is no longer spreading
- [ ] Preserve forensic evidence before any remediation
- [ ] For AI incidents: disable affected model/feature, activate fallback or human-in-the-loop override

**Containment decision matrix**:

| Scenario | Containment Action |
|----------|-------------------|
| Compromised credentials | Rotate all affected credentials; revoke active sessions |
| Malware/ransomware | Isolate affected hosts from network |
| Data exfiltration | Block egress to identified destinations; revoke API keys |
| AI safety violation | Disable model serving; route to fallback/manual process |
| DDoS | Activate WAF rules; engage CDN/DDoS mitigation provider |

### 5.3 Eradication & Recovery (Phase 3)

- [ ] Root cause identified and documented
- [ ] Malicious artifacts removed (malware, backdoors, unauthorized accounts)
- [ ] Affected systems rebuilt or restored from known-good state
- [ ] Patches or configuration changes applied to prevent recurrence
- [ ] Systems returned to production with enhanced monitoring
- [ ] For AI incidents: retrained/patched model validated before re-deployment
- [ ] Verify recovery: functional tests, security scans, monitoring confirmation

### 5.4 Post-Incident Review (Phase 4)

- [ ] Post-incident review meeting scheduled (within 5 business days of resolution)
- [ ] Timeline of events documented
- [ ] Root cause analysis completed (5-whys or fishbone method)
- [ ] Lessons learned documented
- [ ] Action items assigned with owners and due dates
- [ ] IRP updated if procedural gaps identified
- [ ] Risk register updated if new risks identified

---

## 6. Reporting & Notifications

### 6.1 Internal Notifications

| Audience | Trigger | Timeline | Channel |
|----------|---------|----------|---------|
| Engineering team | All Sev-1/2 | Immediately | `<Slack channel / PagerDuty>` |
| Executive leadership | Sev-1 | Within 1 hour | `<Email / direct message>` |
| All staff | Data breach confirmed | Within 24 hours | `<Company-wide channel>` |

### 6.2 External / Regulatory Notifications

| Obligation | Trigger | Timeline | Authority |
|------------|---------|----------|-----------|
| GDPR (Art. 33) | Personal data breach | 72 hours | Supervisory authority |
| EU AI Act (Art. 73) | Serious AI incident | Without undue delay | National authority + market surveillance |
| State breach laws | PII breach (varies by state) | 30-60 days (varies) | State AG / affected individuals |
| FedRAMP (IR-6) | Security incident | Per agency SLA | Authorizing official |
| FedRAMP FSI (mandatory) | Suspected/confirmed significant incident | **1 hour** | FedRAMP PMO via Security Inbox |
| FedRAMP FSI — Emergency msg | Emergency communication received | 12hr (high) / 2BD (moderate) / 3BD (low) | FedRAMP PMO (respond via FSI) |
| SOC 2 auditor | Material incident | Next audit period | External auditor |
| Customers/DPA | Per contractual obligation | Per DPA terms | Affected customers |

**Notification template**: `<Link to pre-drafted notification templates>`

---

## 7. Evidence Preservation

All incident evidence must be preserved for audit and potential legal proceedings:

- [ ] System logs exported and stored immutably (write-once storage)
- [ ] Network captures saved (if applicable)
- [ ] Screenshots of dashboards, alerts, and anomalous behavior
- [ ] Communication logs (Slack exports, email threads)
- [ ] Timeline document with all actions and decisions
- [ ] Chain of custody maintained for forensic artifacts

**Retention period**: Minimum 7 years (FedRAMP) or per legal hold requirements.

---

## 8. Exercises & Testing

| Exercise Type | Frequency | Participants | Documentation |
|---------------|-----------|-------------|---------------|
| **Tabletop exercise** | Quarterly | IR team + relevant stakeholders | GitHub issue via `incident-response-drill.yml` template |
| **FSI Emergency Test drill** | Quarterly | FSI inbox monitors + IR team | Verify inbox receipt, respond within SLA, document |
| **Functional exercise** | Annually | IR team + engineering | Full drill report |
| **IRP review** | Annually (or after Sev-1/2) | IR team + legal | Updated IRP with change log |

### Exercise scenarios (rotate quarterly):
1. Unauthorized access to production database
2. Ransomware on developer workstation
3. AI model producing biased/harmful outputs
4. Supply chain compromise (dependency poisoning)
5. Insider threat / credential misuse
6. Cloud provider region outage with data implications

---

## 9. Metrics & Continuous Improvement

| Metric | Target | Measurement |
|--------|--------|-------------|
| Mean Time to Detect (MTTD) | `< 15 min (Sev-1)` | Alert timestamp - incident start |
| Mean Time to Respond (MTTR) | `< 1 hour (Sev-1)` | First responder action - alert timestamp |
| Mean Time to Resolve | `< 4 hours (Sev-1)` | Resolution - alert timestamp |
| Post-incident review completion | 100% for Sev-1/2 | Reviews completed within 5 business days |
| Action item closure rate | > 90% within 30 days | Tracked via issue tracker |

---

## 10. Document Control

| Field | Value |
|-------|-------|
| **Owner** | `<name / role>` |
| **Last reviewed** | `<date>` |
| **Next review** | `<date — quarterly or after any Sev-1/2 incident>` |
| **Approval** | `<approver name and date>` |
| **Version** | `<version number>` |
