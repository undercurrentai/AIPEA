# AIPEA Metrics

> Signals of AIPEA's adoption, usage, and engineering quality. Small
> numbers, honestly reported. Updated 2026-05-02 (post-Phase-4.c PR #70
> adversarial corpus expansion shipped; v1.6.2 shipped to PyPI 2026-04-24;
> v1.7.0 release-cut target 2026-06-15).

This page exists because an investor's first two questions are
"who's using it?" and "who's about to?" — and "trust me" isn't an
answer. The numbers below are all externally verifiable.

---

## Dynamic badges (live from PyPI, GitHub, Codecov)

```
┌─ Package ───────────────────────────────────────────┐
│ PyPI version:    https://pypi.org/project/aipea/    │
│ Downloads/mo:    https://pypistats.org/packages/aipea│
│ Python:          3.11 + 3.12 (CI-tested matrix)     │
│ License:         MIT                                │
└─────────────────────────────────────────────────────┘

┌─ Repo ──────────────────────────────────────────────┐
│ GitHub:          https://github.com/undercurrentai/AIPEA  │
│ Stars:           https://github.com/undercurrentai/AIPEA/stargazers │
│ Dependent repos: https://github.com/undercurrentai/AIPEA/network/dependents │
│ Open issues:     https://github.com/undercurrentai/AIPEA/issues │
└─────────────────────────────────────────────────────┘

┌─ Quality ───────────────────────────────────────────┐
│ CI:              https://github.com/undercurrentai/AIPEA/actions/workflows/ci.yml  │
│ Coverage:        https://codecov.io/gh/undercurrentai/AIPEA   │
│ Security policy: https://github.com/undercurrentai/AIPEA/security/policy  │
└─────────────────────────────────────────────────────┘
```

See the README badges for live rendering of these.

---

## Engineering-quality signals (2026-04-24)

| Metric | Value | Source of truth |
|---|---|---|
| Library version | 1.6.2 | [`pyproject.toml:7`](../pyproject.toml), [PyPI](https://pypi.org/project/aipea/1.6.2/) |
| Source LOC | ~10,662 | `wc -l src/aipea/*.py` |
| Test count | 1,282 collected | `pytest --collect-only` |
| Test coverage | 93.46% | Codecov, `make test` |
| Coverage floor (CI gate) | 75% | [`pyproject.toml:107`](../pyproject.toml) |
| Public API surface | 50 symbols in `__all__` | [`src/aipea/__init__.py`](../src/aipea/__init__.py) |
| Core runtime dependencies | **1** (`httpx>=0.27.0`) | [`pyproject.toml:24-26`](../pyproject.toml) |
| CI matrix | Python 3.11 + 3.12 | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) |
| Static-analysis gates | Ruff (14 rule families incl. S/Bandit) + mypy strict | [`pyproject.toml:67-82`](../pyproject.toml) |
| Second-reviewer gate | Triple-AI (gpt-5.4-pro + Codex gpt-5.3-codex + Claude Opus 4.6) on security-critical PRs | [`.github/workflows/ai-second-review.yml`](../.github/workflows/ai-second-review.yml) |
| Mutation-score infra | `mutmut` configured; CI gate deferred to v1.7.0+ | [`pyproject.toml:110-111`](../pyproject.toml), [`docs/ROADMAP.md §P5d`](ROADMAP.md) |

---

## Adversarial evaluation hit rates (snapshot 2026-05-02)

Honest hit-rate of AIPEA's `INJECTION_PATTERNS` against published
adversarial corpora. **Includes losses.** This table is manually
updated when `tests/fixtures/adversarial/baseline.json` is
re-baselined; the nightly CI workflow at
[`.github/workflows/adversarial.yml`](../.github/workflows/adversarial.yml)
produces fresh numbers daily, visible in Actions but not silently
committed. Source-code anchor for the regex set:
[`src/aipea/security.py:367-441`](../src/aipea/security.py).

Provenance for each corpus is in
[`tests/fixtures/adversarial/SOURCES.md`](../tests/fixtures/adversarial/SOURCES.md).
Design rationale in
[ADR-008](adr/ADR-008-adversarial-evaluation-suite.md) +
[ADR-005 §C.1](adr/ADR-005-pr52-vc-adversarial-review-response.md).

