# Logs Mapping — Field-to-Framework Reference

This folder documents how `schemas/log_event.schema.json` fields satisfy regulatory record-keeping requirements across EU AI Act, FedRAMP, and SOC 2.

---

## Field-to-Framework Mapping

| Schema Field | Required? | EU AI Act | FedRAMP | SOC 2 |
|-------------|-----------|-----------|---------|-------|
| `ts_utc` | Yes | Art. 12 (logging with timestamps) | AU-3 (content of audit records) | CC7.2 (monitoring) |
| `request_id` | Yes | Art. 12 (traceability of operations) | AU-3 (event correlation) | CC7.2 (event correlation) |
| `subject` | Yes | Art. 12 (identify actors) | AU-3 (identity of subject) | CC6.1 (logical access) |
| `action` | Yes | Art. 12 (type of operation) | AU-3 (type of event) | CC7.2 (event classification) |
| `object` | Yes | Art. 12 (resource accessed) | AU-3 (objects involved) | CC7.2 (affected resources) |
| `outcome` | Yes | Art. 12 (result of operation) | AU-3 (outcome) | CC7.2 (success/failure) |
| `seed_id` | No | Art. 12 (reproducibility) | -- | -- |
| `user_id` | No | Art. 12 (natural person linkage) | AU-3 (user identity) | CC6.1 (user identification) |
| `reason` | No | Art. 14 (explainability) | AU-3 (additional detail) | CC7.3 (root cause) |
| `src_ip` | No | -- | AU-3 (source address) | CC6.1 (network origin) |
| `agent_id` | No | Art. 12 (AI system identifier) | -- | -- |
| `dataset_hash` | No | Art. 10 (data provenance) | -- | -- |

---

## Example Log Events

### 1. Inference Request (normal operation)
```json
{
  "ts_utc": "2026-02-05T14:30:00.123Z",
  "request_id": "req-a1b2c3d4",
  "seed_id": "seed-7890",
  "user_id": "user-456",
  "subject": "inference-service",
  "action": "predict",
  "object": "model/example-llm/v1.2.3",
  "outcome": "allow",
  "reason": null,
  "src_ip": "10.0.1.42",
  "agent_id": "agent-main-001",
  "dataset_hash": "sha256:abcdef1234567890"
}
```

### 2. Human Oversight Intervention
```json
{
  "ts_utc": "2026-02-05T14:31:12.456Z",
  "request_id": "req-e5f6g7h8",
  "seed_id": null,
  "user_id": "reviewer-jane",
  "subject": "oversight-reviewer",
  "action": "block",
  "object": "response/req-a1b2c3d4",
  "outcome": "deny",
  "reason": "PII detected in model output; escalated per oversight-plan.md",
  "src_ip": "10.0.2.10",
  "agent_id": null,
  "dataset_hash": null
}
```

### 3. Error / Failure Event
```json
{
  "ts_utc": "2026-02-05T14:32:45.789Z",
  "request_id": "req-i9j0k1l2",
  "seed_id": "seed-1234",
  "user_id": "user-789",
  "subject": "inference-service",
  "action": "predict",
  "object": "model/example-llm/v1.2.3",
  "outcome": "error",
  "reason": "Model timeout after 30s; circuit breaker tripped",
  "src_ip": "10.0.1.55",
  "agent_id": "agent-main-002",
  "dataset_hash": null
}
```

---

## Export Guidance for Audits

### Retention Periods by Framework

| Framework | Minimum Retention | Notes |
|-----------|-------------------|-------|
| EU AI Act (Art. 12) | "Appropriate in light of intended purpose" (Art. 12(2)); recommend system lifetime + 6 months | Logs must cover entire operational lifetime; no statutory minimum specified |
| FedRAMP (AU-11) | 1 year online, 3 years total | Per NIST 800-53r5 AU-11; agency may require longer |
| SOC 2 (CC7.2) | 1 year minimum | Aligned with audit period; retain for audit + 1 cycle |
| ISO 42001 | Per organizational retention policy | Align with AIMS documentation control requirements |

### Export Format Recommendations

- **Primary format**: JSONL (one JSON object per line) for machine processing
- **Archive format**: Compressed JSONL (`.log.jsonl.gz`) for long-term storage
- **Audit delivery**: CSV export with headers for non-technical reviewers
- **Integrity**: Include SHA-256 checksum file alongside each export archive
- **Encryption at rest**: AES-256-GCM for stored log archives (FedRAMP SC-28)

### Pre-Audit Checklist

- [ ] Verify log coverage spans the full audit period
- [ ] Confirm all required fields are populated (not null) for critical events
- [ ] Generate integrity checksums for exported archives
- [ ] Redact or pseudonymize PII fields if delivering to external auditors
- [ ] Include schema version reference with each export
