# AIPEA Metrics

> Signals of AIPEA's adoption, usage, and engineering quality. Small
> numbers, honestly reported. Updated 2026-04-23 (post-v1.6.1).

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

## Engineering-quality signals (2026-04-23)

| Metric | Value | Source of truth |
|---|---|---|
| Library version | 1.6.1 | [`pyproject.toml:7`](../pyproject.toml), [PyPI](https://pypi.org/project/aipea/1.6.1/) |
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

Average cadence from v1.3.0 onward: ~1 release/10 days. 9 PyPI releases
over ~10 weeks. Next planned release: v1.6.2 (~2026-05-09) per the
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

### PyPI downloads

Live at [`pypistats.org/packages/aipea`](https://pypistats.org/packages/aipea).
Expect small absolute numbers through 2026 — AIPEA is a B2B library, not a
consumer package. Trajectory matters more than absolute volume; we'll
publish a trailing-30-day trend chart here once we have enough data for
it to be meaningful (~v1.7.0, 2026-06).

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

## What we don't publish (and why)

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

---

*Metrics maintained by [`@joshuakirby`](https://github.com/joshuakirby).
Want a metric added? Open a [Discussion](https://github.com/undercurrentai/AIPEA/discussions)
or PR. Honest small numbers, always.*
