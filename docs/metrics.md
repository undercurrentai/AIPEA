# AIPEA Metrics

> Signals of AIPEA's adoption, usage, and engineering quality. Small
> numbers, honestly reported. Updated 2026-04-24 (v1.6.2 shipped to
> PyPI; PR #52 adversarial-review response in flight).

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
  contradicts AIPEA's security-substrate brand. Rationale: PR #52
  response Plan C.2 in ADR-005. `pypistats` + GitHub Insights already
  cover the same signal without the privacy cost.

---

*Metrics maintained by [`@joshuakirby`](https://github.com/joshuakirby).
Want a metric added? Open a [Discussion](https://github.com/undercurrentai/AIPEA/discussions)
or PR. Honest small numbers, always.*