| Corpus | License | Size | Hit-rate / FPR | Notes |
|---|---|---:|---:|---|
| OWASP LLM Top 10 (bright-line) | CC-BY-SA, vendored | 67 | **100%** (gating) | Patterns AIPEA was specifically written to detect. Must-pass. |
| OWASP LLM Top 10 (extended, all categories) | CC-BY-SA, vendored | 53 | 9.4% | Real adversarial techniques regex-only defense may not yet handle. Per-category breakdown in `baseline.json`. |
| **PromptInject (overrides)** | MIT | 17 | **29.4%** | Canonical instruction-override family; below the 60–80% literature expectation due to corpus narrowing in the extraction script — broaden the heuristic in a follow-up to enrich coverage. |
| **JailbreakBench JBB-Behaviors (harmful)** | MIT | 100 | 0% flagged | Harmful-content goals (e.g., "explain how to hotwire a car"); AIPEA's regex set is **not** designed to flag these. 0% is correct — these test semantic content, not override syntax. |
| **JailbreakBench JBB-Behaviors (benign FPR)** | MIT | 100 | **0.0% FPR** | False-positive-rate control set. Target <5%. AIPEA passes cleanly: zero benign queries are flagged. |
| **Garak `promptinject` + `dan` + `latentinjection` extracts** | Apache-2.0 | 43 | **7.0%** | Paraphrase-coverage breadth; reveals DAN-style and latent-injection gaps. |

**ADR-005 §C.1** declined a DistilBERT-classifier replacement; instead,
new regex patterns ship via separate PRs when this benchmark surfaces
paraphrase or encoding gaps (the Wave 21 paraphrase verbs were added
to `INJECTION_PATTERNS` via this exact pattern). The benchmark exists
to surface gaps honestly, not to drive AIPEA toward a moving 100%
target.

### Notable losses (by category)

OWASP extended-tier failure breakdown reveals the categories AIPEA's
regex set does **not** currently catch (each is a candidate for a
future targeted regex extension, never a classifier swap):

| OWASP category | Hit-rate | Notes |
|---|---:|---|
| LLM01 (delimiter) | 0/5 | Delimiter-based injection bypasses ASCII boundaries |
| LLM01 (encoding) | 0/5 | Base64 / URL-encoded payloads slip past byte-level regex |
| LLM01 (multi-language) | 0/8 | Non-English override phrasings need locale-aware patterns |
| LLM01 (paraphrase) | 0/15 | Paraphrase variants beyond Wave-21 verbs |
| LLM01 (role-play) | 0/8 | DAN-style "you are now X" framings |
| LLM01 (indirect) | 5/6 | Mostly caught — indirect injection through quoted user text |
| LLM07 (elicitation) | 0/6 | System-prompt extraction attempts |

These numbers will move when targeted PRs ship new patterns. They are
published here so any drift downward is publicly visible.

---

## Release cadence

