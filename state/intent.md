# AIPEA Intent — What the System SHOULD Do

> Extracted from SPECIFICATION.md sections 1-2 (v1.0.1, 2026-03-09)

## Purpose

AIPEA (AI Prompt Engineer Agent) is a **prompt preprocessing library** that enhances and clarifies natural-language inputs before they reach any AI model. It sits between the user's raw query and the LLM call.

## Core Capabilities

1. **Security screening** — PII/PHI detection, injection prevention, compliance gating
2. **Query analysis** — complexity scoring, temporal detection, domain classification
3. **Context enrichment** — web search results, offline knowledge, model-specific formatting
4. **Prompt formulation** — tiered enhancement from fast templates to multi-step reasoning

## Design Principles (Spec 1.3)

1. **Zero external deps in core** — security, knowledge, search, config import only stdlib (+httpx for search)
2. **Graceful degradation** — search failures return empty results, never exceptions
3. **Security by default** — injection always blocked, PII always scanned
4. **Model-agnostic** — formatting is an output concern, not an architectural dependency

## Core Invariants

- Injection patterns are **always blocked** regardless of compliance mode (8 patterns)
- PII patterns are **always scanned** regardless of compliance mode
- PHI patterns are only scanned in HIPAA mode
- Classified markers are only checked in TACTICAL mode
- SECRET+ security level forces offline processing
- TACTICAL compliance forces offline processing
- Compliance modes restrict model allowlists (HIPAA: BAA-covered, TACTICAL: local only)
- **Global forbidden model list** must block specific models across all modes (spec 3.1.3)

## Processing Tiers

| Tier | Latency | Method |
|------|---------|--------|
| OFFLINE | <2s | Pattern-based, no external calls |
| TACTICAL | 2-5s | LLM-assisted with search context |
| STRATEGIC | 5-15s | Multi-agent reasoning chains |

## Entry Points

- Library: `from aipea import enhance_prompt, AIPEAEnhancer`
- CLI: `aipea configure`, `aipea check`, `aipea doctor`, `aipea info`, `aipea seed-kb`

## Consumers

- Agora IV, AEGIS, future Undercurrent AI products
- AIPEA is product-agnostic (not Agora-specific)
