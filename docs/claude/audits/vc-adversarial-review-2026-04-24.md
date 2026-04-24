# AIPEA — Adversarial VC Review

> **Prepared for:** Prospective Venture Capital Investor
> **Subject:** AIPEA (AI Prompt Engineer Agent), `aipea` v1.6.x on PyPI
> **Repository:** `undercurrentai/AIPEA`
> **Review date:** 2026-04-24 (amended to reflect open-core gateway positioning)
> **Posture:** Adversarial. Defending the capital-allocator's interests, not the seller's narrative.
> **Reviewer role:** Outside technical diligence (no engagement bias)

> **Editorial note (maintainer, 2026-04-24):** Preserved verbatim per the
> AIPEA "adversarial reviews retained in full" convention (cf.
> [`investor-review-adversarial-2026-04-11.md`](investor-review-adversarial-2026-04-11.md)).
> Two metric claims in §2.1 are stale against live repo state at merge time
> and are flagged here rather than edited in the body:
>
> - §2.1 says "**67 commits**, effectively single-author";
>   `git log --oneline | wc -l` on `main` at 2026-04-24 returns **238**.
> - §2.1 says "**18,291 LOC tests, ~810 test methods**";
>   `pytest --collect-only -q` on `main` at 2026-04-24 returns **1,282
>   collected tests**; source LOC is **10,662** per
>   `wc -l src/aipea/*.py`.
>
> See [`docs/adopters.md`](../../adopters.md) and
> [`docs/metrics.md`](../../metrics.md) (shipped in v1.6.2) for authoritative
> live numbers. Substantive findings hold regardless of the drift.
>
> The maintainer response to this review is filed in
> [`docs/adr/ADR-005-pr52-vc-adversarial-review-response.md`](../../adr/ADR-005-pr52-vc-adversarial-review-response.md)
> (shipped 2026-04-24 — includes §12 per-diligence-question appendix).

---

## 1. Executive Summary

**Investment recommendation: DO NOT EVALUATE IN ISOLATION.**

AIPEA is an **intentionally open-source Python library** positioned as a top-of-funnel / developer-adoption gateway into the company's commercial products (Agora IV, AEGIS). That positioning changes the relevant questions. When seen that way:

- "No moat in AIPEA" stops being a criticism — frictionless adoption is the *point* of the open-core layer.
- "No direct paying customers for AIPEA" stops being fatal — the relevant KPIs are adoption, community signal, and conversion into the paid products.
- "Compliance modes are detection, not enforcement" becomes defensible *if* clearly marketed that way: AIPEA as the detection substrate, Agora IV / AEGIS as the enforcement layer built on top.

But the reframe cuts both ways:

- The check is being written on **Agora IV and AEGIS**, not on AIPEA. Neither product was available for this review. The diligence is therefore incomplete regardless of how good or bad AIPEA looks.
- The gateway thesis is **currently unproven**. There is no visible evidence in this repository of external adoption, external contributors, or funnel conversion into the paid products. If the funnel isn't running, AIPEA is still an internal tool wearing an open-source license.
- Overclaims in the OSS layer (see §5 on FedRAMP retraction and HIPAA-as-a-flag) become **more** damaging in a gateway model, not less — the OSS project is the brand's public face for the paid products.

AIPEA itself is a competently engineered library. The investment thesis rests almost entirely on artifacts not in this repository.

| Dimension                 | Grade | One-line rationale                                                                 |
| ------------------------- | :---: | ---------------------------------------------------------------------------------- |
| Engineering quality       | **A–** | Tight scope, strict typing, real tests, active maintenance.                         |
| Test rigor                | **B+** | 75% coverage floor, ~810 tests, but author-written payloads only.                   |
| Security substance        | **B–** | One genuinely clever subsystem (homoglyphs, ReDoS); rest is static regex.           |
| Compliance claims         | **C–** | HIPAA/TACTICAL are detection flags; defensible as OSS substrate, not as product.   |
| Product differentiation   |  **–** | Not applicable under open-core thesis (see §3).                                     |
| OSS adoption signal       | **?**  | No external data in repo. Must come from outside the code: downloads, stars, deps. |
| Honesty of documentation  | **A–** | SECURITY.md and ADRs are refreshingly frank; marketing elsewhere is looser.         |
| **Overall**               | **Incomplete** | Depends on Agora IV / AEGIS diligence and on external funnel metrics.       |

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

