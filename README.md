# AIPEA — AI Prompt Engineer Agent

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Security Policy](https://img.shields.io/badge/security-policy-brightgreen)](SECURITY.md)
[![CI](https://github.com/undercurrentai/AIPEA/actions/workflows/ci.yml/badge.svg)](https://github.com/undercurrentai/AIPEA/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/undercurrentai/AIPEA/graph/badge.svg)](https://codecov.io/gh/undercurrentai/AIPEA)
[![PyPI](https://img.shields.io/pypi/v/aipea)](https://pypi.org/project/aipea/)
[![Downloads](https://img.shields.io/pypi/dm/aipea)](https://pypi.org/project/aipea/)

A standalone Python library for prompt preprocessing, security screening, query analysis, and context enrichment for LLM systems. Extracted from [Agora IV](https://github.com/undercurrentai/agora-iv) production (v4.1.49).

> **Security:** Report vulnerabilities privately via [GitHub Security Advisories](https://github.com/undercurrentai/AIPEA/security/advisories/new) or email `security@undercurrentholdings.com`. See [`SECURITY.md`](SECURITY.md) for scope, response SLAs, and honest framing of what AIPEA's compliance modes do and do not enforce.

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
| `learning` | Adaptive strategy learning with taint-aware feedback averaging — records user feedback, excludes compliance-tainted input from strategy scoring (ADR-004) |
| `enhancer` | High-level facade coordinating the full pipeline |

### Processing Tiers

| Tier | Latency | Use Case |
|------|---------|----------|
| **Offline** | <2s | Air-gapped, classified, simple queries |
| **Tactical** | 2-5s | Standard queries with search context |
| **Strategic** | 5-15s | Complex research, multi-source synthesis |

### Adoption & metrics

Named adopters and integration patterns → [`docs/adopters.md`](docs/adopters.md).
Live download trajectory, engineering-quality signals, and the honest "not
yet published" list → [`docs/metrics.md`](docs/metrics.md).
Production narrative (Wave 18-20 hardening) → [`case-studies/agora-iv-v1.md`](case-studies/agora-iv-v1.md).

## Installation

```bash
# Library only (no CLI)
pip install aipea

# With CLI tools (adds Typer + Rich)
pip install aipea[cli]

# From source (development)
pip install -e ".[dev]"
```

## Getting Started

AIPEA works out of the box with zero configuration. API keys and Ollama are entirely optional — they unlock richer enhancement when available.

**Path 1: Minimal (no setup needed)**

```bash
pip install aipea
```

```python
from aipea import enhance_prompt
result = await enhance_prompt("What is quantum computing?", model_id="gpt-4")
# Works immediately with template-based enhancement — no API keys required
```

**Path 2: With Search Providers (real-time web context)**

[Exa](https://exa.ai) provides AI-powered web search; [Firecrawl](https://firecrawl.dev) provides structured web content retrieval. Both offer free tiers.

```bash
pip install aipea[cli]
aipea configure          # interactive wizard — press Enter to skip any key
```

**Path 3: With Ollama (local LLM enhancement)**

Ollama runs open-source LLMs locally for richer offline enhancement. AIPEA auto-detects it when available.

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a lightweight model
ollama pull gemma3:1b

# Populate the offline knowledge base
aipea seed-kb
```

Run `aipea doctor` at any time to see what capabilities are active and what you can add.

## Configuration

All API keys are optional. AIPEA can be configured via environment variables, a `.env` file, or `~/.aipea/config.toml`. Priority: env vars > `.env` > global TOML > defaults.

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
    for node in results.nodes:
        print(f"[{node.relevance_score:.2f}] {node.content[:100]}")

    kb.close()

asyncio.run(main())
```

### Search Orchestration

```python
import asyncio
from aipea import SearchOrchestrator

async def main():
    orchestrator = SearchOrchestrator()

    # Multi-provider search with strategy selection
    results = await orchestrator.search(
        "quantum error correction 2026",
        strategy="multi_source",
        num_results=10,
    )

    for result in results.results:
        print(f"[{results.source}] {result.title}: {result.url}")

asyncio.run(main())
```

### Adaptive Learning (opt-in)

AIPEA can learn from user feedback to improve strategy selection over time. This is opt-in and uses a local SQLite database — no data leaves your machine.

```python
import asyncio
from aipea import AIPEAEnhancer

async def main():
    enhancer = AIPEAEnhancer(enable_learning=True)

    # Enhance a query — strategy_used is tracked on the result
    result = await enhancer.enhance(
        "How do transformer attention mechanisms work?",
        model_id="claude-opus-4-6",
    )
    print(result.strategy_used)  # e.g. "technical"

    # Record user feedback (positive = good enhancement)
    await enhancer.record_feedback(result, score=0.9)

    # After enough feedback (3+ per strategy), AIPEA uses the
    # historically best-performing strategy for each query type.
    # The next enhance() call may use a different strategy if
    # the learning engine has accumulated better data.

    enhancer.close()

asyncio.run(main())
```

The learning engine stores data in `aipea_learning.db` (configurable via `AIPEA_LEARNING_DB_PATH`). If the database is unavailable, AIPEA falls back to default strategy selection with no error.

#### Compliance-Aware Learning (v1.5.0+)

For regulated deployments, `LearningPolicy` controls which compliance modes may persist feedback:

```python
from aipea import AIPEAEnhancer, LearningPolicy

# HIPAA deployment with opt-in learning + retention limits
policy = LearningPolicy(
    allow_hipaa_recording=True,   # HIPAA: default-deny, must opt in
    retention_days=365,           # Auto-prune events older than 1 year
    max_events=10000,             # Cap total stored events
)
enhancer = AIPEAEnhancer(
    enable_learning=True,
    learning_policy=policy,
)

# TACTICAL mode always blocks recording (hard invariant, no override)
# GENERAL mode records as before (no policy needed)

# Enforce retention limits explicitly
enhancer._learning_engine.prune_events()
```

| Compliance Feature | Behavior |
|---|---|
| TACTICAL mode | Never records (hard invariant) |
| HIPAA mode | Blocks by default; opt in via `allow_hipaa_recording=True` |
| GENERAL mode | Records normally |
| Tainted feedback handling | Recorded for audit, excluded from averaging by default |

**Taint-aware averaging (v1.6.0+):** Feedback on queries that fired compliance-relevant scanner flags (PII/PHI/classified/injection) is recorded to the audit log but excluded from strategy-performance averaging by default. This prevents feedback poisoning attacks (OWASP LLM Top 10 2026 LLM03). Opt into inclusion via `LearningPolicy(exclude_tainted_from_averaging=False)`.

## Integration

AIPEA is designed as a standalone preprocessing layer for LLM systems. It integrates with:

- **[AEGIS Governance](https://github.com/undercurrentai/aegis-governance)** — engineering standards & compliance SDK (`pip install aegis-governance[aipea]`)
- **Agora IV** — multi-model orchestration platform (uses AIPEA for prompt preprocessing)

## Enterprise & Governance

AIPEA is free and open-source. For organizations that need full AI governance — risk registers, model cards, compliance auditing, and policy enforcement — see [AEGIS](https://github.com/undercurrentai/aegis-governance), Undercurrent AI's governance platform.

### What AIPEA's Compliance Modes Do — and Do Not Do

AIPEA exposes a `ComplianceMode` enum with three supported modes (`GENERAL`, `HIPAA`, `TACTICAL`). These modes are **input-inspection and model-allowlist controls**, not enforcement of any regulatory regime. Read this before shipping AIPEA into a regulated environment:

| Mode | What AIPEA does | What AIPEA does **not** do |
|---|---|---|
| `GENERAL` | Default. PII scanning, injection detection, and homoglyph normalization run for every request. | — |
| `HIPAA` | Enables PHI regex patterns (MRN, patient identifier, diagnosis-term detection); restricts the LLM allowlist to BAA-capable models; emits `phi_detected:*` flags in the scan result; logs a runtime warning on match. | Does not redact. Does not block the prompt. Does not persist an audit trail. Does not satisfy the HIPAA Security Rule, Privacy Rule, or BAA requirement on behalf of the integrator. |
| `TACTICAL` | Forces the processing tier to Offline; restricts the LLM allowlist to locally-runnable models; enables classified-marker regex patterns (CONFIDENTIAL / SECRET / TOP SECRET and common compartment markings). | Does not validate an air-gap. Does not enforce classification handling beyond detection. Does not substitute for an accredited tactical enclave. |

**Responsibility stays with the integrator.** AIPEA is an input-inspection layer: it tells you what it saw. Your application is responsible for the enforcement decision (block, redact, route to a compliant backend, log to an immutable audit store, obtain BAAs, encrypt at rest and in transit, and satisfy whatever regulatory regime applies).

> **Deprecated: `ComplianceMode.FEDRAMP`.** AIPEA previously exposed a FedRAMP enum value. That mode was always a config-only stub with no behavioral enforcement. As of v1.3.4 it is formally deprecated — constructing a `ComplianceHandler` with `FEDRAMP` emits a `DeprecationWarning` — and scheduled for removal in v2.0.0. AIPEA does not implement FedRAMP controls; integrators needing FedRAMP should migrate to `ComplianceMode.GENERAL` and implement FedRAMP controls in their own application layer. Decision rationale: [`docs/adr/ADR-002-fedramp-removal.md`](docs/adr/ADR-002-fedramp-removal.md).

For the full scope statement, supported versions, and vulnerability disclosure policy, see [`SECURITY.md`](SECURITY.md).

AEGIS adds the organizational layer that AIPEA deliberately does not: audit trails, human oversight workflows, policy enforcement, and regulatory reporting. If you need those, pair AIPEA with AEGIS rather than treating AIPEA's compliance modes as substitutes for them.

Learn more at [undercurrentholdings.com](https://undercurrentholdings.com).

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
