# AIPEA — Adversarial Due Diligence Review

**Date:** 2026-04-11
**Prepared for:** Venture Capital Group
**Subject:** AIPEA (AI Prompt Engineer Agent), open-source Python library
**Repo state reviewed:** `main` @ 2026-04-11, library `v1.3.2`
**Stance:** Adversarial. This is not a puff piece.
**Companion review:** [`investor-review-2026-04-11.md`](investor-review-2026-04-11.md) — positive self-assessment (39/45, 87%)

> **Why this document exists.** AIPEA already ships a positive investor self-assessment ([`investor-review-2026-04-11.md`](investor-review-2026-04-11.md)) that scored the project 39/45 and recommended invest-with-eyes-open. That review was written by the same agent that developed the code, so its Honesty row had an implicit bias. This adversarial review was commissioned as a counterweight: a third party given the *same* repo and asked to argue the strongest case *against* investment. Both documents are preserved verbatim in `docs/claude/audits/` per the AIPEA honesty convention (cf. `KNOWN_ISSUES.md`). The consolidated response plan that sequences findings from **both** reviews lives at `/Users/joshuakirby/.claude/plans/reactive-growing-lark.md` (local) and is tracked in `docs/ROADMAP.md` §P5 (committed).

---

## Executive summary

AIPEA is a **well-engineered prototype built by a disciplined solo developer**, shipped with real tests and honest internal docs. It is **not** a novel product, **not** a proven market fit, and its most marketable feature — compliance — is largely theater. The security module is the single best piece of the codebase and alone cannot carry an investment thesis. The gap between what the marketing implies ("AI-powered", "intelligent", "HIPAA/FedRAMP compliant", "military-grade") and what the code actually does (regex keyword matching, template string substitution, and a compliance allowlist with honestly-labeled stubs) is wide enough to create reputational and regulatory risk if sold to enterprise buyers without major caveats.

**Recommendation: Pass, or Conditional-with-Escrow.** The engineering talent is real; the product is not.

---

## 1. What AIPEA actually is (stripped of marketing)

AIPEA is a **prompt preprocessor**. A caller hands it a string; AIPEA runs a pipeline:

1. **Scan** the string for injection patterns, PII, and PHI (regex-based).
2. **Classify** the query type and domain (regex keyword lists).
3. **Optionally fetch** web context from Exa or Firecrawl (thin HTTP wrappers).
4. **Wrap** the prompt in one of ~7 hand-written templates ("Please provide a detailed technical response including...").
5. **Return** the enhanced string to the caller.

That's it. With one important exception (local Ollama), **AIPEA does not call LLMs.** The caller still has to invoke OpenAI/Anthropic themselves. The `engine.py` "Strategic tier" for cloud models is template substitution, not inference.

A competent engineer could rebuild the offline tier in an afternoon — it is ~20–30 LOC of template wrapping (`src/aipea/engine.py:110–180`).

---

## 2. What genuinely works (credit where due)

These are real and the VC should not ignore them:

- **Security module craftsmanship** (`src/aipea/security.py`). Homoglyph normalization (Cyrillic/Greek → ASCII, ~line 550), ReDoS-safe regex validation (lines 364–436), case-sensitive PHI compilation to avoid false positives. This is thoughtful defensive engineering.
- **Dependency discipline.** `pyproject.toml` shows a single required runtime dep: `httpx>=0.27.0`. `typer`/`rich` are genuinely optional and degrade gracefully in `cli.py`. Claim verified.
- **Test volume.** ~995 test functions across 16 files and ~14,558 LOC of test code. CI matrix runs Python 3.11 and 3.12 with `mypy --strict` and ruff. Not many solo projects invest this.
- **Config system.** Manual TOML/dotenv parsing (no extra deps) with UTF-8 BOM handling shows attention to Windows edge cases (`src/aipea/config.py`).
- **Honest internal documentation.** `src/aipea/security.py:610–626` openly tags `ComplianceMode.FEDRAMP` as an *"unsupported stub — config only, no behavioral enforcement."* A 54KB `KNOWN_ISSUES.md` spanning 19 bug-hunt waves shows the author is willing to catalog his own defects. This is unusually honest for an early-stage project.