## 3. Re-Framing: AIPEA as an Open-Core Gateway

The seller has represented AIPEA as **open-source by design** and as a **gateway** into the company's commercial products (Agora IV for multi-model orchestration, AEGIS for governance). That reframes most of what follows.

### 3.1 What the open-core / gateway playbook requires

The companies that have made this model work at venture scale — HashiCorp, Confluent, MongoDB, Elastic, GitLab, dbt Labs — share a specific pattern:

1. **A freely adoptable OSS project** that developers pick up without a sales conversation.
2. **Genuine utility in the free layer** so the project is used in production, not just evaluated.
3. **A clear value step-up** to the paid product — features the OSS layer deliberately does not include (scale, collaboration, compliance certification, managed hosting, governance).
4. **Measurable funnel conversion** from OSS users to paid seats.
5. **A community flywheel** — external contributors, issues, blog posts, third-party integrations.

AIPEA satisfies (1) and (2) in its engineering. (3) is architecturally plausible — the product is structured such that AIPEA performs *detection* and the closed-source products can perform *enforcement and orchestration* on top. (4) and (5) are **not visible in the repository** and must be verified out-of-band.

### 3.2 What flips under this framing

| Original criticism                              | Open-core reframe                                                                                  |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| "Rebuildable in 4 days; no moat."               | Intentional. The OSS surface is meant to be easy to adopt, not easy to monetize.                   |
| "No paying customers for AIPEA."                | Wrong KPI. The relevant KPIs are downloads, dependents, stars, external PRs, and funnel conversion. |
| "Compliance modes are flags, not enforcement."  | Defensible *as a detection substrate* — provided the marketing reflects this.                      |
| "Bus factor of one."                            | Softened but not solved. OSS can recruit maintainers; it has not yet done so here.                  |
| "Consumers are internal."                       | Expected in year one of an open-core strategy. Becomes a red flag only if it persists.              |

### 3.3 What does NOT flip — and arguably gets worse

- **The FedRAMP retraction.** In a gateway model the OSS project *is* the brand's public storefront. Overclaims in the OSS layer poison the funnel into the paid products. ADR-002 did the right thing; the question is what the next retraction will be.
- **HIPAA / TACTICAL overclaim risk.** Same logic. A healthcare or defense prospect who adopts AIPEA expecting enforcement, discovers it is detection-only, and churns — they churn out of the *paid* funnel too.
- **Absence of external audit.** If the OSS project is positioned as adjacent to regulated industries, eventual third-party attestation is table stakes. Not urgent, but on the roadmap.
- **The investment target.** The paid products must still be diligenced directly. AIPEA's quality is a positive *signal* about engineering culture; it is not a substitute for revenue, retention, and margin data on Agora IV / AEGIS.

### 3.4 The diligence pivots

Under the gateway framing, the questions a VC must answer stop being about AIPEA itself and become:

1. **Is the funnel running?** Download trajectory, dependent count, external contributors, inbound leads attributed to AIPEA exposure.
2. **Is it converting?** Share of Agora IV / AEGIS pipeline — and closed revenue — that touched AIPEA upstream.
3. **Is the step-up clear?** Can the seller articulate, crisply, what Agora IV / AEGIS do that AIPEA deliberately does not?
4. **Is the OSS brand trustworthy?** Marketing claims in the OSS layer must be calibrated to the code. Overclaims here cost paid pipeline downstream.
5. **What are Agora IV and AEGIS, actually?** The review below cannot answer this. Neither can any AIPEA-only diligence.

---

## 4. Moat Analysis — The Rebuild Test

*In a non-open-core framing this section would be damning. Under the open-core framing (§3) rebuildability is intentional. It is retained for reference and because it informs how defensible the free layer is against forks or competing OSS libraries.*

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

**Verdict (standalone view):** no durable moat in the OSS layer. **Verdict (open-core view):** expected and correct. In the open-core view, durable moat must live in Agora IV / AEGIS; the fact that it is not visible in AIPEA is neither surprising nor concerning — but it means AIPEA cannot be the thing being evaluated.

