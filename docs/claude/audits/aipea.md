# AIPEA CLAUDE.md Audit Packet
> Audit Date: 2026-02-14 | Auditor: Claude Code (Opus 4.6) | Protocol: v4.0

```yaml
audit_id: AIPEA-2026-02-14-v3
target: Projects/AIPEA/CLAUDE.md
previous_version: 2.0.0
new_version: 3.0.0
compliance_tier: STANDARD
tier: 2
token_budget: 8000
protocol: v4.0
parent: ../../CLAUDE.md
```

---

## 1. Audit Summary

| Metric | Value |
|--------|-------|
| Previous version | 2.0.0 (~406 lines, ~14KB, protocol v3.2) |
| New version | 3.0.0 (~417 lines, ~14KB, protocol v4.0) |
| Tier classification | Tier 2 (Standard): ~7K LOC, 2 contributors, internal consumers, STANDARD compliance |
| Token budget | 8,000 (Tier 2 ceiling) |
| Parent inheritance | `../../CLAUDE.md` (Undercurrent Holdings root v3.2.1) |
| Sections added | 3 (Quick Reference, Hierarchy Context, PyPI Release playbook) |
| Sections consolidated | 2 (Quality Gates merged, Ask-First triggers consolidated) |
| Sections deduplicated | 2 (Secret handling, Hard stops — now reference parent) |
| Sections removed | 1 (Unimplemented env vars table) |
| New artifacts | 3 (publish.yml, 3 slash commands) |
| Bloat score | <12% non-directive content |

### Key Changes

1. **v4.0 Protocol Conformance**: Added tier classification, hierarchy declaration, token budget, protocol version
2. **Hierarchy Awareness**: Section 1.4 declares parent inheritance; Sections 2.3 and 7.1 reference parent for shared policies
3. **Deduplication**: Removed duplicate secret handling policy and hard stops that are inherited from root
4. **Quick Reference**: New Section 0 provides instant-context table
5. **PyPI Publish Workflow**: New `.github/workflows/publish.yml` with Trusted Publisher OIDC + quality gate
6. **Playbook Addition**: Section 6.5 documents full PyPI release process
7. **Quality Gates Merged**: Sections 8.1 and 8.2 merged into single unified table with Stage column
8. **Environment Variables Cleaned**: Removed 4 unimplemented env var rows (spec-level, non-actionable)
9. **Research Tools Upgraded**: YAML code blocks converted to actionable tables with concrete queries
10. **Slash Commands**: 3 new commands (test-module, audit-deps, verify-spec)

---

## 2. RCP (Research, Compliance, Provenance)

### 2.1 Research Findings

