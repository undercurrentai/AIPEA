# AIPEA Investor Review & Engineering Recommendations

**Date:** 2026-04-11
**Subject:** AIPEA v1.3.2 — Python prompt-preprocessing library
**Scope:** ~9.6K LOC source, ~13.5K LOC tests, 53 commits across the 50 days from 2026-02-19 to 2026-04-10
**Lead programmer:** Joshua Kirby
**Purpose:** Self-assessment written in investor voice — an evaluation of the project and its lead programmer from the perspective of a potential investor, followed by five actionable recommendations. Scored by the same agent that generated the PR, so the "Honesty" row should be read accordingly.

---

## Part 1 — Investor Scorecard

Nine criteria, each scored 1–5 (1 = red flag, 3 = competent, 5 = exceptional).

| # | Criterion | Score |
|---|-----------|------:|
| 1 | Product judgment | 4 / 5 |
| 2 | Architectural soundness | 5 / 5 |
| 3 | Technical depth | 4 / 5 |
| 4 | Code craftsmanship | 4 / 5 |
| 5 | Test discipline | 5 / 5 |
| 6 | Engineering process | 5 / 5 |
| 7 | Honesty & self-awareness | 5 / 5 |
| 8 | Shipping velocity | 4 / 5 |
| 9 | Risk profile | 3 / 5 |
| | **Total** | **39 / 45 (87%)** |

### 1. Product Judgment — 4 / 5

AIPEA preprocesses prompts before they reach an LLM: PII/PHI scanning, prompt-injection blocking, query analysis, optional web/offline context enrichment, and model-specific prompt formatting. The three-tier model (Offline / Tactical / Strategic) maps to real operational regimes — air-gapped, BAA cloud, general web.

- **Plus:** Defensible niche. Compliance preprocessing is a real enterprise need.
- **Minus:** Not visionary. Differentiation lives in the security layer and offline KB, not the search wrappers.

### 2. Architectural Soundness — 5 / 5

The dependency graph in `CLAUDE.md §4` is enforced in code, not aspirational:

- `security.py`, `knowledge.py`, `config.py`: stdlib only
- `search.py`: stdlib + httpx only
- No circular imports; clean facade in `src/aipea/enhancer.py:224-254`
- 36 public symbols in `__all__` — minimal and coherent

Most "extracted from production" libraries fail here; this one didn't.

### 3. Technical Depth — 4 / 5

~60% real engineering, ~40% thoughtful orchestration of existing tools.

**Genuinely substantive:**

- ReDoS-safe regex validation (`src/aipea/security.py:332-391`) — checks for nested quantifiers, unbounded repeats, catastrophic backtracking.
- Unicode confusables map (35 entries, Cyrillic/Greek → Latin) defeats homoglyph injection bypass.
- Offline knowledge base (`src/aipea/knowledge.py`, 1249 LOC) — SQLite + zlib compression + FTS5 with BM25 fallback + thread-safe locking.
- Double-checked locking for Ollama health probe (`src/aipea/engine.py:631-635`).

**Wrapper-like:**

- Exa/Firecrawl providers are httpx clients with result parsing. Honest, functional, not novel.
- Prompt formatting is template-based (the README is clear about this).

### 4. Code Craftsmanship — 4 / 5

- **Typing:** `mypy --strict` enforced in CI. Only **2 `# type: ignore`** in 9.6K LOC, both documented (`engine.py:634`, `knowledge.py:537`). `py.typed` marker present.
- **Structure:** Largest file is `enhancer.py` (1373 LOC) but composed as a facade, not a god class.
- **Docstrings:** Public APIs documented with Args/Returns/Raises throughout.
- **Anti-patterns:** None major. No dead code, no cargo cult.
- **Weakness:** Genuine broad `except Exception:` swallows at `src/aipea/cli.py:191`, `:220`, `:283`, and `:438`. `cli.py:391` is a residual fallback after a specific `TimeoutExpired` catch; `config.py:444` is a cleanup-and-reraise pattern and is not actually a swallow. See Recommendation 3 below.

### 5. Test Discipline — 5 / 5

- 752 tests, **91.79% coverage** (CI floor is 75%)
- Test LOC : source LOC = **1.4×**
- Assertion density ~1.7 per test in spot checks
- 116 black-box E2E tests added in Wave 8
- Real edge cases: empty queries, ReDoS attack patterns, frontier-model allowlists, parametrized enum sweeps
- Async tests use `AsyncMock` properly; pytest markers used consistently

### 6. Engineering Process — 5 / 5

- **CI:** lint + mypy strict + multi-Python (3.11/3.12) tests + 75% coverage floor + Codecov
- **Workflows:** CodeQL, Dependabot, dependency-review, compliance-nightly (Trivy/Checkov/Safety/mutmut), compliance-evidence-scheduler, scaffold-checks, publish
- **All GitHub Actions SHA-pinned**, not tag-pinned — enterprise grade
- **PyPI release:** OIDC Trusted Publisher, gated `release` environment, quality gate re-runs before publish
- **Pre-commit:** Ruff, mypy, Bandit, Semgrep, Gitleaks, plus custom `ai-rmf-artifacts` and `ai-act-lint` hooks
- **Conventional Commits** consistently followed; atomic commits; PR-merged feature branches

