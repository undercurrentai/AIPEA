<!-- SOC 2 P1.x | EU AI Act Art. 16 | ISO 42001 Support | NIST AI RMF GOVERN -->
# Data Subject Rights (DSR) / Privacy Operations — Template

> **Instructions**: Replace all `<placeholder>` values with your organization's actual data.
> Remove this instruction block before finalizing.

---

## 1. Purpose & Scope

Establish procedures for handling data subject rights requests in compliance with applicable privacy regulations (GDPR, CCPA/CPRA, EU AI Act, and contractual obligations).

**Applicable regulations**: `<GDPR, CCPA/CPRA, other state/country privacy laws>`

**In-scope data**: `<All personal data processed by the organization and its subprocessors>`

---

## 2. Roles & Responsibilities

| Role | Responsibility | Assignee |
|------|---------------|----------|
| **Privacy Officer / DPO** | Overall DSR program oversight, regulatory liaison | `<name>` |
| **DSR Request Handler** | Intake, identity verification, request routing | `<name / team>` |
| **Engineering Lead** | Technical execution of data retrieval, deletion, correction | `<name / team>` |
| **Legal Counsel** | Exemption determinations, regulatory interpretation | `<name>` |
| **AI Safety Lead** | AI-specific data requests (training data, inference logs) | `<name>` |

---

## 3. Supported Request Types

| Request Type | Description | Regulatory Basis | SLA |
|-------------|------------|-----------------|-----|
| **Access (portability)** | Provide copy of all personal data held | GDPR Art. 15, 20; CCPA 1798.100 | `<30 days>` |
| **Deletion (erasure)** | Delete all personal data (right to be forgotten) | GDPR Art. 17; CCPA 1798.105 | `<30 days>` |
| **Correction (rectification)** | Correct inaccurate personal data | GDPR Art. 16; CCPA 1798.106 | `<30 days>` |
| **Restriction of processing** | Limit how personal data is used | GDPR Art. 18 | `<30 days>` |
| **Objection to processing** | Object to specific processing activities | GDPR Art. 21 | `<30 days>` |
| **Objection to automated decisions** | Right not to be subject to solely automated decisions | GDPR Art. 22; EU AI Act Art. 86 | `<30 days>` |
| **Opt-out of sale/sharing** | Opt out of data sale or cross-context behavioral advertising | CCPA 1798.120 | `<15 business days>` |

---

## 4. Request Intake Process

### 4.1 Submission Channels

| Channel | URL / Address | Available To |
|---------|-------------|-------------|
| Privacy portal | `<URL>` | All data subjects |
| Email | `<privacy@example.com>` | All data subjects |
| In-app settings | `<Feature description>` | Authenticated users |
| Postal mail | `<Address>` | All data subjects |

### 4.2 Intake Checklist

- [ ] Request received and logged with unique tracking ID
- [ ] Acknowledgement sent to requester within `<3 business days>`
- [ ] Request type identified (access, deletion, correction, etc.)
- [ ] Requester's identity verified (see Section 5)
- [ ] Authorized agent verification completed (if applicable)
- [ ] Request routed to appropriate handler
- [ ] SLA clock started

---

## 5. Identity Verification

Before fulfilling any DSR, the requester's identity must be verified to prevent unauthorized disclosure.

### 5.1 Verification Methods

| Verification Level | When Required | Method |
|-------------------|---------------|--------|
| **Standard** | Access, correction requests | Email verification to account email + 2 data point match |
| **Enhanced** | Deletion, restriction requests | Standard + government ID or notarized request |
| **Agent verification** | Authorized agent submits on behalf | Signed authorization + agent ID + data subject verification |

### 5.2 Verification Data Points (match 2 of 4)

- Account email address
- Last 4 digits of payment method
- Account creation date
- Recent transaction or activity detail

**Failed verification**: If identity cannot be verified within `<10 business days>`, notify requester and close request with documented reason.

---

## 6. Fulfillment Procedures

### 6.1 Access / Portability

1. Identify all data stores containing the subject's personal data
2. Extract data from each store (see data map in Section 8)
3. Compile into machine-readable format (JSON or CSV)
4. Review for third-party personal data (redact if present)
5. Deliver via secure channel (encrypted download link, expiry: 7 days)
6. Log fulfillment with evidence

