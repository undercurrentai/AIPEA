# Agora IV Adapter for AIPEA

## Overview

After AIPEA extraction (Phase 3), AgoraIV consumes AIPEA as a pip dependency.
The existing `agora_prompt_enhancement.py` becomes a thin adapter that wraps
`aipea.AIPEAEnhancer`.

## Migration Plan

### Before (current)

```python
# agora_prompt_enhancement.py imports directly
from aipea_security_context import SecurityScanner, ComplianceHandler, ...
from aipea_search_providers import SearchOrchestrator, ...
from pcw_prompt_engine import PCWPromptEngine, ProcessingTier, ...
from pcw_query_analyzer import PCWQueryAnalyzer, QueryAnalysis, ...
```

### After (post-extraction)

```python
# agora_prompt_enhancement.py wraps AIPEA
from aipea import AIPEAEnhancer, EnhancementResult, EnhancedRequest
from aipea import SecurityLevel, ComplianceMode, ProcessingTier, StorageTier, QueryType

class AgoraPromptEnhancement:
    def __init__(self, ...):
        self._enhancer = AIPEAEnhancer(...)

    async def enhance(self, query, model_id, ...) -> EnhancementResult:
        return await self._enhancer.enhance(query, model_id, ...)
```

### Backward Compatibility Shims

```python
# pcw_query_analyzer.py (shim)
from aipea.analyzer import QueryAnalyzer as PCWQueryAnalyzer
from aipea.analyzer import QueryAnalysis, SearchStrategy
from aipea._types import ProcessingTier, QueryType

# pcw_prompt_engine.py (shim)
from aipea.engine import PromptEngine as PCWPromptEngine
from aipea.engine import SearchContext, EnhancedQuery, ...
from aipea._types import ProcessingTier, QueryType

# aipea_security_context.py (shim)
from aipea.security import *

# aipea_offline_knowledge.py (shim)
from aipea.knowledge import *

# aipea_search_providers.py (shim)
from aipea.search import *
```

## Verification

After migration, run:

```bash
cd /Projects/AgoraIV
make test  # All 2,187+ tests must pass
```

Zero test changes expected — shims preserve all import paths.
