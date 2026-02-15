<!-- FedRAMP PL-2, SA-4 | SOC 2 CC1.x/CC2.x | ISO 42001 Planning -->
# System Description (SOC 2 / FedRAMP Support) — Template

> **Instructions**: Replace all `<placeholder>` values with your organization's actual data.
> Remove this instruction block before finalizing.

---

## 1. Overview

### 1.1 Organization

| Field | Value |
|-------|-------|
| **Organization name** | `<organization name>` |
| **Service name** | `<service / product name>` |
| **Description** | `<Brief description of what the service does>` |
| **Service type** | `<SaaS / PaaS / IaaS / AI-as-a-Service>` |
| **Primary users** | `<Target user base>` |

### 1.2 Services In Scope

| Service | Description | Deployment | Criticality |
|---------|------------|------------|-------------|
| `<Service 1>` | `<What it does>` | `<AWS / GCP / Azure region(s)>` | Tier 1 (Critical) |
| `<Service 2>` | `<What it does>` | `<Deployment location>` | Tier 2 (Important) |
| `<Service 3>` | `<What it does>` | `<Deployment location>` | Tier 3 (Standard) |

### 1.3 System Boundaries

**In scope**: `<All production systems, databases, APIs, AI models, and supporting infrastructure>`

**Out of scope**: `<Development environments, personal devices, third-party end-user devices>`

**Boundary justification**: `<Why the boundary is drawn here — e.g., these are the systems that store, process, or transmit customer data>`

---

## 2. Architecture & Components

### 2.1 Component Inventory

| Component | Technology | Purpose | Data Handled |
|-----------|-----------|---------|-------------|
| **API Gateway** | `<e.g., AWS API Gateway>` | Request routing, rate limiting | Request metadata |
| **Application Server** | `<e.g., ECS Fargate, Lambda>` | Business logic | Customer data, AI inputs/outputs |
| **Database** | `<e.g., RDS PostgreSQL>` | Persistent storage | All customer data |
| **Cache** | `<e.g., ElastiCache Redis>` | Session state, query cache | Session tokens, cached queries |
| **AI/ML Infrastructure** | `<e.g., SageMaker, custom>` | Model training and inference | Training data, inference inputs/outputs |
| **Object Storage** | `<e.g., S3>` | File storage, backups | Documents, model artifacts, logs |
| **Message Queue** | `<e.g., SQS, Kafka>` | Async processing | Event payloads |
| **CDN** | `<e.g., CloudFront>` | Static asset delivery | Public assets |
| **Monitoring** | `<e.g., CloudWatch, Datadog>` | Observability | Metrics, logs, traces |

### 2.2 Architecture Diagram

`<Insert or link to architecture diagram showing component relationships, data flows, and trust boundaries>`

---

## 3. Data Flows

### 3.1 Data Ingress

| Source | Data Type | Protocol | Authentication | Encryption |
|--------|----------|----------|---------------|------------|
| End users (web/mobile) | API requests | HTTPS (TLS 1.2+) | JWT / OAuth 2.0 | TLS in transit |
| Partner integrations | API requests | HTTPS (TLS 1.2+) | API key + mTLS | TLS in transit |
| Data pipelines | Batch data | `<Protocol>` | `<Auth method>` | `<Encryption>` |

### 3.2 Data Egress

| Destination | Data Type | Protocol | Purpose | Controls |
|-------------|----------|----------|---------|----------|
| End users | API responses | HTTPS | Service delivery | Response filtering, rate limiting |
| Email provider | Notifications | HTTPS API | Transactional email | Minimal PII, no sensitive data |
| Analytics | Aggregated metrics | HTTPS | Business intelligence | Anonymized / aggregated only |
| AI model providers | Inference requests | HTTPS | AI processing | Data minimization, no PII where possible |

### 3.3 Data at Rest

| Data Store | Data Classification | Encryption | Access Control | Retention |
|-----------|-------------------|------------|---------------|-----------|
| Primary DB | Confidential | AES-256 | IAM + app-level RBAC | `<Per retention policy>` |
| Object storage | Varies | AES-256 (SSE-S3/KMS) | IAM bucket policies | `<Per lifecycle rules>` |
| Logs | Internal | AES-256 | IAM + log group policies | `<90 days hot, 7 years cold>` |
| Backups | Confidential | AES-256 | IAM + cross-account | `<Per BCP-DRP.md>` |

---

## 4. Subservice Organizations

| Vendor | Service | SOC 2 / ISO 27001 | Data Processed | Responsibility |
|--------|---------|-------------------|----------------|---------------|
| `<Cloud provider>` | IaaS / PaaS | `<Report on file: Y/N>` | All customer data | Infrastructure, physical security |
| `<DNS provider>` | DNS hosting | `<Report on file: Y/N>` | Domain records | DNS resolution, DDoS protection |
| `<Email provider>` | Transactional email | `<Report on file: Y/N>` | Email addresses, names | Email delivery |
| `<Monitoring provider>` | Observability | `<Report on file: Y/N>` | Logs, metrics, traces | Monitoring, alerting |
| `<AI model provider>` | AI inference | `<Report on file: Y/N>` | Inference inputs/outputs | Model hosting, inference |

**Complementary User Entity Controls (CUECs)**: `<Document any controls that subservice organizations expect you to implement>`

---

## 5. Applicable Trust Services Criteria

| Category | Applicable | Key Controls |
|----------|-----------|-------------|
| **Security (CC)** | Yes | Access control, encryption, vulnerability management, incident response |
| **Availability (A)** | `<Yes / No>` | SLOs, BCP/DRP, monitoring, redundancy |
| **Confidentiality (C)** | `<Yes / No>` | Data classification, encryption, access restrictions, DLP |
| **Processing Integrity (PI)** | `<Yes / No>` | Input validation, output verification, reconciliation |
| **Privacy (P)** | `<Yes / No>` | Notice, consent, data minimization, DSR handling |

---

## 6. Applicable Commitments

| Commitment | Source | Description |
|-----------|--------|-------------|
| SLA | Customer contracts | `<e.g., 99.9% uptime monthly>` |
| Data processing | DPA | `<e.g., Process data only per documented instructions>` |
| Breach notification | DPA / Contracts | `<e.g., Notify within 72 hours>` |
| Data residency | Contracts / Regulation | `<e.g., Data stored in US / EU only>` |
| Data retention | Privacy policy | `<e.g., Delete within 30 days of account closure>` |

---

## 7. Document Control

| Field | Value |
|-------|-------|
| **Owner** | `<name / role>` |
| **Last reviewed** | `<date>` |
| **Next review** | `<date — annually or when architecture changes>` |
| **Approval** | `<approver name and date>` |
| **Version** | `<version number>` |