| Version | PyPI date | Headline change |
|---|---|---|
| v1.0.0 | 2026-02-14 | Extraction from Agora IV v4.1.49 |
| v1.1.0 | 2026-02-17 | Engine test coverage (49% → 99%) |
| v1.2.0 | 2026-03-13 | Logic coherence remediation (F1-F14) |
| v1.3.0 | 2026-03-?? | Dialogical Clarification + named strategies + semantic KB search + quality assessor |
| v1.3.3 | 2026-04-11 | Wave A: 13 security fixes; SECURITY.md added |
| v1.4.0 | 2026-04-13 | Adaptive Learning Engine (PR #31) |
| v1.5.0 | 2026-04-15 | Compliance-aware learning (ADR-003; PR #40) |
| v1.6.0 | 2026-04-15 | Taint-aware feedback averaging (ADR-004; PR #44) |
| v1.6.1 | 2026-04-22 | Injection-regex hardening (8 → 10 patterns; PR #50) |
| v1.6.2 | 2026-04-24 | PR #52 VC-review response, telemetry dashboard, HTTP_TIMEOUT deprecation, P5e trio, benchmarks deleted (PRs #51/#52/#53/#55/#56) |

Average cadence from v1.3.0 onward: ~1 release/10 days. 10 PyPI releases
over ~10 weeks. Next planned release: v1.7.0 (~2026-06-15) per the
approved v2.0.0 roadmap in [`TODO.md`](../TODO.md).

---

## Adoption signals

### Named adopters

- **Agora IV** — extraction source and longest-running consumer (see
  [`docs/adopters.md`](adopters.md)).
- **AEGIS** — downstream via `aegis-governance/src/integration/aipea_bridge.py`.

### Dependent-repo count (public signal)

Track live at
[`github.com/undercurrentai/AIPEA/network/dependents`](https://github.com/undercurrentai/AIPEA/network/dependents).
As of 2026-04-23, only internal Undercurrent Holdings repos declare
AIPEA as a dependency. External adopters are welcome — open a
[Discussion](https://github.com/undercurrentai/AIPEA/discussions) to
be listed.

### PyPI downloads — live charts

- **Trajectory chart** (last 30 days, updated daily):
  [![Downloads](https://static.pepy.tech/badge/aipea/month)](https://pepy.tech/project/aipea)
- **Cumulative**: [![Total downloads](https://static.pepy.tech/badge/aipea)](https://pepy.tech/project/aipea)
- **Full dashboard**: [`pepy.tech/project/aipea`](https://pepy.tech/project/aipea)
- **Raw stats**: [`pypistats.org/packages/aipea`](https://pypistats.org/packages/aipea)

Expect small absolute numbers through 2026 — AIPEA is a B2B library,
not a consumer package. Trajectory matters more than absolute volume.

### GitHub activity — live

- **Stars**: [![Stars](https://img.shields.io/github/stars/undercurrentai/AIPEA?style=flat)](https://github.com/undercurrentai/AIPEA/stargazers)
- **Forks**: [![Forks](https://img.shields.io/github/forks/undercurrentai/AIPEA?style=flat)](https://github.com/undercurrentai/AIPEA/network/members)
- **Open issues**: [![Issues](https://img.shields.io/github/issues/undercurrentai/AIPEA)](https://github.com/undercurrentai/AIPEA/issues)
- **Last commit**: [![Last commit](https://img.shields.io/github/last-commit/undercurrentai/AIPEA)](https://github.com/undercurrentai/AIPEA/commits/main)
- **Contributors**: [![Contributors](https://img.shields.io/github/contributors/undercurrentai/AIPEA)](https://github.com/undercurrentai/AIPEA/graphs/contributors)
- **Dependent repos (public)**:
  [`github.com/undercurrentai/AIPEA/network/dependents`](https://github.com/undercurrentai/AIPEA/network/dependents)

---

## Security-quality signals

Beyond the automated gates:

- 20 security/correctness defects fixed via bug-hunt waves 18, 19, 20
  (all with regression tests). Full list: [`KNOWN_ISSUES.md`](../KNOWN_ISSUES.md).
- Zero post-release security incidents across 9 PyPI releases (2026-02-14
  to 2026-04-23).
- Every `security.py`, `__init__.py`, `pyproject.toml`, or
  `.github/workflows/**` PR has been reviewed by **three** AI reviewers
  (gpt-5.4-pro, OpenAI Codex gpt-5.3-codex, Claude Opus 4.6) since Wave C1
  (2026-04-11). Verdict enforcement: `REQUEST_CHANGES` from any reviewer
  blocks merge via branch protection.
- [`SECURITY.md`](../SECURITY.md) documents disclosure policy, response
  SLAs, and — importantly — the honest scope of what AIPEA's compliance
  modes do and do not enforce. FedRAMP is deprecated and scheduled for
  v2.0.0 removal per [ADR-002](adr/ADR-002-fedramp-removal.md).

---

## Signals we currently do NOT publish — and why

Honest gaps, per the PR #52 adversarial VC review §7 diligence
questions. We list these so the absence isn't discoverable only by
searching for "dependents: 0".

- **Funnel conversion rate** (AIPEA → Agora IV / AEGIS paid seats) —
  blocked on AEGIS/Agora-side instrumentation. Tracked as Plan B
  finding #14 in the
  [PR #52 response plan](https://github.com/undercurrentai/AIPEA/blob/main/docs/adr/ADR-005-pr52-vc-adversarial-review-response.md)
  (ADR-005 shipping v1.7.0). Until that exists, the open-core gateway
  thesis cannot be quantified.
- **External contributors**: **0** at 2026-04-24. Single-author repo
  per `git shortlog -sn`. Bus-factor mitigation is active — see
  `docs/MAINTAINERS.md` (v1.8.0) and the second-committer contract
  (Plan B #16, authorized 2026-04-24).
- **Signed design partners**: **0** at 2026-04-24 across healthcare /
  fintech / defense verticals. Tracked as Plan B finding #21.
- **External PRs merged**: **0** at 2026-04-24 (all 52 merged PRs
  are from the maintainer). Inbound contribution path documented in
  `CONTRIBUTING.md` + pinned Discussion (v1.6.3).
- **Named customer counts beyond internal Undercurrent products** — we
  don't have design partners or beta customers yet. When we do, they'll
  appear in [`docs/adopters.md`](adopters.md) with their consent.
- **Projected revenue** — AIPEA is a platform library, not a SaaS product;
  revenue signals live at the product layer (AEGIS, LIBERTAS). See
  [Undercurrent Holdings root CLAUDE.md](../../../CLAUDE.md) §12 for
  product pricing.
- **Internal incident-rate metrics** — covered under the Agora IV case
  study at [`case-studies/agora-iv-v1.md`](../case-studies/agora-iv-v1.md)
  with appropriate anonymization of internal operational details.
- **Opt-out install telemetry / phone-home pings** — **declined** by
  policy. Privacy-hostile to regulated consumers (HIPAA, TACTICAL);
  contradicts AIPEA's security-substrate brand. Rationale:
  [ADR-005 §C.2](adr/ADR-005-pr52-vc-adversarial-review-response.md#c2-opt-out-install-pings--telemetry).
  `pypistats` + GitHub Insights already cover the same signal without
  the privacy cost.

---

*Metrics maintained by [`@joshuakirby`](https://github.com/joshuakirby).
Want a metric added? Open a [Discussion](https://github.com/undercurrentai/AIPEA/discussions)
or PR. Honest small numbers, always.*
