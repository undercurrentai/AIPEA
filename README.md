# AIPEA — AI Prompt Engineer Agent

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-496%20passing-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-90.91%25-brightgreen)]()

A standalone Python library for prompt preprocessing, security screening, query analysis, and context enrichment for LLM systems. Extracted from [Agora IV](https://github.com/undercurrentai/agora-iv) production (v4.1.49).

## Architecture

AIPEA processes prompts through a multi-stage pipeline:

```
User Query → SecurityScanner → QueryAnalyzer → SearchOrchestrator → PromptEngine → Enhanced Prompt
                  │                   │                 │                  │
              PII/PHI scan      Tier routing      Context fetch     Model-specific
              Classification    Domain detect     Knowledge base    prompt formatting
              Injection guard   Complexity score   MCP providers    Tier processing
```

### Core Modules

| Module | Purpose |
|--------|---------|
| `security` | PII/PHI detection, classification markers, injection prevention, compliance modes |
| `analyzer` | Query complexity scoring, domain detection, temporal awareness, tier routing |
| `search` | Multi-provider search orchestration (Exa, Firecrawl, Context7) |
| `knowledge` | Offline knowledge base with SQLite storage and domain-aware retrieval |
| `engine` | Model-specific prompt formatting, tier-based processing (Offline/Tactical/Strategic) |
| `enhancer` | High-level facade coordinating the full pipeline |

### Processing Tiers

| Tier | Latency | Use Case |
|------|---------|----------|
| **Offline** | <2s | Air-gapped, classified, simple queries |
| **Tactical** | 2-5s | Standard queries with search context |
| **Strategic** | 5-15s | Complex research, multi-source synthesis |

## Installation

```bash
# Library only (no CLI)
pip install aipea

# With CLI tools (adds Typer + Rich)
pip install aipea[cli]

# From source (development)
pip install -e ".[dev]"
```

## Configuration

AIPEA can be configured via environment variables, a `.env` file, or `~/.aipea/config.toml`. Priority: env vars > `.env` > global TOML > defaults.

```bash
# Interactive setup wizard (requires [cli] extra)
aipea configure

# Save to global config instead of project .env
aipea configure --global

# Check current configuration
aipea check

# Full diagnostic report
aipea doctor
```

Or configure manually with environment variables:

```bash
export EXA_API_KEY="your-exa-key"
export FIRECRAWL_API_KEY="your-firecrawl-key"
export AIPEA_HTTP_TIMEOUT=30  # seconds (optional)
```

Or create a `.env` file in your project root:

```
EXA_API_KEY="your-exa-key"
FIRECRAWL_API_KEY="your-firecrawl-key"
```

## Usage

### Quick Start — `enhance_prompt`

The simplest way to use AIPEA is through the `enhance_prompt` facade:

```python
import asyncio
from aipea import enhance_prompt

async def main():
    result = await enhance_prompt(
        "What are the latest advances in transformer architectures?",
        model_id="gpt-5.2",
    )
    print(result.enhanced_prompt)
    print(f"Processing tier: {result.processing_tier}")
    print(f"Security context: {result.security_context.security_level}")

asyncio.run(main())
```

### Security Scanning

```python
from aipea import SecurityScanner, SecurityContext, SecurityLevel, ComplianceMode

scanner = SecurityScanner()
context = SecurityContext(
    security_level=SecurityLevel.UNCLASSIFIED,
    compliance_mode=ComplianceMode.HIPAA,
)

# Scan for PII, PHI, classification markers, and injection attempts
result = scanner.scan("Patient John Doe, SSN 123-45-6789, diagnosed with...", context)
print(result.has_pii())       # True
print(result.has_phi())       # True
print(result.is_blocked)      # False (PII is flagged, not blocked)
print(result.flags)           # ["pii_detected:ssn", "phi_detected:diagnosis", ...]
```

### Query Analysis

```python
from aipea import QueryAnalyzer

analyzer = QueryAnalyzer()
analysis = analyzer.analyze("Compare CRISPR-Cas9 efficiency across cell types in 2026 studies")

print(analysis.query_type)          # QueryType.RESEARCH
print(analysis.suggested_tier)      # ProcessingTier.STRATEGIC
print(analysis.complexity)          # 0.85
print(analysis.needs_current_info)  # True (detected temporal reference)
print(analysis.domain_indicators)   # ["biology", "genetics"]
```

### Offline Knowledge Base

```python
import asyncio
from aipea import OfflineKnowledgeBase, StorageTier, KnowledgeDomain

async def main():
    kb = OfflineKnowledgeBase("/path/to/knowledge.db", StorageTier.STANDARD)

    # Add domain knowledge
    await kb.add_knowledge(
        "Transformer attention mechanism computes Q*K^T/sqrt(d_k) for scaled dot-product attention.",
        domain=KnowledgeDomain.TECHNICAL,
    )

    # Search knowledge base
    results = await kb.search("attention mechanism", limit=5)
    for node in results:
        print(f"[{node.relevance_score:.2f}] {node.content[:100]}")

    kb.close()

asyncio.run(main())
```

### Search Orchestration

```python
from aipea import SearchOrchestrator

orchestrator = SearchOrchestrator()

# Multi-provider search with strategy selection
results = await orchestrator.search(
    "quantum error correction 2026",
    strategy="multi_source",
    num_results=10,
)

for result in results.results:
    print(f"[{results.source}] {result.title}: {result.url}")
```

## Integration with Agora IV

AIPEA is vendored into Agora IV at `vendor/aipea/` and re-exported through thin shim modules:

```python
# These imports work in Agora IV (re-export shims)
from aipea_security_context import SecurityScanner, SecurityContext
from pcw_query_analyzer import QueryAnalyzer
from pcw_search_providers import SearchOrchestrator
from pcw_offline_knowledge import OfflineKnowledgeBase
from pcw_prompt_engine import PromptEngine
from aipea_enhancer import enhance_prompt
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run all checks
make all        # format + lint + type check + tests

# Individual commands
make fmt         # Ruff format + auto-fix
make lint        # Ruff check + format check
make type        # mypy strict mode
make test        # pytest with coverage (75% minimum)
make sec         # Security-focused lint rules
make ci          # CI parity (lint + type + test, no autofix)
```

## Testing

```bash
# Full test suite with coverage
pytest tests/ -v --cov=src/aipea --cov-report=term-missing

# Run specific module tests
pytest tests/test_security.py -v
pytest tests/test_analyzer.py -v
pytest tests/test_engine.py -v
```

## License

MIT