If this engineer interviewed at a portfolio company, we would recommend hiring him. That is a very different statement from recommending the VC invest in AIPEA.

---

## 3. Where the narrative overshoots the substance

### 3.1 "Intelligent query analysis" is regex keyword matching
`src/aipea/analyzer.py:72–107` detects "temporal" intent by matching words like `latest|recent|breaking|news` and "medical domain" by matching `patient|diagnosis|treatment`. Complexity is a sentence count plus pattern-match tally, capped at 1.0 (lines 233–274). There is no ML, no embedding, no NLP model. It is dictionary lookup. "Intelligent" is a stretch.

### 3.2 "Context enrichment" is string concatenation
The pipeline flags, classifies, fetches, and **concatenates**. There is no cross-step reasoning — e.g., *"query is medical AND contains PHI, therefore redact and route to a HIPAA-covered provider"* — that would make this an agent. `enhancer.py` is an orchestrator, not a reasoner.

### 3.3 "AI-powered" in the README
The only real AI call in AIPEA is to a **local Ollama server** (`engine.py:696–750`). When cloud models (`gpt-4`, `claude-opus`) are specified, AIPEA does not call them — it formats a prompt and returns a string. The README's "AI-powered web search" is Exa's tagline (Exa does the AI; AIPEA wraps the HTTP call).

### 3.4 Prompt-injection detection is trivially bypassable
`security.py:318–327` lists ~8 injection regexes. Representative samples:

- `ignore\s+(previous|all)\s+instructions` — bypassed by "disregard prior directives", "forget everything above", any paraphrase.
- `<script[^>]*>` — lowercase only; misses `<SCRIPT>`, `< script>`, Unicode variants.
- `DROP\s+TABLE`, `UNION\s+SELECT` — SQL injection in a *prompt* context is cargo culting. This is not a real threat vector for an LLM preprocessor.
- `\{\{[\s\S]*?\}\}` — catches Jinja2; misses `${VAR}`, ERB, other template syntaxes.

The homoglyph normalization helps, but an adversary who knows the ruleset defeats it in one rewrite. **This is security theater dressed in competent regex engineering.**

Worse: `tests/test_security.py` verifies the regexes match the strings the author wrote. It does **not** test the module against published jailbreak corpora, OWASP LLM Top-10 payloads, or fuzzing. The module has never been adversarially tested by anyone but its author.

---

## 4. Compliance theater

This is the most important section for investors considering an enterprise angle. The README and docs advertise HIPAA, TACTICAL (military), and FedRAMP compliance modes. Here is what each mode actually does in the code:

| Mode | Marketed as | Actually enforced |
|---|---|---|
| **HIPAA** | "HIPAA support, PHI redaction" | Enables PHI regex patterns. On match: **logs a warning**. Does not block. Does not redact. No audit trail storage. No BAA. No encryption contract. (`security.py:634–644`) |
| **TACTICAL** | "military-grade" | Forces offline processing + allowlists `llama-3.3-70b`. That is the entire enforcement. No secure-enclave, no air-gap validation. |
| **FEDRAMP** | "FedRAMP support" | **Empty stub.** Honestly labeled as such in code (`security.py:610–626`). No behavioral change. |

Real HIPAA/FedRAMP requires: immutable audit logs with retention, encryption at rest and in transit, BAAs with vendors, data-residency enforcement, penetration testing, and third-party certification. AIPEA does **none** of these. What AIPEA sells as "compliance" is **input detection plus a model allowlist**, which is stage 1 of maybe 4. Selling this to a regulated buyer without that caveat is a liability.

The FedRAMP stub being honestly labeled in the code is refreshing — but the same label does not appear in the README or investor-facing docs. That gap is where risk lives.

---

## 5. Project health — red flags

### 5.1 Bus factor ≈ 1
Git log: ~41 commits from Joshua Kirby, ~16 from an account that appears to be an automation agent (`ThermoclineLeviathan`). The repo is ~33 days old. One person leaves and this project stalls. There is no `CONTRIBUTING.md` of substance, no `SECURITY.md`, no disclosed vuln-reporting policy, no second maintainer.

