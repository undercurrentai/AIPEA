# AIPEA — Adversarial VC Review

> **Prepared for:** Prospective Venture Capital Investor
> **Subject:** AIPEA (AI Prompt Engineer Agent), `aipea` v1.6.x on PyPI
> **Repository:** `undercurrentai/AIPEA`
> **Review date:** 2026-04-24
> **Posture:** Adversarial. Defending the capital-allocator's interests, not the seller's narrative.
> **Reviewer role:** Outside technical diligence (no engagement bias)

---

## 1. Executive Summary

**Investment recommendation: PASS as a standalone venture.**

AIPEA is a **competently engineered internal tool** that has been polished, packaged, and published to PyPI. It is not, on the evidence in this repository, a venture-scale product. The code is clean, the tests are real, and the maintainer is disciplined — but the intellectual-property surface is thin, the "security" and "compliance" claims are materially softer than the marketing suggests, and there is **no evidence of paying customers outside the owning company**.

If the VC is being pitched "AIPEA as the company," the answer is no. If the VC is evaluating Undercurrent Holdings more broadly and AIPEA is being shown as a quality proxy, then AIPEA demonstrates that the team can ship — but the differentiated value must live in the adjacent closed-source products (Agora IV, AEGIS), which were not available for this review.

| Dimension                 | Grade | One-line rationale                                                                 |
| ------------------------- | :---: | ---------------------------------------------------------------------------------- |
| Engineering quality       | **A–** | Tight scope, strict typing, real tests, active maintenance.                         |
| Test rigor                | **B+** | 75% coverage floor, ~810 tests, but author-written payloads only.                   |
| Security substance        | **B–** | One genuinely clever subsystem (homoglyphs, ReDoS); rest is static regex.           |
| Compliance claims         | **D**  | HIPAA/TACTICAL are configuration flags, not enforcement. FedRAMP was theater.       |
| Product differentiation   | **D**  | Rebuildable by a competent engineer in 3–4 days.                                    |
| Market traction           | **F**  | Zero evidence of external paying users. Consumers are internal sister products.     |
| Honesty of documentation  | **A–** | SECURITY.md and ADRs are refreshingly frank; marketing elsewhere is looser.         |
| **Overall**               | **C**  | Good library, bad standalone investment.                                            |

---

## 2. What AIPEA Actually Is (Stripped of Marketing)

AIPEA is a **Python preprocessing library** that sits in front of an LLM call. Given a user prompt, it:

1. Runs regex checks for prompt-injection strings, PII, and (optionally) PHI / classified markers.
2. Classifies the query into one of ~7 categories using hardcoded regex patterns.
3. Optionally fetches web context via HTTP calls to Exa or Firecrawl.
4. Optionally pulls from a local SQLite + FTS5 "knowledge base" seeded with ~20 Q&A entries.
5. Optionally shells out to a local Ollama model for offline enhancement.
6. Formats the assembled context for the target model family (XML for Claude, Markdown for GPT, etc.).
7. Returns the enhanced prompt plus metadata.

That is the complete product. There is **no ML model**, no learned classifier, no embeddings, no vector DB, no agentic reasoning loop. The "adaptive learning" module (`learning.py`) is a SQLite table that keeps a running average of user feedback per `(QueryType, strategy)` tuple.

### 2.1 Physical metrics (verified)

- Source: **10,662 LOC** across 16 files (CLAUDE.md claim of ~10,695 is accurate within rounding).
- Tests: **18,291 LOC**, ~810 test methods. Test-to-source ratio **1.7×**.
- Runtime dependencies: **`httpx` only**. Optional CLI adds `typer`/`rich`.
- Python support: 3.11 + 3.12 (CI matrix). mypy strict. Ruff configured.
- Repository: **67 commits**, effectively single-author (ThermoclineLeviathan). Active — most recent commit 2026-04-24.

### 2.2 Claimed consumers

