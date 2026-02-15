<!-- FedRAMP CM-2/3 | SOC 2 CC8.x | ISO 42001 Operation | NIST AI RMF MANAGE -->
# Change Management — Template

> **Instructions**: Replace all `<placeholder>` values with your organization's actual data.
> Remove this instruction block before finalizing.

---

## 1. Purpose & Scope

Ensure all changes to production systems, infrastructure, and AI models are planned, tested, approved, and documented to maintain system integrity and compliance.

**In-scope**: `<All production applications, infrastructure, databases, AI models, network configurations>`

**Out-of-scope**: `<Development/sandbox environments not connected to production data>`

---

## 2. Change Classes

Changes are classified per Engineering Standards S10 (Governance):

| Class | Description | Review Required | Auto-Merge Eligible | Examples |
|-------|-------------|-----------------|---------------------|----------|
| **Class A** | Style-only (formatting, comments, docs) | CI gates only | Yes | Code formatting, README updates, comment fixes |
| **Class B** | Refactor (behavior-preserving) | Peer review + perf verification + golden dataset check | No | Function extraction, dependency upgrade, query optimization |
| **Class C** | Behavioral (changes outputs) | Peer review + backtest delta report + risk sign-off | No | New feature, algorithm change, model retrain, schema migration |

---

## 3. Change Request Process

### 3.1 Request Submission

All changes require a pull request. Class B and C changes also require a change request issue using the `change-request.yml` GitHub issue template.

**Required fields**:
- [ ] Change class identified
- [ ] Risk level assessed (Low / Medium / High / Critical)
- [ ] Change description (what and why)
- [ ] Impact analysis (affected systems, users, services)
- [ ] Rollback plan documented and verified
- [ ] Test plan with acceptance criteria

### 3.2 Risk Assessment

| Risk Level | Criteria | Approval Required |
|------------|----------|-------------------|
| **Low** | No customer impact, easily reversible | Peer review |
| **Medium** | Limited customer impact, reversible with effort | Peer review + team lead |
| **High** | Significant customer impact or hard to reverse | Peer review + team lead + engineering manager |
| **Critical** | Production-wide impact, requires maintenance window | All above + executive sponsor |

### 3.3 Approval Matrix

| Change Class | Risk Level | Approvers | SLA |
|-------------|------------|-----------|-----|
| Class A | Any | CI gates (automated) | Immediate |
| Class B | Low/Medium | 1 peer reviewer | 1 business day |
| Class B | High/Critical | 2 reviewers + team lead | 2 business days |
| Class C | Low/Medium | 2 reviewers + team lead | 2 business days |
| Class C | High/Critical | 2 reviewers + team lead + eng manager | 3 business days |

---

## 4. CI Gate Requirements

All changes must pass these automated gates before merge:

| Gate | Class A | Class B | Class C |
|------|---------|---------|---------|
| Lint + format | Required | Required | Required |
| Unit tests | Required | Required | Required |
| Integration tests | -- | Required | Required |
| Performance benchmarks | -- | Required (no regression) | Required (delta report) |
| Golden dataset check | -- | Required (exact match) | Required (delta documented) |
| Security scan (semgrep/bandit) | Required | Required | Required |
| Merge blocker gates (S0) | Required | Required | Required |

---

## 5. Emergency Changes

Emergency changes bypass the standard approval process when there is an active Sev-1/2 incident.

**Requirements**:
- [ ] Incident ticket exists and is linked
- [ ] Incident Commander or on-call lead approves verbally
- [ ] Change is the minimum necessary to resolve the incident
- [ ] Retrospective change request filed within 2 business days
- [ ] Post-incident review covers the emergency change

**Emergency changes still require**:
- All CI gates to pass (no gate bypass)
- At least 1 peer review (can be synchronous/pair)
- Rollback plan documented (even if brief)

---

## 6. Rollback Procedures

Every Class B/C change must document a rollback plan before approval:

| Change Type | Rollback Method | Expected Duration |
|-------------|----------------|-------------------|
| Application code | Revert PR + redeploy | `< 15 min` |
| Database migration | Reverse migration script | `< 30 min` |
| Infrastructure (IaC) | Revert IaC + apply | `< 30 min` |
| AI model update | Revert to previous model version | `< 15 min` |
| Configuration change | Revert config + restart | `< 10 min` |

**Rollback trigger criteria**:
- Error rate exceeds `<threshold>` for `<duration>`
- Latency p99 exceeds `<threshold>` for `<duration>`
- Customer-reported issues correlated with deployment
- AI model outputs exceed drift/bias thresholds

---

## 7. AI Model Changes

AI model changes (retraining, fine-tuning, prompt changes, feature changes) are always Class C and require additional documentation:

- [ ] Model card updated with new version details
- [ ] Backtest delta report comparing old vs new model
- [ ] Bias/fairness metrics compared across protected groups
- [ ] Risk register reviewed and updated if risk profile changed
- [ ] Human oversight plan reviewed for adequacy
- [ ] Post-market monitoring baselines updated

---

## 8. Evidence & Audit Trail

All change evidence is preserved automatically via:

| Evidence Type | Source | Retention |
|---------------|--------|-----------|
| Change request | GitHub issue (change-request.yml template) | Indefinite (issue tracker) |
| Code review | PR comments and approvals | Indefinite (git history) |
| CI gate results | GitHub Actions logs | Per CI retention policy |
| Deployment logs | CI/CD pipeline output | `<retention period>` |
| Rollback events | Deployment logs + incident tickets | `<retention period>` |

---

## 9. Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Change failure rate | `< 15%` | Failed deployments / total deployments |
| Lead time for changes | `< 1 week (Class B), < 2 weeks (Class C)` | Commit to production |
| Mean time to restore | `< 1 hour` | Incident to rollback complete |
| Emergency change ratio | `< 10%` of total changes | Emergency changes / total changes |

---

## 10. Document Control

| Field | Value |
|-------|-------|
| **Owner** | `<name / role>` |
| **Last reviewed** | `<date>` |
| **Next review** | `<date — annually or after process change>` |
| **Approval** | `<approver name and date>` |
| **Version** | `<version number>` |