---

## 5. The "Security-First" Narrative vs. the Code

AIPEA is marketed as a security-first prompt preprocessor suitable for regulated environments. This is where the gap between narrative and reality is widest — and it matters *more*, not less, under an open-core framing because the OSS layer is the brand's public face for the paid products.

### 5.1 Prompt-injection detection

What's there: **eleven hardcoded regex patterns** (`security.py:367–404`) covering `ignore.*previous.*instructions`, role-tag spoofing, SQL keywords (`DROP TABLE`, `UNION SELECT` — largely irrelevant in a prompt-injection context), and template-injection braces.

- **Real strength:** Unicode normalization and confusables mapping *before* pattern match means naive homoglyph bypasses fail. That is better than many commercial competitors.
- **Real weakness:** Signature-based detection. One paraphrase ("disregard prior directives from developers") defeats it. There is no published jailbreak-corpus testing, no fuzzing, no red-team history. Every test in `test_security.py` uses author-written payloads. An adversary reading this now-public code bypasses the ruleset in an afternoon.

### 5.2 PII / PHI scanning

- **PII:** 6 regex categories — SSN, credit card, generic API key, `sk-`-prefixed keys, bearer token, password strings. That is all.
- **PHI (HIPAA mode only):** 3 categories — MRN, DOB, patient-name. **No diagnosis codes, no medication names, no addresses, no phone numbers, no ICD-10.** A clinical query containing "Metformin 500mg BID, patient in Seattle" passes undetected.

Calling this a PHI scanner in healthcare marketing is, charitably, aspirational.

### 5.3 Compliance modes — the core honesty problem

The product exposes three compliance modes: `GENERAL`, `HIPAA`, `TACTICAL` (plus deprecated `FEDRAMP`).

**HIPAA mode** (`security.py:734–744`) does exactly three things:
1. Turns on the 3 PHI regexes.
2. Sets a model allowlist via **substring match** (e.g. `"claude-opus-4-6"` in model name).
3. Sets a boolean `phi_redaction_enabled = True` that **no code consumes**. Nothing in AIPEA redacts, blocks, or rewrites PHI. It emits a flag and lets the caller decide.

There is no BAA. No audit trail persistence. No encryption enforcement. No access controls. The library says so in `SECURITY.md`: *"No BAA or regulatory certification. Undercurrent Holdings does not execute Business Associate Agreements for AIPEA, is not SOC 2 / HIPAA / FedRAMP certified as a vendor."* That disclosure is honest — but it contradicts the framing of "HIPAA mode" as a feature elsewhere.

**TACTICAL mode** (`security.py:746–753`) restricts the allowed model to `llama-3.3-70b` (again by substring — `llama-3.3-70b-instruct-tuned-v4` would also pass) and sets `force_offline=True`. The "offline" flag is advisory metadata for the integrator. **AIPEA itself does not block network egress, does not validate air-gap status, and does not attest to any classified-environment property.**

**FEDRAMP** was marketed until ADR-002 (2026-04-11) formally deprecated it as "a config-only stub with no behavioral enforcement." Crediting the team for the retraction, this is evidence of a prior period in which regulatory claims were made that the code did not support. That pattern — ship the label, defer the enforcement — is exactly the thing a VC should interrogate before taking the remaining compliance claims at face value.

### 5.4 Independent audit

**None exists.** The `docs/claude/audits/` directory contains only self-reviews (including an adversarial self-review, which is useful but is not third-party attestation). The "second-reviewer gate" on security changes is two AI systems (GPT 5.4 Pro + Claude) plus Codex — not independent human auditors. There is no SOC 2, no penetration test, no CVE disclosure history, no bug-bounty program.

For a product positioning itself near healthcare and defense, the absence of external audit is disqualifying for enterprise sale and is a meaningful diligence gap for investors.

---

## 6. Engineering Quality — The Legitimate Strengths

Balanced against the above, the engineering is genuinely good.