### 7. Honesty & Self-Awareness — 5 / 5

Rare and noteworthy:

- Stubs are labeled as stubs (Context7 provider; FedRAMP enforcement at `src/aipea/security.py:610-626`)
- `KNOWN_ISSUES.md` (54KB) documents 18 bug-hunt waves with fixed/deferred/reclassified status
- Wave 18 closes 7 deferred bugs from earlier waves and reclassifies one as INTENTIONAL with citations to Exa's SDK docs
- `CHANGELOG.md` is genuinely synchronized with commits; PR numbers cross-reference everywhere
- README doesn't oversell; "Getting Started" admits zero-config path uses template-based enhancement only

### 8. Shipping Velocity — 4 / 5

- 5 releases in 50 days: 1.1.0 → 1.2.0 → 1.3.0 → 1.3.1 → 1.3.2
- Semver respected (new optional features = minor; fixes/metadata = patch)
- 53 commits in the 50-day snapshot window; 39 commits in the most recent 30 days — sustained, focused work
- PyPI presence is real: `aipea==1.3.2` is published with monthly download badge

### 9. Risk Profile — 3 / 5

| Risk | Severity | Notes |
|------|----------|-------|
| Solo human contributor | High | Only Joshua Kirby commits code; ThermoclineLeviathan is automation. Bus-factor 1. |
| FedRAMP claimed but stubbed | Medium | Honestly labeled, but commercially risky. |
| Pattern-based PII detection | Medium | Won't catch obfuscation ("S-S-N is one two three..."). |
| No mutation testing in main CI | Low | `mutmut` runs nightly with `continue-on-error`. |
| No performance regression tests | Low | Semantic search + FTS can degrade silently. |
| "Extracted from Agora IV v4.1.49" unverifiable from this repo | Low | Internal evidence is consistent but not independently verified. |
| Heavy compliance scaffolding for 1-person shop | Watch | Visionary or premature depending on enterprise pipeline. |

---

## Part 2 — Investor Verdict

**Recommendation: Invest, with eyes open about what you're buying.**

You are not buying a visionary. You are buying a **disciplined, honest executor** who:

- picks defensible problems and scopes them realistically,
- ships on a sustainable cadence with real CI/CD, real tests, and real governance,
- writes code that survives `mypy --strict` with only two documented exceptions across 9.6K LOC,
- documents bugs publicly and closes them in numbered waves rather than hiding them,
- respects his own architectural rules (the dependency graph is enforced in code, not just in `CLAUDE.md`).

The strongest signal is honesty. Most engineers in early-stage companies overclaim; this one labels his stubs, reclassifies bugs with citations, and ships a `Development Status :: 5 - Production/Stable` classifier only after hitting 91.79% coverage. That's a leading indicator for the kind of person who won't tell you the prototype is "basically done" three months before it actually is.

**Open questions before writing a check:**

1. **Bus factor.** If the thesis depends on AIPEA scaling, who's the second engineer, and when?
2. **Customers.** The compliance scaffolding is sized for enterprise. Is there a paying pipeline?
3. **Moat.** The security layer and offline KB are real; the search providers are commodity. What's the durable advantage?
4. **FedRAMP.** Roadmap with a customer attached, or aspirational scaffolding?

If the answers are credible, this is a strong **technical** bet. The engineering risk is low; the **commercial** risk is unmeasured by anything in this repo.

---

## Part 3 — Five Detailed Recommendations

The gap between 87% and 95%+ isn't code quality — it's bus factor, commercial validation, and a few honest engineering tightenings. These five recommendations target exactly that gap, ordered by leverage.

### Recommendation 1 — Solve the bus-factor problem with a paid second pair of eyes

**Gap addressed:** Risk profile (3/5). Every commit traces back to one human; no external code review on any PR.

**Action:** Contract a part-time senior reviewer with a security background for ~4 hours/week. Add a `CODEOWNERS` file requiring their review on:

- `src/aipea/security.py`
- `src/aipea/__init__.py` (public API surface)
- `pyproject.toml` (dependency changes)

Document the review SLA in `CONTRIBUTING.md`.

**Why this is #1:** The single largest investor objection isn't code quality — it's bus factor 1. A second pair of eyes on security-critical code is also the cheapest way to harden the most sensitive module in the codebase.

**Effort:** Process change + ongoing contractor cost.
**Investor signal:** Very high.
**Engineering value:** High (security review on `security.py`).

### Recommendation 2 — Resolve FedRAMP: ship it or stop claiming it