### 5.2 Documentation vs. code mismatch on version
`CLAUDE.md:2` declares `version: 3.0.5 | Updated: 2026-04-11`, while `src/aipea/__init__.py:16` and `pyproject.toml:7` both report `1.3.2`. (Generous reading: `3.0.5` is the Agent-Contract document version, not the library version — but this is not labeled clearly in the document header and will be misread by any reviewer skimming.) At best, sloppy. At worst, misleading.

### 5.3 Known compliance/security bugs sit unreleased in `main`
`CHANGELOG.md` "[Unreleased]" documents 13 bugs fixed after the `v1.3.2` PyPI release, including:

- **#95**: HIPAA PHI regex `re.IGNORECASE` false-positive flood.
- **#96**: HIPAA/TACTICAL compliance leak via hardcoded security context bypass.
- **#104**: UTF-8 BOM data corruption in `.env` parsing.
- **#107**: ReDoS denial-of-service in regex pattern validation.

Users running `pip install aipea==1.3.2` from PyPI **today** are running code with a documented HIPAA compliance bypass, a DoS, and a data-loss bug. The fixes exist in `main` but have not been released. If AIPEA has paying HIPAA-mode users at this moment, that is a live liability.

### 5.4 Bug waves suggest loose quality gates
Wave 19 fixed 13 bugs — several of which are the class of mistake that `mypy`, `ruff`, and tests exist precisely to prevent (case-insensitive regex flags, TOCTOU file-write races, duplicate exception handling, hardcoded security context). The existence of test volume and strict typing is not the same as those gates being tight.

### 5.5 No verifiable customers
`docs/integration/agora-adapter.md` describes a *future* migration ("After AIPEA extraction (Phase 3), AgoraIV *will* consume AIPEA"). `aegis-adapter.md` references tests that live in the AEGIS repo, not this one. **Zero public case studies. Zero download data worth reading** (first release ~2026-04-09). The claim that Agora IV and AEGIS are consumers is aspirational, not evidence of production use.

---

## 6. Competitive position

AIPEA overlaps with well-funded and well-adopted alternatives:

| Player | Overlap with AIPEA | Where AIPEA is weaker |
|---|---|---|
| **LangChain** (prompt templates, retrieval chains) | Near-complete on the offline tier | LangChain has adoption, ecosystem, retrieval chains |
| **LiteLLM** | Complementary — AIPEA is input-side only | LiteLLM actually routes to providers; AIPEA does not |
| **Guardrails AI / NeMo Guardrails** | AIPEA does input validation only | Guardrails has output validation and real policy engines |
| **Semantic Kernel** (prompt functions) | Similar model-family templating | Microsoft distribution |
| **Instructor / Outlines** | Out of scope for AIPEA | AIPEA has no structured-output story |

AIPEA is missing: output validation, multi-turn state, fallback chains, cost-aware routing. Its only real differentiator is **offline compliance tooling**: the SQLite knowledge base, homoglyph-aware scanner, and forced-offline TACTICAL mode. That is a narrow moat — attractive only to air-gapped or heavily regulated buyers, and those are long, hard sales cycles.

---

## 7. Risks, ranked

| # | Risk | Severity |
|---|---|---|
| 1 | **Regulatory liability from unbacked compliance claims.** Selling HIPAA/FedRAMP to a buyer who believes the marketing and discovers detection-only enforcement after a PHI exposure. | High |
| 2 | **Injection bypass reputational risk.** First public red-team write-up bypassing the regex list damages the brand permanently. | High |
| 3 | **Live PyPI users running code with a documented HIPAA bypass bug.** Unreleased fixes in `main` mean anyone who installed `v1.3.2` is unpatched. | High |
| 4 | **Bus factor 1.** Solo maintainer, 33-day-old repo, no second committer. | High |
| 5 | **TAM unknown.** Zero verifiable customers. Overlap with LangChain/Guardrails means distribution is the hard problem, not tech. | High |
| 6 | **Doc/version drift.** `CLAUDE.md` header shows `3.0.5`; code is `1.3.2`. Cosmetic, but diligence-unfriendly. | Medium |
| 7 | **Quality gates loose.** Wave 19 caught bugs that strict typing + linting should have. | Medium |
| 8 | **Offline tier is commodity.** Easily re-implementable; not defensible. | Medium |