### 6.2 Deletion / Erasure

1. Identify all data stores containing the subject's personal data
2. Determine if any exemptions apply (see Section 7)
3. Execute deletion across all primary data stores
4. Queue deletion from backups (next backup rotation cycle)
5. Notify subprocessors to delete (with confirmation tracking)
6. Verify deletion completeness
7. Retain minimal record of the deletion request itself (for audit trail)

**AI-specific considerations**:
- Training data: If subject's data was used in model training, document whether retraining is feasible
- Inference logs: Delete inference inputs/outputs containing personal data
- Model artifacts: If deletion from trained model is infeasible, document and disclose per GDPR Art. 17(1)

### 6.3 Correction / Rectification

1. Identify all data stores containing the inaccurate data
2. Verify the correct data provided by the requester
3. Update records across all primary data stores
4. Notify subprocessors of corrections
5. Log the correction with before/after evidence

### 6.4 Objection to Automated Decisions

1. Identify the automated decision system involved
2. Provide human review of the specific decision
3. Document the human reviewer's assessment
4. Communicate outcome to data subject with explanation
5. Update oversight plan if systemic issues identified

---

## 7. Exemptions

Certain requests may be partially or fully denied under legal exemptions:

| Exemption | Applicable To | Regulation | Documentation Required |
|-----------|-------------|-----------|----------------------|
| Legal obligation | Deletion | GDPR Art. 17(3)(b) | Cite specific legal requirement |
| Legitimate interests | Deletion, objection | GDPR Art. 17(3)(e) | Balancing test documented |
| Legal claims | Deletion | GDPR Art. 17(3)(e) | Active or pending litigation |
| Fraud prevention | Deletion | CCPA 1798.105(d)(2) | Document fraud risk |
| Compliance evidence | Deletion | Various | Regulatory retention period |

**All exemptions must be**: documented with legal justification, approved by Legal Counsel, communicated to the requester with explanation.

---

## 8. Data Map (Personal Data Inventory)

| Data Store | Personal Data Fields | Purpose | Deletion Method | Responsible Team |
|-----------|---------------------|---------|----------------|-----------------|
| `<Primary DB>` | `<name, email, etc.>` | `<Account management>` | `<SQL DELETE + verify>` | `<Engineering>` |
| `<Object storage>` | `<Documents, uploads>` | `<User content>` | `<S3 delete + lifecycle>` | `<Engineering>` |
| `<Analytics>` | `<Usage data, IPs>` | `<Product analytics>` | `<API delete>` | `<Data team>` |
| `<Email provider>` | `<Email, name>` | `<Notifications>` | `<API delete>` | `<Engineering>` |
| `<AI training data>` | `<Inference I/O>` | `<Model training>` | `<Dataset filter + retrain>` | `<ML team>` |
| `<Logs>` | `<IPs, user agents>` | `<Security / audit>` | `<TTL expiry>` | `<Infrastructure>` |
| `<Backups>` | `<All of above>` | `<Disaster recovery>` | `<Next rotation cycle>` | `<Infrastructure>` |

---

## 9. Subprocessor DSR Coordination

| Subprocessor | Data Held | Deletion API/Process | SLA | Contact |
|-------------|----------|---------------------|-----|---------|
| `<name>` | `<data types>` | `<Method>` | `<SLA>` | `<contact>` |
| `<name>` | `<data types>` | `<Method>` | `<SLA>` | `<contact>` |

---

## 10. Metrics & Reporting

| Metric | Target | Reporting Frequency |
|--------|--------|-------------------|
| Requests received (by type) | Tracking only | Monthly |
| Average fulfillment time | `< 20 days` | Monthly |
| SLA compliance rate | `> 95%` | Monthly |
| Requests denied (with reason) | Tracking only | Quarterly |
| Verification failure rate | `< 10%` | Quarterly |

**Regulatory reporting**: Prepare annual summary of DSR activity for DPO review and potential regulatory disclosure.

---

## 11. Document Control

| Field | Value |
|-------|-------|
| **Owner** | `<Privacy Officer / DPO>` |
| **Last reviewed** | `<date>` |
| **Next review** | `<date — annually or after regulatory change>` |
| **Approval** | `<approver name and date>` |
| **Version** | `<version number>` |
