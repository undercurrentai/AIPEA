<!-- FedRAMP AC-2, IA-5 | SOC 2 CC6.x | ISO 42001 Support -->
# Access Review — Quarterly Procedure & Checklist

> **Instructions**: Replace all `<placeholder>` values with your organization's actual data.
> Remove this instruction block before finalizing.

---

## 1. Purpose & Scope

Ensure that access to production systems, data stores, and administrative tools follows the principle of least privilege. Identify and remediate orphaned accounts, excessive permissions, and missing MFA enforcement.

**In-scope systems**: `<List all systems subject to quarterly access review>`

**Review frequency**: Quarterly (documented via `quarterly-access-review.yml` GitHub issue template)

---

## 2. Roles & Responsibilities

| Role | Responsibility |
|------|---------------|
| **Review Lead** | Coordinate the review, compile findings, file evidence |
| **System Owners** | Provide user exports, validate access appropriateness for their systems |
| **People/HR** | Confirm active employment status, role changes, terminations |
| **Security** | Review privileged access, MFA enforcement, service account usage |

---

## 3. Systems & Data Sources

| System | Type | User Export Method | Privileged Roles |
|--------|------|-------------------|-----------------|
| `<Identity Provider (IdP)>` | SSO / Directory | `<Admin console export / API>` | Global admin, group admin |
| `<Cloud provider (AWS/GCP/Azure)>` | Infrastructure | `<IAM user/role export>` | Root, admin, power user |
| `<Source control (GitHub/GitLab)>` | Development | `<Org member export / API>` | Owner, admin |
| `<Production database>` | Data store | `<User/role export>` | Superuser, write access |
| `<CI/CD platform>` | Deployment | `<Admin console>` | Pipeline admin, deploy |
| `<Monitoring/logging>` | Observability | `<User export>` | Admin, write |
| `<AI/ML platform>` | AI infrastructure | `<User/role export>` | Model deploy, data access |

---

## 4. Review Procedure

### Phase 1: Data Collection

- [ ] Export user list from Identity Provider (IdP)
- [ ] Export user/role lists from each in-scope system (see Section 3)
- [ ] Obtain current employee roster from HR/People team
- [ ] Obtain list of recent terminations, transfers, and role changes (since last review)
- [ ] Export service account inventory

### Phase 2: Analysis

- [ ] **Orphaned accounts**: Cross-reference system users against HR roster — flag accounts for terminated or transferred employees
- [ ] **Excessive permissions**: Identify users with admin/privileged access who don't require it for their current role
- [ ] **Shared accounts**: Identify any shared or generic accounts (should be eliminated or converted to service accounts)
- [ ] **Service accounts**: Verify each service account has a documented owner and justified scope
- [ ] **MFA enforcement**: Verify MFA is enabled for all human accounts, especially privileged accounts
- [ ] **Inactive accounts**: Flag accounts with no login activity in `<90 days>`
- [ ] **External / contractor access**: Verify all external accounts are still needed and have appropriate expiry dates

### Phase 3: Remediation

- [ ] Disable or delete orphaned accounts (within `<5 business days>` of identification)
- [ ] Downgrade excessive permissions to least-privilege
- [ ] Enable MFA on any non-compliant accounts (or disable account if MFA cannot be enforced)
- [ ] Remove or convert shared accounts
- [ ] Update service account documentation
- [ ] Set expiry dates on contractor/external accounts if missing

### Phase 4: Documentation & Evidence

- [ ] Compile review findings into quarterly access review report
- [ ] File evidence in GitHub issue (using `quarterly-access-review.yml` template)
- [ ] Attach user export CSVs (redact passwords/secrets if present in exports)
- [ ] Attach before/after screenshots showing remediation actions
- [ ] Obtain sign-off from Review Lead and system owners

---

## 5. Privileged Access Review (Enhanced)

Privileged accounts require additional scrutiny:

| Check | Status | Notes |
|-------|--------|-------|
| All privileged users justified by role | `<Pass / Fail>` | `<Details>` |
| Privileged access uses separate accounts (not daily-driver) | `<Pass / Fail>` | `<Details>` |
| MFA enforced on all privileged accounts | `<Pass / Fail>` | `<Details>` |
| Privileged session logging enabled | `<Pass / Fail>` | `<Details>` |
| Break-glass accounts documented and sealed | `<Pass / Fail>` | `<Details>` |
| Root/superuser credentials rotated per policy | `<Pass / Fail>` | `<Details>` |

---

## 6. Service Account Review

| Account | System | Owner | Purpose | Last Credential Rotation | Status |
|---------|--------|-------|---------|-------------------------|--------|
| `<account>` | `<system>` | `<owner>` | `<purpose>` | `<date>` | `<Active / Decommission>` |
| `<account>` | `<system>` | `<owner>` | `<purpose>` | `<date>` | `<Active / Decommission>` |

**Service account policy**: Credentials must be rotated every `<90 days>`. Accounts without a documented owner must be disabled.

---

## 7. Metrics

| Metric | This Quarter | Previous Quarter | Target |
|--------|-------------|-----------------|--------|
| Total accounts reviewed | `<count>` | `<count>` | 100% of in-scope |
| Orphaned accounts found | `<count>` | `<count>` | 0 |
| Excessive permissions found | `<count>` | `<count>` | Decreasing trend |
| MFA non-compliance | `<count>` | `<count>` | 0 |
| Remediation completion rate | `<% within SLA>` | `<%>` | > 95% |

---

## 8. Document Control

| Field | Value |
|-------|-------|
| **Owner** | `<name / role>` |
| **Last reviewed** | `<date>` |
| **Next review** | `<date — next quarter>` |
| **Approval** | `<approver name and date>` |
| **Version** | `<version number>` |