---

## 8. Questions the VC must get answered before committing

These are the specific external checks I could not perform from the repo alone, and which a partner should insist on:

1. **Does `pip install aipea==1.3.2` from PyPI actually work and match the git SHA claimed?** (Highest-leverage single check. Several CLAUDE.md references to tags and releases could not be verified locally.)
2. **Is there a single signed design partner for HIPAA or FedRAMP?** If yes — which one, what's the contract scope, has a third party audited AIPEA against their compliance framework?
3. **Who has performed an independent security audit of `security.py`?** Not an internal review. A third party with an LLM-adversarial corpus.
4. **Is there a second committer lined up, and what's the knowledge-transfer plan if Joshua is unavailable for 30/60/90 days?**
5. **What is the release plan for the "[Unreleased]" fixes?** If #95/#96/#104/#107 have been sitting in `main` post-v1.3.2, why has a `v1.3.3` not shipped? (Expected answer: a process gap — which is itself informative.)
6. **Are Agora IV and AEGIS actually importing AIPEA in production, or are the adapter docs aspirational?** Ask for a git-blame of an import statement in the consumer repo.

---

## 9. Bottom line

**What you are being asked to buy:** a disciplined solo engineer who ships working code, real tests, and honest internal documentation — wrapped in marketing that over-reaches on AI sophistication, compliance coverage, and customer traction.

**What the code actually is:** a prompt preprocessor with a genuinely good security scanner, a commodity offline template tier, and compliance modes that are detection-plus-allowlist, not real regulatory controls.

**What the market is:** unproven. Overlapping players (LangChain, LiteLLM, Guardrails) own distribution. The narrow defensible slice — air-gapped/regulated buyers — is a slow, expensive sales motion.

**Our recommendation: Pass.** If the VC has high conviction on the founder specifically, a **conditional bet with escrow** is defensible — tied to (a) a signed design partner in a regulated vertical, (b) a third-party security audit of the injection and compliance modules, and (c) version/doc cleanup plus a `v1.3.3` release that lands the "[Unreleased]" fixes on PyPI before any investment closes. Absent those conditions, this is a strong technical founder without a product-market thesis worth underwriting.

---

## Appendix: Corrections since this review was written (2026-04-11)

A verification sweep against `main` as of 2026-04-11 after this review landed found the following:

- **§5.2 version drift** — The `CLAUDE.md` `3.0.5` field *is* labeled as the Agent Contract version in the document body (section titles use "Agent Contract"), though the header line is ambiguous to a skim reader. The adversarial framing is slightly harsh; the underlying diligence concern (visual drift-by-misread) is valid and is addressed in Wave B3 of the response plan.
- **§3.4 "trivially bypassable"** — The 8 injection regexes are defended by NFKC normalization + a 35-entry Unicode confusable map + `_is_regex_safe()`. "Trivially bypassable" overstates the current state. The underlying concern (no external adversarial corpus testing) stands and is addressed in Wave D4 of the response plan.
- **§5.3 "unreleased bugs"** — **Closed**. Confirmed verbatim; this was the #1 adversarial finding and was resolved by shipping `v1.3.3` on 2026-04-11 (see `CHANGELOG.md` `[1.3.3]` and GitHub release v1.3.3).
- **§5.1 "No `SECURITY.md`"** — **Closed**. `SECURITY.md` was added in `v1.3.3`. `CONTRIBUTING.md` is still thin and is addressed in Wave B4 of the response plan.
- **§4 README compliance framing** — README *does* caveat FedRAMP as "planned" (line 248 as of 2026-04-11). It does not explicitly state that HIPAA/TACTICAL are detection + allowlist only, which is the stronger framing the adversarial review demands. Addressed in Wave B2 of the response plan.

None of the corrections materially change the verdict. They are recorded here to preserve the adversarial review's framing verbatim while giving future readers an anchor to the repo's current state.

---

*Adversarial review preserved verbatim from the 2026-04-11 engagement. For the consolidated response plan covering this review + the positive self-assessment, see ROADMAP.md §P5 and the wave tracking in TODO.md.*
