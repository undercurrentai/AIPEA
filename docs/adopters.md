# AIPEA Adopters

> Who's using AIPEA, what they use it for, and which version they're
> tested against. Updated 2026-05-02 (post-v1.6.2 ship; Agora IV
> row bumped to v1.6.2 with HTTP_TIMEOUT-deprecation migration note).

AIPEA is young (v1.6.2, shipped 2026-04-24) and maintained by a small team
at [Undercurrent Holdings](https://github.com/undercurrentai). This page
names the adopters we know about. If you're using AIPEA and want to be
listed (or prefer to stay anonymous), open a PR or email
[dev@undercurrentholdings.com](mailto:dev@undercurrentholdings.com).

---

## Named adopters

### Agora IV: internal multi-model AI coordination platform

| | |
|---|---|
| **Role** | Primary extraction source and internal consumer (Undercurrent Holdings' internal platform, not public) |
| **Repo** | `undercurrentai/agora-iv` (private, not publicly accessible) |
| **AIPEA version tested** | v1.6.2 (via shim: `aipea_search_providers.py`, `pcw_query_analyzer.py`, `pcw_prompt_engine.py`, `aipea_security_context.py`, `agora_prompt_enhancement.py`). **Migration note**: Agora IV's 14 `HTTP_TIMEOUT` references continue to work in v1.6.2 but now emit `DeprecationWarning` on first import via PEP 562 `__getattr__`; planned migration to `_resolve_http_timeout()` is scheduled in Agora IV's v4.2.0 cycle. Hard removal lands in AIPEA v2.0.0rc1 (target 2026-09-01). |
| **Integration pattern** | Shim (wildcard re-export) + thin adapter for `enhance_for_agora()`. Preserves 2,187+ AgoraIV tests without import-path churn. |
| **What Agora IV uses AIPEA for** | Security scanning (PII/PHI/injection), query analysis (complexity, domain, temporal needs), model-specific prompt formatting, multi-provider search orchestration (Exa, Firecrawl), and offline knowledge-base retrieval. |
| **Production scale signal** | None publicly verifiable. AIPEA was extracted from the prompt-preprocessing layer of Agora IV v4.1.49, an internal Undercurrent Holdings platform; claims about its internal use cannot be checked by the public. All 20 Wave 18-20 bug-hunt findings (e.g. HIPAA compliance leak #96, ReDoS #107, zero-width Unicode bypass #108) were caught and fixed inside AIPEA before they could affect downstream Agora IV behavior. |
| **Contact** | `@joshuakirby` |

### AEGIS: governance research project (pre-product)

| | |
|---|---|
| **Role** | Downstream consumer via adapter bridge (Undercurrent Holdings' separate governance research project, pre-product) |
| **Repo** | `undercurrentai/aegis-governance` (private). The client SDK is published on PyPI as [`aegis-governance`](https://pypi.org/project/aegis-governance/). |
| **AIPEA version tested** | v1.6.x (optional dependency — AEGIS degrades gracefully to passthrough if AIPEA isn't installed) |
| **Integration pattern** | Direct: AEGIS's private repo contains a `src/integration/aipea_bridge.py` adapter (`AIPEAGateAdapter`) that wraps `enhance_prompt()` and maps AIPEA's fields onto AEGIS's claim-preprocessing contract. AIPEA-side integration tests land in v1.7.0 per the approved roadmap. |
| **What AEGIS uses AIPEA for** | Preprocessing engineering proposals (claims) before gate evaluation: security screening for unsafe claims, complexity scoring for gate routing, evidence-gathering via live search, and audit-trail generation via processing-tier labels. |
| **Production scale signal** | None. AEGIS is pre-product R&D: its hosted evaluation service is not publicly available, with no public signup, API keys, pricing, or paying customers. The AIPEA bridge is internal and not publicly verifiable. |
| **Contact** | `@joshuakirby` |

---

## What "adopter" means here

We list an organization or project as an adopter when **all three** are
true:

1. They import AIPEA (or one of its modules) in their production code
   path, not just in experiments or notebooks.
2. They pin or track a specific AIPEA version in their dependency manifest.
3. They've hit at least one real production-traffic path through AIPEA
   (not just CI / test stubs).

We don't list anonymous PyPI download counts here — for that, see
[`docs/metrics.md`](metrics.md).

---

## Future adopters

AIPEA is MIT-licensed, stdlib + httpx in core, and ships with three
compliance modes (GENERAL / HIPAA / TACTICAL). If you're evaluating it
for a regulated or air-gapped workload, we'd love to talk:

- **GitHub Discussions**: open-office-hours thread
- **Email**: [dev@undercurrentholdings.com](mailto:dev@undercurrentholdings.com)
- **Security-sensitive contact**: see [`SECURITY.md`](../SECURITY.md)

Design-partner outreach for HIPAA / DoD-TACTICAL verticals is an active
BD workstream; if that's a fit for your organization, we'll prioritize
your use case in the v2.0.0+ roadmap.