| Source | Query | Finding |
|--------|-------|---------|
| pyproject.toml | Build system | hatchling build backend — supports `hatch build` for PyPI |
| pyproject.toml | Tool config | ruff line-length=100, py312 target, S-rules for bandit, mypy strict |
| Makefile | Build targets | 13 targets: install, fmt, lint, type, test, sec, all, ci, mut, sbom, score, deps, perf |
| pytest | Test suite | 498 passed, 15 skipped, 90.92% coverage (updated 2026-02-18) |
| CI workflow | Gate config | 3 jobs: lint, typecheck, test (matrix: py3.11 + py3.12); also scaffold-checks, compliance-nightly, compliance-evidence-scheduler workflows |
| __init__.py | Public API | 32 exports in `__all__`, version = "1.0.0" |
| pyproject.toml | License | MIT license, >=3.11 required |
| Exa search | PyPI publishing 2025/2026 | Trusted Publishers (OIDC) is standard; `pypa/gh-action-pypi-publish@release/v1` |
| Context7 | hatch build docs | `hatch build` creates sdist + wheel; `hatch version` for version management |
| wc -l src/aipea/*.py | Source LOC | 7,332 lines across all source modules (updated 2026-02-18) |

### 2.2 Discrepancies Found

| Issue | v2.0.0 State | Actual | Resolution in v3.0.0 |
|-------|-------------|--------|----------------------|
| Unimplemented env vars | Listed in Section 5.3 | Not read by any source code | Removed; only 3 implemented vars retained |
| Secret policy duplication | Full policy duplicated from parent | Parent has identical policy | Reference parent + AIPEA-specific additions only |
| Hard stops duplication | "Commit secrets", "Force push" listed | Same as parent hard stops | Reference parent + AIPEA-specific stops only |
| PyPI publishing | Listed as out-of-scope (manual) | No workflow exists | Created publish.yml + release playbook |
| Quality gates split | Separate tables for Local vs CI | Same gates run in both contexts | Merged into unified table with Stage column |

### 2.3 Compliance Detection

| Tier | Detected | Evidence |
|------|----------|----------|
| Standard | YES | Default baseline, scaffold-adopted governance artifacts |
| AI-Governed | PARTIAL | ai/ directory added via scaffold adoption (2026-02-14); model-card.yaml, risk-register.yaml, data-card.yaml present |
| Security-First | PARTIAL | Ruff S-rules in CI; Trivy + safety in compliance-nightly workflow |
| Regulated | PARTIAL | Compliance procedures in docs/compliance/ via scaffold adoption |
| Agentic Safety | NO | No multi-agent patterns |

**Result**: STANDARD tier (Tier 2) confirmed. No conditional addenda required.

### 2.4 Hierarchy Validation

| Check | Status | Evidence |
|-------|--------|----------|
| Parent exists | PASS | `../../CLAUDE.md` exists (v3.2.1) |
| `inherits_from` declared | PASS | Header YAML block |
| Inherited policies listed | PASS | Section 1.4 |
| No parent duplication | PASS | Secrets and hard stops reference parent |
| AIPEA-specific overrides documented | PASS | Section 1.4 states "None" |

---

## 3. Section-by-Section Classification

| Section | Classification | Action | Rationale |
|---------|---------------|--------|-----------|
| Version header | Directive | UPGRADED | Added tier, protocol, token_budget, inherits_from |
| 0. Quick Reference | Directive | ADDED | Instant-context table (v4.0 requirement) |
| 1. Purpose & Scope | Directive | EXPANDED | Added 1.3 Out-of-Scope, 1.4 Hierarchy Context |
| 2. Agent Contract | Directive | CONSOLIDATED | Ask-first 11→8 rows, hard stops reference parent |
| 3. Standards | Directive | KEPT | Accurate per pyproject.toml |
| 4. Architecture | Knowledge | KEPT | Concise dependency graph, <10% of doc |
| 5. Tooling & Commands | Directive | TRIMMED | Removed unimplemented env vars, converted YAML→tables |
| 6. Playbooks | Directive | EXPANDED | YAML→numbered lists, added 6.5 PyPI Release |
| 7. Security | Directive | DEDUPLICATED | Parent reference for secrets policy |
| 8. Quality Gates | Directive | MERGED | Two tables → one unified table with Stage column |
| 9. Ask-First Matrix | Directive | UPDATED | Added publish workflow + version bump triggers |
| 10. Context Management | Directive | EXPANDED | Added token budget awareness, subagent table |
| 11. Change Management | Directive | EXPANDED | Added version semantics, early audit triggers |
| 12. References | Index | UPDATED | Added parent CLAUDE.md link |

---

## 4. Self-Red-Team

### 4.1 Attack Vectors Considered

| Vector | Risk | Mitigation in CLAUDE.md |
|--------|------|------------------------|
| Agent modifies public API without review | Medium | Ask-First trigger on `__init__.py` changes |
| GPL dependency added to MIT project | High | Hard Stop on GPL/LGPL dependencies |
| Secrets committed to repo | Critical | Hard Stop + parent policy reference |
| Agent breaks CI by changing ruff/mypy config | Medium | Ask-First on pyproject.toml tool config changes |
| Agent over-engineers library with new deps | Medium | Minimal-deps design principle + zero-deps hard stop |
| Agent modifies security module without audit | High | Ask-First trigger with security audit requirement |
| Agent changes compliance mode behavior | High | Ask-First trigger with regulatory implications note |
| Unauthorized PyPI publish | Medium | Workflow requires GitHub Release (manual gate) + `release` environment |
| Agent bypasses quality gate for publish | Low | `needs: quality-gate` enforced in workflow; NEVER bypass |

### 4.2 Coverage Gaps

| Gap | Severity | Addressed? |
|-----|----------|------------|
| No guidance on when to use subagents | Low | Yes (Section 10) |
| No playbook for dependency updates | Medium | Yes (Section 6.4) |
| No PyPI release process documented | Medium | Yes (Section 6.5 + publish.yml) |
| No version semantics defined | Low | Yes (Section 11) |
| No early audit triggers | Low | Yes (Section 11) |
| No hierarchy awareness | Medium | Yes (Section 1.4) |

---

## 5. Self-Validation Checklist

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Tier declared in header | PASS | `tier: 2` in YAML block |
| 2 | Hierarchy declared | PASS | `inherits_from: ../../CLAUDE.md` |
| 3 | Token budget declared | PASS | `token_budget: 8000` |
| 4 | Ask-first triggers defined | PASS | Section 2.2 (8 triggers) |
| 5 | Hard stops defined | PASS | Section 2.3 (4 AIPEA-specific + parent reference) |
| 6 | Quality gates defined | PASS | Section 8 (7 gates with stage/bypass columns) |
| 7 | Playbooks defined | PASS | Section 6 (5 playbooks) |
| 8 | Research tools documented | PASS | Section 5.4 (6 triggers with tools + queries) |
| 9 | Architecture documented | PASS | Section 4 (dependency graph + 4 principles) |
| 10 | Bloat under 15% | PASS | <12% non-directive content |
| 11 | No stale data | PASS | All metrics verified against source files |
| 12 | Parent not duplicated | PASS | Secrets + hard stops reference parent |

---

## 6. Composable Compliance Assessment

**AIPEA Tier**: STANDARD (Tier 2)

| Compliance Module | Required? | Reason |
|-------------------|-----------|--------|
| AI Governance (model cards, risk registers) | NO | AIPEA is a preprocessing library, not an AI model |
| Security-First (SAST/DAST workflows) | NO | Ruff S-rules provide baseline; no web-facing surface |
| Regulated (audit trails, approval gates) | NO | No regulatory requirements for library |
| Agentic Safety (multi-agent protocols) | NO | Single-library, not multi-agent |

**Note**: AIPEA *implements* compliance modes (HIPAA, TACTICAL, FEDRAMP) for its consumers, but the compliance artifacts themselves are the consumer's responsibility, not AIPEA's. AIPEA enforces constraints; consumers prove compliance.

---

## 7. Research Log

| Timestamp | Tool | Query | Finding | Applied To |
|-----------|------|-------|---------|------------|
| 2026-02-14 | pyproject.toml read | Build backend | hatchling — confirms `hatch build` for PyPI | publish.yml |
| 2026-02-14 | CI workflow read | Action versions | checkout@v4, setup-python@v5 | publish.yml consistency |
| 2026-02-14 | Exa (plan phase) | "Python hatchling PyPI publish trusted publisher 2025 2026" | Trusted Publishers OIDC is standard; no API tokens needed | publish.yml + Section 6.5 |
| 2026-02-14 | Context7 (plan phase) | hatch build docs | `hatch build` creates sdist + wheel in `dist/` | publish.yml build step |
| 2026-02-14 | wc -l | Source LOC count | 6,088 lines in src/aipea/*.py (initial); 6,249 on 2026-02-15; 6,289 on 2026-02-16 | Section 0 Quick Reference |
| 2026-02-14 | __init__.py read | Public API surface | 30 exports in `__all__` | Section 0 Quick Reference |
| 2026-02-14 | Root CLAUDE.md read | Parent policies | Secret handling, evidence requirements, reality-first | Section 1.4 inheritance |

---

## 8. Signal

- **Upgrade confidence**: HIGH. All data sourced from actual project files and verified research.
- **Risk of stale data**: LOW. AIPEA was extracted on 2026-02-14. All files are current.
- **Downstream impact**: LOW. CLAUDE.md is agent guidance only. New publish.yml only triggers on manual release creation. Slash commands are additive.
- **Token efficiency**: Net neutral (~14KB → ~14KB). New content (Quick Reference, hierarchy, PyPI) offset by deduplication (secrets, hard stops, env vars).

---

## 9. Post-Audit Amendments

| Date | Change | Detail |
|------|--------|--------|
| 2026-02-15 | Metrics update | Bug hunt waves 1-4: 357→375 tests, 90.43%→91.62% coverage, 6,249→6,279 LOC |
| 2026-02-16 | Metrics update | Bug hunt wave 5: 375→378 tests, 91.62%→91.59% coverage, 6,279→6,289 LOC |
| 2026-02-16 | CLAUDE.md date fields | Updated `Updated:` to 2026-02-16, `last_audit:` to 2026-02-16 |
| 2026-02-16 | KNOWN_ISSUES.md | 23 items across waves 1-5 (was 0 at audit time) |
| 2026-02-16 | Metrics update | Wave 6 + ultrathink: 378→395 tests, 91.59%→92.44% coverage, 6,289→6,291 LOC |
| 2026-02-16 | KNOWN_ISSUES.md | Restructured: 9 FIXED, 6 INTENTIONAL, 8 DEFERRED |
| 2026-02-16 | Metrics update | ReDoS char-class fix: 395→401 tests, 92.44%→92.46% coverage, 6,291→6,299 LOC |
| 2026-02-16 | KNOWN_ISSUES.md | Added #24-#27 (FIXED), updated #6/#19 line refs: 13 FIXED, 6 INTENTIONAL, 8 DEFERRED |
| 2026-02-16 | Metrics update | Wave 7 bug hunt: 401→404 tests, 92.46%→92.58% coverage, 6,299→6,311 LOC |
| 2026-02-16 | KNOWN_ISSUES.md | Added #28-#30 (FIXED), #31 (DEFERRED): 16 FIXED, 6 INTENTIONAL, 9 DEFERRED |
| 2026-02-16 | Metrics update | Deferred issue resolution (9 fixes + 2 QG): 404→413 tests, 92.58%→92.71% coverage, 6,311→6,404 LOC |
| 2026-02-16 | KNOWN_ISSUES.md | All 9 DEFERRED + #31 resolved: 25 FIXED, 6 INTENTIONAL, 0 DEFERRED |
| 2026-02-16 | Metrics update | Wave 8 bug hunt: 413→417 tests, 92.71%→92.72% coverage, 6,404→6,415 LOC |
| 2026-02-16 | KNOWN_ISSUES.md | Added #32-#33 (FIXED), 1 false positive documented: 27 FIXED, 6 INTENTIONAL, 0 DEFERRED |
| 2026-02-17 | Metrics update | Wave 9 bug hunt: 417→420 tests, 92.72%→92.75% coverage, 6,415→6,426 LOC |
| 2026-02-17 | KNOWN_ISSUES.md | Added #34-#35 (FIXED), #36 (DEFERRED), #37 (FIXED via QG): 30 FIXED, 6 INTENTIONAL, 1 DEFERRED |
| 2026-02-17 | CLI/config system | Added config.py, cli.py, __main__.py + tests: 420→488 tests, 92.75%→90.83% coverage, 6,426→7,278 LOC, 30→32 exports |
| 2026-02-17 | Wave 10 bug hunt | 3 fixes (#38-#40), 2 deferred (#41-#42): 488→496 tests, 90.83%→90.91% coverage, 33 FIXED, 6 INTENTIONAL, 3 DEFERRED |
| 2026-02-18 | Quality gate ultrathink | 1 fix (#43 — search.py SearchContext coercion): 496→498 tests, 90.91%→90.92% coverage, 34 FIXED, 6 INTENTIONAL, 3 DEFERRED |

*Audit completed: 2026-02-14 | Auditor: Claude Code (Opus 4.6) | Protocol: v4.0*
*Last amended: 2026-02-18*
