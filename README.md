# AIPEA — AI Prompt Engineer Agent

Prompt preprocessing, security screening, query analysis, and context enrichment for LLM systems.

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

```python
from aipea.security import SecurityScanner, SecurityContext
from aipea.knowledge import OfflineKnowledgeBase, StorageTier
from aipea.search import SearchOrchestrator, SearchStrategy
```

## Testing

```bash
pytest tests/ -v
```