- **Scope discipline.** One runtime dependency (`httpx`). Clear module boundaries (`security`, `knowledge`, `search`, `config` import nothing from `aipea.*`).
- **Type safety.** `mypy --strict` is passing across the source tree. Public API is fully annotated.
- **Test realism.** Tests exercise behavior, not lines. Parameterized edge cases (e.g. `TestWave19PatientNameIgnorecaseFalsePositive`, `TestUnicodeHomoglyphBypass`) directly target regressions tied to numbered issues. 75% coverage floor is enforced in CI.
- **Graceful degradation.** Search provider down → empty results. Ollama missing → template fallback. KB uninitialised → empty context. No hidden exceptions from dependency failure.
- **Release hygiene.** Conventional commits, Keep-a-Changelog, ADRs for every meaningful architectural decision, CI gates for lint + type + test on both Python versions, trusted-publisher PyPI release via GitHub Actions.
- **Bug-response speed.** The "Wave" cadence in `CHANGELOG.md` shows 40+ real bugs caught and fixed in a few months, including security-relevant ones (ReDoS in #107, zero-width bypass in #108, HIPAA false-positive in #95).

This is what a healthy small codebase looks like. It is not what a venture-scale platform looks like.

---

## 7. Red Flags & Diligence Questions

The following are items the VC should press on before writing a check. Under the open-core framing the emphasis has shifted from "is AIPEA a business?" to "is the funnel working, and what are the paid products?"

**Funnel & adoption (open-core-specific):**

1. **Monthly download trajectory on PyPI.** Is it growing month-over-month? What is the 30-day active install count?
2. **External dependents.** How many non-Undercurrent GitHub repositories list `aipea` as a dependency? What do they use it for?
3. **Community signal.** Stars, forks, external issues filed, external PRs merged, Discord/Slack activity, blog/Twitter mentions.
4. **Funnel conversion.** What percentage of Agora IV / AEGIS pipeline — or closed revenue — originated from an AIPEA touchpoint? If the answer is "we don't track it," the gateway thesis is unfalsifiable.
5. **Step-up articulation.** Can the seller draw a crisp line between what AIPEA deliberately does not do and what Agora IV / AEGIS add on top? Fuzzy answers here suggest the paid products may not be differentiated.

**Claims hygiene (matters more in an open-core model, not less):**

6. **What does "HIPAA mode" promise in marketing and in sales conversations?** Compare the written claim to `security.py:734–744`. Detection-only is defensible *if* the copy says so. Enforcement claims are a liability that flows downstream to the paid products.
7. **The FedRAMP retraction.** Ask the founder directly: what other compliance claims in current marketing are not backed by enforcement in code? The honest ones admit this quickly. The unhealthy ones get defensive.
8. **External security audit.** Is there a credible timeline to SOC 2 Type II, third-party pentest, or jailbreak-corpus evaluation? For an OSS project adjacent to regulated industries, eventual attestation is table stakes.

**Technical defensibility (still relevant because the free layer still competes with other free layers):**

9. **Durable advantage over LangChain / LlamaIndex / Guardrails-AI / NeMo-Guardrails / AWS Bedrock Guardrails.** Each is free or bundled and ships more sophisticated filtering. AIPEA's differentiation in the *OSS* category cannot be "minimal dependencies" — that is a taste preference.
10. **Bus factor.** `git shortlog -sn` shows effectively a single contributor. What is the plan to turn AIPEA into a project with real community maintainers rather than a solo author with an OSS license?

**What's behind the curtain:**

11. **Agora IV and AEGIS, concretely.** Can the VC see the repositories, revenue, retention, and margin data? The investment case lives here, not in AIPEA.
12. **Metric anchoring in repo docs.** CLAUDE.md is meticulous about anchoring metrics with commit/date. That rigor is admirable but also implies the team knows metrics drift. Ask to see today's coverage, test count, and bug-catch rate rather than documented numbers.

---

## 8. What Would Change the Thesis

Under the open-core / gateway framing, the investment becomes meaningfully more attractive if **at least two** of the following are true:

- **Demonstrable funnel conversion.** The seller can show that a non-trivial share of Agora IV / AEGIS pipeline and closed revenue originated from AIPEA exposure. This is the single most important signal.
- **Visible OSS adoption.** Month-over-month download growth, a meaningful count of external dependents, external contributors merging real PRs, and third-party content (blog posts, comparison articles, integration guides) written without the seller's prompting.
- **Strong paid products.** Agora IV and AEGIS, reviewed under the same lens applied here, demonstrate real differentiation, retention, and margin.
- **Calibrated marketing.** Every compliance and security claim in the OSS layer matches what the code enforces; nothing needs to be retracted in the next twelve months.
- **Credible audit roadmap.** A funded, timeboxed plan for SOC 2 Type II and an independent security audit of the free layer (prompt-injection specifically), even if completion is 12–18 months out.

Absent most of these, the company is a consultancy attached to a PyPI package with two internal side projects.

---

## 9. Recommendation

**Do not form an investment decision on AIPEA alone.** The evidence in this repository cannot answer the question the VC is actually asking.

- **If the check is being written on AIPEA as the product,** decline. The open-source-gateway model requires a monetized tier, which this repo is not. AIPEA standalone is a maintenance project, not a venture.
- **If the check is being written on Undercurrent Holdings (AIPEA + Agora IV + AEGIS),** AIPEA is a *positive signal* about engineering culture and a *plausible* open-core funnel. Treat that as earning the team the right to a second-stage diligence — on Agora IV and AEGIS specifically — under the same adversarial lens applied here. Do not proceed on the AIPEA review alone.

**Before second-stage diligence is scheduled, request from the seller:**

1. PyPI download trajectory (12 months, monthly).
2. List of external repositories depending on `aipea` (any public GitHub-code search evidence is acceptable).
3. Community metrics: stars, external issues, external PRs merged, community-channel sizes.
4. Attributed funnel data: share of Agora IV / AEGIS pipeline and closed revenue that touched AIPEA first.
5. Read access to Agora IV and AEGIS repositories and current customer lists.

**If pressured to invest before that material is produced,** require as closing conditions:

1. Independent pentest and SOC 2 readiness assessment of the OSS layer (buyer-paid, seller-selected from a shortlist of three).
2. Restatement of every compliance claim in OSS marketing to match what the code enforces — done before close.
3. A named design partner in either healthcare or defense with a signed LOI before funds release.
4. Bus-factor mitigation: contractual commitment of the single current contributor plus at least one additional engineer funded from proceeds.
5. A written, dated plan to demonstrate funnel conversion from AIPEA into paid products within 12 months, with measurable checkpoints.

The core risk is not that AIPEA breaks — it almost certainly will not break, because the code is sober. The core risk is that **AIPEA remains a well-maintained internal tool with an OSS license**, the funnel never materializes, and the capital funds engineering salaries rather than a venture outcome. That risk is a question about the funnel and about the paid products. It is not a question this repository can answer.

---

## 10. Path Forward — Current State to Full Vision

The design-reference (`docs/design-reference/`) sketches a larger system than AIPEA alone; the library is one organ of it. The right transition is **not** to evolve AIPEA into a SaaS — `CLAUDE.md §1.2` correctly scopes AIPEA as a library. The transition is to harden AIPEA in place while the surrounding commercial products (Agora IV, AEGIS) are built to production scale around it.

What follows is a staged path with explicit exit criteria. Useful both as a roadmap for the team and as tranched-capital gates for the investor.

### Phase 0 — Pre-conditions (0–30 days)

Nothing downstream is worth doing until these are in motion.

- **De-risk bus factor.** A second committer with push rights. Module ownership documented. ADR review partner established.
- **Instrument OSS telemetry.** Opt-out install pings, PyPI download dashboard, GitHub traffic tracking. The gateway thesis is unfalsifiable without this data.
- **Claims audit.** Every compliance statement in README, website, and sales material walked against `security.py`. Retract or reword anything the code does not enforce. One more FedRAMP-style retraction in public is avoidable.

**Exit:** Two committers with commit access. 12 months of download history visible. No unbacked compliance claim in any external surface.

### Phase 1 — Earn the right to monetize (1–6 months)

Turn AIPEA from "plausible detection substrate" into "measurably better than the OSS alternatives in its category."

- **Adversarial benchmark.** Evaluate AIPEA against published jailbreak corpora (OWASP LLM Top 10, public injection datasets, 3–4 academic adversarial suites). Publish results — including losses.
- **Independent pentest** of `security.py` and the search-result scanning path. One reputable firm, scoped narrowly, findings posted to the repo. Cheap (~$25–40K) and disproportionately credible.
- **Swap regex injection layer for a fine-tuned small classifier** (DistilBERT-scale, ONNX-exported). Keep regex as fallback. Single most leveraged technical change: adversarial robustness moves from "patch-and-pray" to "trainable."
- **Broaden PII/PHI catalogs** to match real-world healthcare and financial surfaces (phone, address, medication names, ICD-10, account-number patterns). Clinical reviewer in the loop.
- **Sign 3 named design partners** — one healthcare, one regulated fintech, one public-sector/defense. Each with a signed LOI, a named contact, and a use case AIPEA+AEGIS actually solves.

**Exit:** Published adversarial benchmark competitive against Guardrails-AI / NeMo-Guardrails / LlamaGuard. Independent pentest report posted. Three design-partner LOIs. First external-contributor PRs merged.

### Phase 2 — Commercialize the edges, not the library (6–12 months)

Most of the capital goes here. AIPEA stays narrow; the surrounding products become real.

- **AEGIS as the enforcement layer on top of AIPEA detection.** Redaction, blocking, audit-trail persistence, role-based policy engine. This is what enterprise buyers pay for.
- **Agora IV as a multi-tenant service,** not a library import. Managed deployment, billing, metering, per-tenant isolation. The design-reference AWS deployment doc is the starting sketch.
- **Compliance infrastructure, in order:** SOC 2 Type II audit started (9-month clock), BAA capability for HIPAA customers, signed DPA template for GDPR, explicit FedRAMP-Moderate roadmap *only* if public-sector pipeline justifies it. Do not claim any of these before they are real.
- **Cross-instance learning endpoint** (opt-in, differentially private). The design-reference implies this; the shipped `learning.py` does not have it. Once it exists, AIPEA gains a data network effect: every adopter improves the shared detection, which improves the product, which attracts more adopters. The only place AIPEA itself gains a moat.
- **Pricing page and self-serve flow.** Free OSS → Team → Enterprise (with BAA/SSO/audit). Metering enforced in the service tier, not in AIPEA.

**Exit:** AEGIS + Agora IV in production with paying design partners. SOC 2 Type II achieved. Federated-learning endpoint serving real traffic. Revenue, even if small, from non-Undercurrent accounts.

### Phase 3 — Convert or pivot (12–24 months)

- **Funnel conversion measured.** Target: 3–5% of AIPEA monthly active installs → paid trial → paid seat, within a year of instrumentation. If the number is an order of magnitude below that, the gateway thesis is falsified and the company should reposition as direct enterprise sales.
- **Reference customers by vertical.** 3 healthcare, 3 public-sector, 3 fintech — each quotable.
- **Analyst coverage** for the compliance-aware-LLM-orchestration category. If the category doesn't exist, define it.
- **Open-core maintainers program.** At least one external maintainer with merge rights. Bus factor structurally solved.

**Exit:** ARR at a level that justifies Series B economics. Category position defensible against AWS Bedrock Guardrails / NVIDIA NeMo-Guardrails / LangChain's enterprise tier.

### What NOT to Do

- **Do not evolve AIPEA into a SaaS.** Keep it a library. The SaaS is AEGIS+Agora.
- **Do not ship billing or tier-gating code into AIPEA.** Free and unmetered. Metering lives upstack.
- **Do not chase FedRAMP until Phase 3** unless a named public-sector prospect is funding it. ATO is an 18-month, multi-million-dollar rabbit hole and the revenue rarely justifies it without a design partner.
- **Do not bring "future enhancement" labels** from the design-reference (federated learning, quantum-resistant, NAS) into AIPEA roadmap language until each has a customer-signed reason to exist. That is the habit that produced the FedRAMP retraction.

### Critical Path

The single item that must be true before anything else is measurable or fundable: **download / adoption telemetry must exist and must be growing.** Without it, every later milestone is unmeasurable and every later claim is unfalsifiable. It is the cheapest, most leveraged, most-neglected item in the entire plan.

---

## 11. Key Evidence Cited

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

*Prepared adversarially. Findings reflect evidence present in the repository as of 2026-04-24. Amended on the same date to reflect seller's representation that AIPEA is intentionally open-source and positioned as a gateway to commercial products (Agora IV, AEGIS) — a framing that reshapes the diligence questions without resolving them.*