**Gap addressed:** Commercial liability. FedRAMP is prominent enough in the README and `ComplianceMode` enum to attract enterprise interest, but `src/aipea/security.py:610-626` honestly labels it as a stub. A government buyer will spot the gap inside the first hour of evaluation.

**Decision fork:**

- **Path A (commercial):** Find one design-partner organization that actually needs FedRAMP. Scope a minimum-viable enforcement surface — model allowlist, audit-trail hook, encryption-at-rest contract — built *with their input*, shipped as v1.4.0. Converts a liability into a wedge into the regulated-AI market.
- **Path B (honest):** Remove `FEDRAMP` from `ComplianceMode`, strike it from the README, and write a one-page ADR in `docs/adr/` explaining why. Leave HIPAA and TACTICAL as the supported regulated modes.

Either is defensible. The current state is the worst of both worlds.

**Effort:** A = months; B = one afternoon.

### Recommendation 3 — Tighten CLI error handling and introduce a custom exception hierarchy

**Gap addressed:** Code craftsmanship (4/5). Genuine broad `except Exception:` swallows in `src/aipea/cli.py` at lines 191 and 220 (Exa/Firecrawl connectivity probes that log at DEBUG and return `False`), line 283 (rich version lookup — should catch `PackageNotFoundError`), and line 438 (knowledge-base doctor check). Line 391 already catches `subprocess.TimeoutExpired` specifically and only falls through to a residual `except Exception:`, which is a weaker candidate. `config.py:444` is a cleanup-and-reraise pattern (`except Exception: ... raise`), so it is *not* a swallow and is out of scope for this recommendation. Library consumers (Agora, AEGIS) can't discriminate "search provider 401'd" from "SQLite file locked" from "regex pattern malformed" — every genuine swallow looks the same.

**Action:**

1. Create `src/aipea/errors.py` with an `AIPEAError` base and five subclasses: `SecurityScanError`, `EnhancementError`, `KnowledgeStoreError`, `SearchProviderError`, `ConfigError`.
2. Walk each genuine broad `except Exception:` swallow and replace it with specific exception types actually expected. Keep one outermost catch-all in CLI command handlers that logs full traceback at DEBUG and a friendly message at ERROR — but only one, at the boundary.
3. Add one regression test per converted block. Fits naturally into the existing bug-hunt wave methodology — file under the next open wave number (Wave 19 is already taken by PR #14).

**Effort:** 1–2 days.
**Result:** Pushes the code-craftsmanship category from 4/5 toward 5/5 in a subsequent self-assessment.

### Recommendation 4 — Promote mutation testing and add performance regression gating

**Gap addressed:** Risk profile. 91.79% line coverage doesn't prove operator correctness. Mutmut is nightly with `continue-on-error`. No latency SLOs.

**Action:**

1. **Mutation testing:** Resolve the enum-trampoline issue noted in `KNOWN_ISSUES.md`. Move `mutmut` into a dedicated CI job with a mutation-score floor that ratchets up 1% per release. Start at current baseline; don't try to hit 100%.
2. **Performance regression:** Add a `benchmarks/` `pytest-benchmark` suite measuring `enhance_prompt()` p50/p95 latency for each tier (Offline / Tactical / Strategic) against ~10 representative queries. Check in a baseline JSON. Add a CI job that fails if p95 regresses by more than 20% versus baseline.

Together these catch the slow drift that 752 unit tests won't.

**Effort:** ~1 week.
**Result:** Converts "we have great coverage" into "we have great coverage *and* we'd notice if it stopped working."

### Recommendation 5 — Build a commercial validation surface

**Gap addressed:** Risk profile. The compliance scaffolding (NIST AI RMF artifacts, EU AI Act hooks, OPA policy) is sized for enterprise, but there's no visible evidence enterprises are buying. An investor's first two questions are "who is using this?" and "who is about to?" — neither has a discoverable answer right now.

**Action (non-engineering):**

1. Create `case-studies/` with two anonymized integration write-ups. Agora IV is the obvious first; AEGIS is the second. Include real numbers — latency, security findings caught, compliance modes used.
2. Add a `docs/metrics.md` page linking PyPI download trends, GitHub stars, dependent-repo count. Even small numbers, honestly reported, beat no numbers.
3. Open GitHub Discussions and commit to one weekly office-hours slot.
4. Identify three target design-partner orgs (one HIPAA, one TACTICAL/defense, one general SaaS) and write a one-page outreach pitch for each. Send them.

**Effort:** 2–3 weeks of focused outreach.
**Why:** The codebase can't do BD work for you. The technical bet is strong; the commercial bet is invisible.

---

## If Only One Recommendation Is Acted On

**Recommendation 1 — bus factor.** A second qualified reviewer on `src/aipea/security.py` simultaneously removes the highest-risk objection from investor diligence *and* hardens the most sensitive module in the codebase. Everything else can wait a quarter; that one can't.

---

*Prepared for investor evaluation of AIPEA v1.3.2 on 2026-04-11.*