- **Agora IV** — internal Undercurrent product. AIPEA was extracted *from* Agora IV, so internal usage is real but not arm's-length validation.
- **AEGIS** — internal Undercurrent product. Integration pattern documented in `SPECIFICATION.md §5.3`; not independently auditable.
- **External** — none visible. No GitHub dependents. No public PyPI download counter surfaced. No case studies. No customer logos.

---

## 3. Moat Analysis — The Rebuild Test

The central VC question: **how long would it take a competent engineer to rebuild this?**

| Component                      | LOC    | Rebuild |
| ------------------------------ | -----: | :-----: |
| Security scanner (`security.py`) | 938   | ~2 days |
| Query analyzer (`analyzer.py`)   | 843   | ~1 day  |
| Search orchestration (`search.py`)| 1,071 | ~1 day  |
| Knowledge base (`knowledge.py`)  | 711   | ~1 day  |
| Prompt engine (`engine.py`)      | 1,685 | ~1 day  |
| Enhancer facade (`enhancer.py`)  | 1,500+| ~1 day  |
| Adaptive learning (`learning.py`)| ~500  | ~0.5 day |
| **Total greenfield rebuild**     | ~10.7K | **~4 days for 2 engineers** |

The only genuinely non-obvious engineering is in `security.py`: Unicode NFKC + confusables map (35 entries, lines 48–100), invisible-character stripping with spaced-form rescan (lines 635–643), and a seven-layer ReDoS safety check on regex patterns (lines 445–517). **That's the IP.** It is perhaps 400 lines of interesting code. It is not patentable and not secret; a good engineer could read a few OWASP and homoglyph-attack papers and reproduce it in a sprint.

**Verdict:** No durable moat. The moat is operational hygiene and documentation, not algorithmic advantage.

---

## 4. The "Security-First" Narrative vs. the Code

AIPEA is marketed as a security-first prompt preprocessor suitable for regulated environments. This is where the gap between narrative and reality is widest.

### 4.1 Prompt-injection detection

What's there: **eleven hardcoded regex patterns** (`security.py:367–404`) covering `ignore.*previous.*instructions`, role-tag spoofing, SQL keywords (`DROP TABLE`, `UNION SELECT` — largely irrelevant in a prompt-injection context), and template-injection braces.

- **Real strength:** Unicode normalization and confusables mapping *before* pattern match means naive homoglyph bypasses fail. That is better than many commercial competitors.
- **Real weakness:** Signature-based detection. One paraphrase ("disregard prior directives from developers") defeats it. There is no published jailbreak-corpus testing, no fuzzing, no red-team history. Every test in `test_security.py` uses author-written payloads. An adversary reading this now-public code bypasses the ruleset in an afternoon.

### 4.2 PII / PHI scanning

- **PII:** 6 regex categories — SSN, credit card, generic API key, `sk-`-prefixed keys, bearer token, password strings. That is all.
- **PHI (HIPAA mode only):** 3 categories — MRN, DOB, patient-name. **No diagnosis codes, no medication names, no addresses, no phone numbers, no ICD-10.** A clinical query containing "Metformin 500mg BID, patient in Seattle" passes undetected.

Calling this a PHI scanner in healthcare marketing is, charitably, aspirational.

### 4.3 Compliance modes — the core honesty problem

The product exposes three compliance modes: `GENERAL`, `HIPAA`, `TACTICAL` (plus deprecated `FEDRAMP`).

**HIPAA mode** (`security.py:734–744`) does exactly three things:
1. Turns on the 3 PHI regexes.
2. Sets a model allowlist via **substring match** (e.g. `"claude-opus-4-6"` in model name).
3. Sets a boolean `phi_redaction_enabled = True` that **no code consumes**. Nothing in AIPEA redacts, blocks, or rewrites PHI. It emits a flag and lets the caller decide.

There is no BAA. No audit trail persistence. No encryption enforcement. No access controls. The library says so in `SECURITY.md`: *"No BAA or regulatory certification. Undercurrent Holdings does not execute Business Associate Agreements for AIPEA, is not SOC 2 / HIPAA / FedRAMP certified as a vendor."* That disclosure is honest — but it contradicts the framing of "HIPAA mode" as a feature elsewhere.

