# AEGIS Adapter for AIPEA

## Overview

AEGIS (AI Ethics Governance & Integrity System) uses AIPEA to preprocess
claims before gate evaluation. The adapter lives in the `aegis-governance`
repo at `src/integration/aipea_bridge.py`.

## Usage

```python
from integration.aipea_bridge import AIPEAGateAdapter

adapter = AIPEAGateAdapter(compliance_mode="general")
claim = await adapter.preprocess_claim("Evaluate this engineering proposal")

# claim.enhanced_claim    → enriched text for gate evaluation
# claim.query_type        → "technical" | "research" | "analytical" | ...
# claim.complexity        → 0.0-1.0 complexity score
# claim.needs_current_info → whether live search is recommended
# claim.search_context    → {"source": ..., "confidence": ..., "result_count": ...} or None
# claim.processing_tier   → "offline" | "tactical" | "strategic"
# claim.enhancement_time_ms → processing latency
```

AIPEA is an optional dependency. When not installed, the adapter returns
passthrough results (original claim text, `query_type="unknown"`,
`complexity=0.5`, `processing_tier="offline"`).

## Field Mapping

| AIPEA Field | AEGIS Field | Usage |
|-------------|-------------|-------|
| `enhanced_prompt` | `enhanced_claim` | Enriched text for gate evaluation |
| `query_analysis.complexity` | `claim_complexity` | Route to appropriate gate depth |
| `query_analysis.needs_current_info` | `requires_live_search` | Trigger evidence gathering |
| `search_context.results` | `background_evidence` | Pre-gathered context |
| `security_context.flags` | `security_flags` | Block unsafe claims |
| `processing_tier` | `preprocessing_tier` | Audit trail |

## When to Use

- **Gate evaluation**: Preprocess claims before research verification
- **Batch processing**: Enrich multiple claims with context before scoring
- **Security screening**: Screen user inputs for PII/injection before processing

## Installation

```bash
# In aegis-governance repo
pip install aipea
```

## Status

**Implemented** — `AIPEAGateAdapter` and `PreprocessedClaim` live in
`aegis-governance/src/integration/aipea_bridge.py` with 9 unit tests.
