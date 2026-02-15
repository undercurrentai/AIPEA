<!-- FedRAMP SA-12 | SOC 2 CC9.x | ISO 42001 Support | NIST AI RMF GOVERN -->
# Vendor Risk Assessment — Template

> **Instructions**: Complete one assessment per vendor. Replace all `<placeholder>` values.
> Remove this instruction block before finalizing.

---

## 1. Vendor Overview

| Field | Value |
|-------|-------|
| **Vendor name** | `<vendor name>` |
| **Service provided** | `<description of services>` |
| **Contract owner** | `<internal owner name>` |
| **Contract start / renewal** | `<start date>` / `<renewal date>` |
| **Data processed** | `<types of data the vendor handles>` |
| **Data classification** | `<Public / Internal / Confidential / Restricted>` |
| **Data residency** | `<countries / regions where data is stored>` |
| **Subprocessors** | `<Yes / No — if yes, list in Section 6>` |

---

## 2. Criticality Tier

| Tier | Criteria | Review Frequency |
|------|----------|-----------------|
| **Critical** | Service outage causes immediate customer impact; processes restricted data | Quarterly |
| **High** | Service outage causes internal disruption; processes confidential data | Quarterly |
| **Medium** | Service degradation is tolerable short-term; processes internal data | Semi-annually |
| **Low** | Service is non-essential; processes public data only | Annually |

**This vendor's tier**: `<Critical / High / Medium / Low>`

**Quarterly reviews**: Tracked via `vendor-risk-assessment.yml` GitHub issue template.

**Justification**: `<Why this tier was assigned>`

---

## 3. Security Posture Assessment

### 3.1 Certifications & Reports

| Certification | Status | Report Date | Expiry | On File |
|--------------|--------|-------------|--------|---------|
| SOC 2 Type 2 | `<Current / Expired / N/A>` | `<date>` | `<date>` | `<Y / N>` |
| ISO 27001 | `<Current / Expired / N/A>` | `<date>` | `<date>` | `<Y / N>` |
| ISO 42001 (AI) | `<Current / Expired / N/A>` | `<date>` | `<date>` | `<Y / N>` |
| FedRAMP | `<Authorized / In Process / N/A>` | `<date>` | -- | `<Y / N>` |
| PCI DSS | `<Current / Expired / N/A>` | `<date>` | `<date>` | `<Y / N>` |
| Penetration test | `<Completed / N/A>` | `<date>` | -- | `<Y / N>` |

### 3.2 Security Questionnaire

- [ ] Vendor completed security questionnaire (SIG Lite, CAIQ, or custom)
- [ ] Encryption at rest: `<AES-256 / other / none>`
- [ ] Encryption in transit: `<TLS 1.2+ / other / none>`
- [ ] MFA enforced for administrative access: `<Yes / No>`
- [ ] Vulnerability management program in place: `<Yes / No>`
- [ ] Incident response plan documented: `<Yes / No>`
- [ ] Background checks on personnel with data access: `<Yes / No>`

---

## 4. Data Protection Assessment

| Control | Status | Notes |
|---------|--------|-------|
| **Data encryption at rest** | `<Yes / No / Partial>` | `<Details>` |
| **Data encryption in transit** | `<Yes / No / Partial>` | `<Details>` |
| **Data residency compliance** | `<Compliant / Non-compliant>` | `<Regions>` |
| **Data retention & deletion** | `<Documented / Undocumented>` | `<Retention period>` |
| **DSR handling capability** | `<Yes / No>` | `<Can process access/deletion requests>` |
| **Data minimization** | `<Yes / No>` | `<Only processes what is necessary>` |
| **Backup & recovery** | `<Documented / Undocumented>` | `<RPO/RTO targets>` |

---

## 5. Contractual Controls

| Control | Status | Document |
|---------|--------|----------|
| **Data Processing Agreement (DPA)** | `<Signed / Pending / N/A>` | `<Link or reference>` |
| **Breach notification clause** | `<Yes — within X hours / No>` | `<DPA section>` |
| **Subprocessor notification** | `<Yes / No>` | `<DPA section>` |
| **Right to audit** | `<Yes / No>` | `<Contract section>` |
| **Data return / deletion on termination** | `<Yes / No>` | `<Contract section>` |
| **Liability / indemnification** | `<Documented / Undocumented>` | `<Contract section>` |
| **SLA with penalties** | `<Yes / No>` | `<Contract section>` |

---

## 6. Subprocessor Review

| Subprocessor | Service | Data Access | Location | Risk |
|-------------|---------|-------------|----------|------|
| `<name>` | `<service>` | `<data types>` | `<country>` | `<Low / Medium / High>` |
| `<name>` | `<service>` | `<data types>` | `<country>` | `<Low / Medium / High>` |

**Subprocessor change notification**: `<How the vendor notifies of subprocessor changes>`

---

## 7. AI-Specific Assessment (if applicable)

Complete this section if the vendor provides AI/ML services:

| Control | Status | Notes |
|---------|--------|-------|
| **Model transparency** | `<Yes / No>` | `<Vendor provides model documentation>` |
| **Training data governance** | `<Documented / Undocumented>` | `<Data sourcing, consent, bias checks>` |
| **Human oversight capability** | `<Yes / No>` | `<Ability to override AI decisions>` |
| **Output logging / auditability** | `<Yes / No>` | `<AI outputs are logged and accessible>` |
| **Bias monitoring** | `<Yes / No>` | `<Regular fairness assessments>` |
| **EU AI Act compliance** | `<Compliant / In progress / N/A>` | `<GPAI / High-risk classification>` |

---

## 8. Risk Scoring

| Risk Category | Score (1-5) | Weight | Weighted Score |
|--------------|-------------|--------|----------------|
| **Data sensitivity** | `<1-5>` | 3 | `<score>` |
| **Security posture** | `<1-5>` | 3 | `<score>` |
| **Business criticality** | `<1-5>` | 2 | `<score>` |
| **Contractual coverage** | `<1-5>` | 1 | `<score>` |
| **Regulatory alignment** | `<1-5>` | 1 | `<score>` |
| **Total** | -- | -- | `<total / 50>` |

**Risk rating**: `<Low (0-15) / Medium (16-30) / High (31-40) / Critical (41-50)>`

---

## 9. Residual Risk & Approval

| Field | Value |
|-------|-------|
| **Overall risk rating** | `<Low / Medium / High / Critical>` |
| **Residual risks** | `<List any risks not fully mitigated>` |
| **Mitigating controls** | `<Internal controls that reduce residual risk>` |
| **Risk acceptance** | `<Accepted / Conditionally accepted / Rejected>` |
| **Conditions (if conditional)** | `<What must be remediated and by when>` |
| **Approved by** | `<name, title>` |
| **Approval date** | `<date>` |
| **Next review date** | `<date — per criticality tier frequency>` |