**TACTICAL mode** (`security.py:746–753`) restricts the allowed model to `llama-3.3-70b` (again by substring — `llama-3.3-70b-instruct-tuned-v4` would also pass) and sets `force_offline=True`. The "offline" flag is advisory metadata for the integrator. **AIPEA itself does not block network egress, does not validate air-gap status, and does not attest to any classified-environment property.**

**FEDRAMP** was marketed until ADR-002 (2026-04-11) formally deprecated it as "a config-only stub with no behavioral enforcement." Crediting the team for the retraction, this is evidence of a prior period in which regulatory claims were made that the code did not support. That pattern — ship the label, defer the enforcement — is exactly the thing a VC should interrogate before taking the remaining compliance claims at face value.

### 4.4 Independent audit

**None exists.** The `docs/claude/audits/` directory contains only self-reviews (including an adversarial self-review, which is useful but is not third-party attestation). The "second-reviewer gate" on security changes is two AI systems (GPT 5.4 Pro + Claude) plus Codex — not independent human auditors. There is no SOC 2, no penetration test, no CVE disclosure history, no bug-bounty program.

For a product positioning itself near healthcare and defense, the absence of external audit is disqualifying for enterprise sale and is a meaningful diligence gap for investors.

---

## 5. Engineering Quality — The Legitimate Strengths

Balanced against the above, the engineering is genuinely good.

