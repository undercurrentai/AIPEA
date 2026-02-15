# AEGIS Adapter for AIPEA

## Overview

AEGIS (AI Ethics Governance & Integrity System) can use AIPEA to preprocess
claims before gate evaluation. This adapter lives in the `aegis-governance`
repo, not in AIPEA.

## Integration Pattern

```python
from aipea import enhance_prompt, EnhancementResult, ComplianceMode

class AIPEAGateAdapter:
    """Preprocesses claims through AIPEA before gate evaluation."""

    def __init__(self, compliance_mode: str = "general"):
        self.compliance_mode = ComplianceMode(compliance_mode)

    async def preprocess_claim(
        self,
        claim_text: str,
        model_id: str = "claude-opus-4-6",
    ) -> dict:
        """Enhance a claim through AIPEA before gate evaluation.

        Returns a dict suitable for feeding into AEGIS gate input.
        """
        result: EnhancementResult = await enhance_prompt(
            query=claim_text,
            model_id=model_id,
            compliance_mode=self.compliance_mode,
        )

        return {
            "enhanced_claim": result.enhanced_prompt,
            "query_type": result.query_analysis.query_type.value,
            "complexity": result.query_analysis.complexity,
            "needs_current_info": result.query_analysis.needs_current_info,
            "search_context": (
                {
                    "source": result.search_context.source,
                    "confidence": result.search_context.confidence,
                    "result_count": len(result.search_context.results),
                }
                if result.search_context
                else None
            ),
            "security_flags": [f for f in (result.security_context.to_dict() if hasattr(result.security_context, 'to_dict') else {})],
            "processing_tier": result.processing_tier.value,
            "enhancement_time_ms": result.enhancement_time_ms,
        }
```

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

This is a **specification only**. The adapter code will be written when
AEGIS integration is scheduled.
