# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in AIPEA, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, use [GitHub Security Advisories](https://github.com/undercurrentai/AIPEA/security/advisories/new) to report vulnerabilities privately. Alternatively, email **<security@undercurrentholdings.com>**.

### What to Include

- Description of the vulnerability
- Affected version(s) and module(s) (e.g., `security.py`, `knowledge.py`, `config.py`)
- Steps to reproduce — ideally a minimal Python snippet
- Potential impact (e.g., injection bypass, PHI exposure, ReDoS, data loss)
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 5 business days
- **Fix Timeline** (from confirmed triage):
  - Critical (compliance bypass, remote code execution, data exposure): 7 days
  - High (ReDoS / DoS, injection bypass, privilege escalation): 14 days
  - Medium (information disclosure, logic errors in security paths): 30 days
  - Low (hardening, defense-in-depth): next minor release

Patches are shipped via PyPI under a new patch version (e.g., `1.3.3`). Users are notified via the GitHub Security Advisory linked from the release notes.

## Scope and Honest Framing

AIPEA is a **prompt-preprocessing library**. Its security layer is designed for *input inspection*, not enforcement of regulatory regimes.

### What AIPEA's security layer does

- **Injection detection**: pattern-based detection of prompt-injection attempts (system-role hijacking, instruction-override phrases, markdown-template injection) with NFKC + homoglyph normalization (`security.py:INJECTION_PATTERNS`).
- **PII scanning**: regex-based detection of email addresses, SSNs, phone numbers, credit-card numbers.
- **PHI scanning (HIPAA mode)**: regex-based detection of MRNs, patient identifiers, and common PHI patterns.
- **Classified-marker scanning (TACTICAL mode)**: detection of U.S. classification markers (CONFIDENTIAL / SECRET / TOP SECRET and compartment markings).
- **Compliance-mode model allowlisting**: the `ComplianceMode` enum restricts which LLM identifiers are permitted per regime.
- **ReDoS-safe regex validation**: user-supplied patterns are validated against `_is_regex_safe()` before compilation (`security.py`).
- **Graceful degradation**: search failures return empty results; scan failures are logged and re-raised at the caller boundary — AIPEA never silently swallows a security finding.

### What AIPEA's security layer does NOT do

- **No redaction or blocking**: on detection, AIPEA emits a `SecurityScanResult` with `pii_detected` / `phi_detected` / `classified_marker` flags and (by default) logs a warning. It does **not** automatically redact content or abort the enhancement pipeline. Integrators are responsible for the enforcement decision.
- **No audit-trail storage**: AIPEA does not persist scan results or decision logs. If your regulatory regime requires tamper-evident audit logs, the consumer application is responsible.
- **No encryption at rest or in transit**: AIPEA holds no secrets and stores no customer data by default. The offline knowledge base (`knowledge.py`) is a local SQLite file with no built-in encryption — if it contains sensitive data, encrypt the filesystem.
- **No BAA or regulatory certification**: Undercurrent Holdings does not execute Business Associate Agreements for AIPEA, is not SOC 2 / HIPAA / FedRAMP certified as a vendor, and makes no representations about regulatory compliance on the integrator's behalf.
- **HIPAA / TACTICAL modes are detection + allowlist only**. They are not a substitute for a compliant data pipeline, access controls, encryption, or audit logging. See `src/aipea/security.py` and the README "Compliance Modes" section for the exact behavior of each mode.
- **`ComplianceMode.FEDRAMP` is deprecated (v1.3.4) and scheduled for removal in v2.0.0.** AIPEA does not implement FedRAMP controls. The enum value was a config-only stub with no behavioral enforcement and is retained only as a deprecated alias for API back-compat through the v1.x line. Constructing a `ComplianceHandler` with `FEDRAMP` now emits a `DeprecationWarning`. Do not ship AIPEA's FedRAMP mode to a FedRAMP environment; migrate to `ComplianceMode.GENERAL` and implement FedRAMP controls in your own application layer. Decision rationale: [`docs/adr/ADR-002-fedramp-removal.md`](docs/adr/ADR-002-fedramp-removal.md).

### Taint-aware feedback averaging (ADR-004)

Feedback recorded by `AdaptiveLearningEngine` is taint-aware. Feedback associated with queries that fired compliance-relevant scanner flags (PHI/PII/classified/injection) is retained in the audit log (`learning_events` table with `taint_flags` and `excluded_from_averaging` columns) but excluded from strategy-performance averaging by default. This closes the stateful feedback-poisoning vector identified by OWASP LLM Top 10 2026 (LLM03) and satisfies audit trail completeness requirements from NISTIR 8596. Integrators may opt into inclusion via `LearningPolicy(exclude_tainted_from_averaging=False)`.

## Security Measures in Development

AIPEA applies defense-in-depth to its own codebase:

### Code Quality

- **Static analysis**: `ruff` (with Bandit-aligned `S` rules), `mypy --strict`, `pytest` with 75% coverage floor (current: 92%+).
- **CI gates**: lint, type check, and test matrix (Python 3.11 + 3.12) on every PR; blocks merge on failure.
- **Dependency review**: Dependabot weekly grouped updates; `dependency-review` action on PR; `pip-audit` + `safety` in the nightly compliance workflow.
- **Secret scanning**: Gitleaks in pre-commit and CI; no secrets may be committed.
- **Supply chain**: all GitHub Actions are **SHA-pinned**, not tag-pinned. PyPI publishing uses **OIDC Trusted Publisher** — no long-lived API tokens in repo secrets.
- **Second-reviewer gate** (from v1.3.3): PRs touching `src/aipea/security.py`, `src/aipea/__init__.py`, `pyproject.toml`, or `.github/workflows/**` pass through a dual-AI review gate (GPT 5.4 Pro + Codex CLI) as required CI status checks before merge, with `@joshuakirby` as the accountable human reviewer.

### Dependency Discipline

Core modules (`security`, `knowledge`, `config`, `_types`, `quality`) are **stdlib-only**. `search` uses stdlib + `httpx`. The optional CLI adds `typer` and `rich`. This minimal surface is maintained deliberately — new dependencies require explicit ASK-first approval per `CLAUDE.md §3.3`.

### Known Limitations

AIPEA publishes its own known issues honestly. See:

- [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) — bug-hunt wave history with fix/deferral/reclassification tracking
- [`CHANGELOG.md`](CHANGELOG.md) — per-release security-relevant fixes flagged inline
- [`docs/claude/audits/`](docs/claude/audits/) — internal audit packets, including adversarial investor-perspective reviews

## Supported Versions

Security fixes are backported to the current minor release line only.

| Version | Supported          |
|---------|--------------------|
| 1.6.x   | Yes                |
| 1.5.x   | Security fixes only |
| 1.4.x   | Security fixes only |
| < 1.4   | No — upgrade to 1.6.x |

Users of any pre-`1.4.0` version should upgrade — `1.6.0` closes a feedback-poisoning vector (ADR-004), and `1.3.3` closed a HIPAA-mode compliance leak (#96) and ReDoS (#107). See `CHANGELOG.md` for details.

## Credits

We credit reporters (with permission) in the release notes of the fix. If you prefer anonymity, say so in your report.

---

*AIPEA Security Policy | Owner: @joshuakirby | Effective: v1.6.2 (2026-04-24; policy text unchanged since v1.6.1 — date bumped to reflect v1.6.2 release metadata refresh)*