- **Scope discipline.** One runtime dependency (`httpx`). Clear module boundaries (`security`, `knowledge`, `search`, `config` import nothing from `aipea.*`).
- **Type safety.** `mypy --strict` is passing across the source tree. Public API is fully annotated.
- **Test realism.** Tests exercise behavior, not lines. Parameterized edge cases (e.g. `TestWave19PatientNameIgnorecaseFalsePositive`, `TestUnicodeHomoglyphBypass`) directly target regressions tied to numbered issues. 75% coverage floor is enforced in CI.
- **Graceful degradation.** Search provider down → empty results. Ollama missing → template fallback. KB uninitialised → empty context. No hidden exceptions from dependency failure.
- **Release hygiene.** Conventional commits, Keep-a-Changelog, ADRs for every meaningful architectural decision, CI gates for lint + type + test on both Python versions, trusted-publisher PyPI release via GitHub Actions.
- **Bug-response speed.** The "Wave" cadence in `CHANGELOG.md` shows 40+ real bugs caught and fixed in a few months, including security-relevant ones (ReDoS in #107, zero-width bypass in #108, HIPAA false-positive in #95).

This is what a healthy small codebase looks like. It is not what a venture-scale platform looks like.

---

## 6. Red Flags & Diligence Questions

The following are items the VC should press on before writing a check.

1. **Who pays for AIPEA today?** Not an internal Undercurrent team — an arm's-length customer. If the answer is zero, the valuation must be justified purely on future potential, which is weak given (3) below.
2. **What does "HIPAA mode" promise in the sales conversation?** Get the exact written claim and compare it to `security.py:734–744`. If sales is implying enforcement and the code performs detection, there is latent regulatory and reputational liability.
3. **What is the durable technical advantage over LangChain / LlamaIndex / Guardrails-AI / NeMo-Guardrails / AWS Bedrock Guardrails?** Each of these is free or bundled and ships more sophisticated input-filtering. AIPEA's answer cannot be "minimal dependencies" — that is a taste preference, not a moat.
4. **Why no external security audit?** For a product sold as security-first, the absence of SOC 2, external pentest, and published jailbreak-corpus evaluation is unusual.
5. **How much of AIPEA's reason-to-exist is captured by the upstream Agora IV / AEGIS products?** If 80% of the value lives in the closed-source sister products, then AIPEA is a byproduct, not the business. The VC is then actually investing in products that weren't presented for review.
6. **Bus factor.** `git shortlog -sn` shows effectively a single contributor. What happens to velocity and trust if that contributor leaves?
7. **The FedRAMP retraction.** Ask the founder directly: what other compliance claims in current marketing are not backed by enforcement in code? The honest ones admit this quickly. The unhealthy ones get defensive.
8. **Metric anchoring in the repo's own docs.** CLAUDE.md is meticulous about anchoring metrics with commit/date. That rigor is admirable but also implies the team knows metrics drift. Ask to see today's coverage, test count, and bug-catch rate rather than documented numbers.

---

## 7. What Would Change the Thesis

AIPEA becomes interesting to a VC only if **at least two** of the following are true:

- **External paying customers.** Logos, references, MRR. Not "we use it internally."
- **An ML-based detection layer.** Replace the regex patterns with a fine-tuned injection classifier or embedding-based anomaly detector. That creates real adversarial-robustness and is the kind of moat that compounds with usage data.
- **Actual compliance certification.** SOC 2 Type II at minimum; real BAA capability; independent pentest with published findings. Not "HIPAA mode" as a config flag.
- **Cross-user learning.** Today, `learning.py` is per-installation. If anonymized feedback from many deployments improved the shared model, data network effects start to exist.
- **Distribution surface.** Native integrations with Bedrock, SageMaker, Vertex AI, HuggingFace Inference — not just Exa/Firecrawl/Ollama.

Without two of those, the company is a consultancy attached to a PyPI package.

---

## 8. Recommendation

**Do not invest in AIPEA as a standalone.** The code is honest and the maintainer is competent, but there is no defensible moat, no customer validation, and the compliance narrative is softer than the marketing.

**If evaluating Undercurrent Holdings more broadly**, treat AIPEA as a positive **signal about engineering culture** (real tests, honest ADRs, frank SECURITY.md) and then demand to see the actual revenue-bearing products — Agora IV and AEGIS — under the same diligence lens applied here. Those are the company; AIPEA is a support library.

**If pressured to invest anyway**, require as closing conditions:
1. Independent pentest and SOC 2 readiness assessment (buyer-paid, seller-selected from a shortlist of three).
2. Restatement of compliance claims in all marketing to match what the code enforces.
3. A named design partner in either healthcare or defense with a signed LOI before funds release.
4. Bus-factor mitigation: contractual commitment of the single contributor plus a second engineer funded from proceeds.

Absent those, the risk is not that AIPEA breaks — it almost certainly will not break, because the code is sober — it is that AIPEA **does not grow into anything**, and the capital funds a maintenance salary rather than a venture outcome.

---

## 9. Key Evidence Cited

- `src/aipea/security.py:48-100` — Unicode confusables map (genuine IP).
- `src/aipea/security.py:240-290, 367-404` — Hardcoded injection regex set.
- `src/aipea/security.py:327-351` — PII/PHI pattern inventory.
- `src/aipea/security.py:445-517` — ReDoS safety validator (genuine IP).
- `src/aipea/security.py:734-744` — HIPAA mode implementation (detection + allowlist only).
- `src/aipea/security.py:746-753` — TACTICAL mode implementation (advisory flag only).
- `src/aipea/security.py:755-783` — FEDRAMP stub (honestly deprecated).
- `src/aipea/analyzer.py:70-150` — Regex-based query classification.
- `src/aipea/enhancer.py:430-674` — Orchestration facade.
- `src/aipea/learning.py` — Local-only per-tuple running average.
- `SECURITY.md` — Honest disclosure of non-certification.
- `docs/adr/ADR-002-fedramp-removal.md` — FedRAMP retraction.
- `docs/claude/audits/investor-review-adversarial-2026-04-11.md` — Prior self-authored adversarial review (converges on similar findings).
- `CHANGELOG.md` Waves 14–20 — Bug-catch pattern: edge-case hardening, not fundamental redesigns.

---

*Prepared adversarially. Findings reflect evidence present in the repository as of 2026-04-24.*
