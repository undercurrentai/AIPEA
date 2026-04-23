# AIPEA Specification
> **AI Prompt Engineer Agent** | Version 1.6.0 | 2026-04-15

```yaml
status: ACCEPTED
classification: INTERNAL
maintainer: joshuakirby
origin: AgoraIV production (v4.1.49) + Agora V design reference
license: MIT
```

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Core Modules (Proven)](#3-core-modules-proven)
4. [Enhancement Engine](#4-enhancement-engine)
5. [Integration Contracts](#5-integration-contracts)
6. [Processing Tiers](#6-processing-tiers)
7. [Security & Compliance](#7-security--compliance)
8. [Configuration & Deployment](#8-configuration--deployment)
9. [Intentional Descopes](#9-intentional-descopes)
10. [Future Roadmap](#10-future-roadmap)
11. [API Reference](#11-api-reference)

---

## 1. Executive Summary

### 1.1 What AIPEA Is

AIPEA (AI Prompt Engineer Agent) is a **prompt preprocessing library** that enhances
and clarifies natural-language inputs before they reach any AI model. It sits between
the user's raw query and the LLM call, adding:

- **Security screening** — PII/PHI detection, injection prevention, compliance gating
- **Query analysis** — complexity scoring, temporal detection, domain classification
- **Context enrichment** — web search results, offline knowledge, model-specific formatting
- **Prompt formulation** — tiered enhancement from fast templates to multi-step reasoning

AIPEA ships as a **Python library** (`pip install aipea`). Consumer systems (Agora,
AEGIS, or any future product) import it and call a single function:

```python
from aipea import enhance_prompt

result = await enhance_prompt(
    query="What are the latest advances in quantum error correction?",
    model_id="claude-opus-4-6",
)
print(result.enhanced_prompt)  # Enriched prompt ready for the model
```

### 1.2 Who It Serves

| Consumer | Use Case |
|----------|----------|
| **Agora IV** | Multi-model conversation orchestration — enhances queries before dispatching to 3+ LLMs |
| **AEGIS** | Gate evaluation preprocessing — enriches claims before research verification |
| **CLI tools** | Any command-line AI assistant that benefits from smarter prompts |
| **Future products** | Any Undercurrent system that calls an LLM |

### 1.3 Design Principles

These principles are drawn from 15 bug-hunt waves and 47 quality gates on the
production Agora IV codebase:

1. **Zero external dependencies in core** — The 3 core modules (`security`, `knowledge`,
   `search`) import only stdlib + `httpx`. No framework lock-in.
2. **Graceful degradation** — Every search call returns empty results on failure, never
   exceptions. Every tier falls back to the one below.
3. **Security by default** — Injection patterns are always blocked regardless of
   compliance mode. PII scanning is always on. Classified content forces offline.
4. **Model-agnostic** — Works with any LLM. Model-specific formatting is an output
   concern, not an architectural dependency.
5. **Air-gap ready** — Tier 0 (Offline) operates with zero network connectivity,
   using SQLite + zlib compression + optional Ollama SLMs.
6. **Production-proven** — Every class, method, and pattern in this spec has been
   deployed and tested in AgoraIV (2,187 passed + 1 skipped, 77.99% coverage, v4.1.49).

### 1.4 Provenance

AIPEA was designed in **Agora V/AIPEA/** (9 files, ~8,200 LOC) as a comprehensive
autonomous agent system. A production subset was built and shipped in **AgoraIV**
as 6 modules (~4,700 LOC). This specification:

- Preserves everything that shipped and works
- Documents what was intentionally descoped and why
- Defines the extraction path from AgoraIV into a standalone library
- Plans future enhancements informed by both the original design and production learnings

---

## 2. Architecture Overview

### 2.1 System Context

```
                    ┌─────────────────────────────────┐
                    │         Consumer System          │
                    │  (Agora, AEGIS, CLI, Future...)  │
                    └───────────┬─────────────────────┘
                                │ enhance(query, model_id, ...)
                                ▼
                    ┌─────────────────────────────────┐
                    │           AIPEA Library          │
                    │                                  │
                    │  ┌──────────┐  ┌─────────────┐  │
                    │  │ Security │  │  Analyzer    │  │
                    │  │ Scanner  │  │  (routing)   │  │
                    │  └────┬─────┘  └──────┬──────┘  │
                    │       │               │         │
                    │  ┌────▼───────────────▼──────┐  │
                    │  │      Enhancement Engine    │  │
                    │  │  (tiered prompt formulation)│  │
                    │  └────┬──────────────┬───────┘  │
                    │       │              │          │
                    │  ┌────▼────┐   ┌─────▼──────┐  │
                    │  │ Offline │   │   Search    │  │
                    │  │   KB    │   │ Providers   │  │
                    │  └─────────┘   └────────────┘  │
                    └─────────────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────────────────┐
                    │      EnhancementResult           │
                    │  (enhanced_prompt, metadata)     │
                    └─────────────────────────────────┘
```

### 2.2 Module Dependency Graph

```
aipea/
├── security.py          # ZERO imports from other aipea modules
├── knowledge.py         # ZERO imports from other aipea modules
├── search.py            # ZERO imports from other aipea modules (only httpx)
├── config.py            # ZERO imports from other aipea modules (stdlib only)
├── quality.py           # ZERO imports from other aipea modules (stdlib only)
├── strategies.py        # Imports: _types.py (QueryType enum only)
├── learning.py          # Imports: _types.py (QueryType), security.py (ComplianceMode)
├── _types.py            # Shared enums (ProcessingTier, QueryType, SearchStrategy)
├── models.py            # Shared data models (QueryAnalysis)
├── analyzer.py          # Imports: security.py, _types.py
├── engine.py            # Imports: search.py, _types.py; lazy-imports strategies.py
├── enhancer.py          # Imports: ALL above (facade); lazy-imports learning.py
├── cli.py               # Imports: config.py, aipea (requires [cli] extra)
└── __main__.py          # Entry point: python -m aipea
```

Key insight: The 3 core modules form an **independent base layer** with zero
cross-dependencies. This is not accidental — it was validated across 15 bug hunts
and enables the modules to be tested, deployed, and consumed independently.

### 2.3 Data Flow

```
User Query
    │
    ▼
[1] SecurityScanner.scan(query, context)
    │
    ├─ BLOCKED → return blocked result
    │
    ▼
[2] QueryAnalyzer.analyze(query, security_context)
    │  → QueryAnalysis(type, complexity, tier, search_strategy)
    │
    ▼
[3] Route: offline or online?
    │
    ├─ OFFLINE (classified, tactical, no connectivity)
    │  → OfflineKnowledgeBase.search(query, domain)
    │
    ├─ ONLINE
    │  → SearchOrchestrator.search(query, strategy)
    │
    ▼
[4] PromptEngine.formulate(query, complexity, context, model_type)
    │
    ▼
[5] EnhancementResult
    (enhanced_prompt, processing_tier, security_context,
     query_analysis, search_context, timing, notes)
```

### 2.4 Package Structure

```
aipea/                           # pip install aipea
├── __init__.py                  # Public API: enhance_prompt(), AIPEAEnhancer, types
├── security.py                  # SecurityScanner, ComplianceHandler, SecurityContext
├── knowledge.py                 # OfflineKnowledgeBase, KnowledgeNode, StorageTier
├── search.py                    # SearchOrchestrator, ExaProvider, FirecrawlProvider
├── analyzer.py                  # QueryAnalyzer, QueryRouter, QueryAnalysis
├── engine.py                    # PromptEngine, TierProcessors, Ollama client
├── enhancer.py                  # AIPEAEnhancer facade (main entry point)
├── models.py                    # QueryAnalysis (shared data model)
├── _types.py                    # ProcessingTier, QueryType, SearchStrategy, etc.
├── config.py                    # AIPEAConfig, load_config (stdlib-only config system)
├── cli.py                       # CLI commands: configure, check, doctor, info
└── __main__.py                  # python -m aipea entry point
```

---

## 3. Core Modules (Proven)

These three modules are **production-proven** with zero Agora dependencies.
They are extracted verbatim from AgoraIV and form AIPEA's independent base layer.

### 3.1 Security Context (`security.py`)

**Source**: `aipea_security_context.py` (637 LOC in AgoraIV)
**Dependencies**: stdlib only (`re`, `logging`, `dataclasses`, `enum`)
**Test coverage**: 49 tests across 3 test files *(AgoraIV extraction baseline; see CI for current)*

#### 3.1.1 Enums

```python
class SecurityLevel(Enum):
    """Security classification levels."""
    UNCLASSIFIED = 0   # Public/general information
    SENSITIVE = 1      # General business sensitive
    CUI = 2            # Controlled Unclassified Information
    SECRET = 3         # Classified — requires clearance
    TOP_SECRET = 4     # Highest classification

class ComplianceMode(Enum):
    """Regulatory compliance modes. Supported: GENERAL, HIPAA, TACTICAL.
    FEDRAMP is deprecated (ADR-002) and scheduled for removal in v2.0.0.
    """
    GENERAL = "general"    # Standard use — minimal restrictions
    HIPAA = "hipaa"        # Medical/PHI handling — BAA-covered models
    TACTICAL = "tactical"  # Military/Defense — local models only, air-gapped
    FEDRAMP = "fedramp"    # DEPRECATED — config-only stub, see ADR-002
```

#### 3.1.2 SecurityScanner

Scans queries for 4 categories of security-sensitive content:

| Category | Patterns | Behavior |
|----------|----------|----------|
| **PII** | SSN, credit card, API key, password | Flag (always checked) |
| **PHI** | MRN, DOB, patient name | Flag (HIPAA mode only) |
| **Classified markers** | TOP SECRET, SECRET, NOFORN, SCI | Flag + force offline (TACTICAL only) |
| **Injection** | SQL injection, XSS, prompt injection, template injection, bracket-style role tags | **Block** (always) |

Key production learnings baked in:
- **ReDoS protection**: Custom patterns validated against catastrophic backtracking
  before execution. Patterns exceeding 200 chars or containing nested quantifiers
  are rejected. Hardcoded `INJECTION_PATTERNS` are also self-validated at
  `SecurityScanner.__init__` time via the same checks (defense-in-depth).
- **Word-boundary matching**: Classified markers use `\b` word boundaries to prevent
  false positives (e.g., "SECRET" in "SECRETARY").
- **Immutable input**: Scanner no longer mutates the input `SecurityContext` — it
  returns `force_offline` as a field on `ScanResult` instead.

```python
class ScanResult:
    flags: list[str]        # e.g., ["pii_detected:ssn", "injection_attempt"]
    is_blocked: bool        # True if query should be rejected
    force_offline: bool     # True if classified content detected

    def has_pii(self) -> bool: ...
    def has_phi(self) -> bool: ...
    def has_classified_content(self) -> bool: ...
    def has_injection_attempt(self) -> bool: ...
```

#### 3.1.3 ComplianceHandler

Configures operational parameters per compliance mode:

| Mode | Audit Retention | Encryption | Allowed Models | PHI Redaction | Force Offline |
|------|----------------|------------|----------------|---------------|---------------|
| GENERAL | 90 days | No | All | No | No |
| HIPAA | 6 years (2190d) | Yes | claude-opus-4-6, gpt-5.2 (BAA-covered) | Yes | No |
| TACTICAL | 7 years (2555d) | Yes | llama-3.3-70b (local only) | No | Yes |

**Deprecated:** `FEDRAMP` previously appeared in this table. It was always a config-only stub with no behavioral enforcement and has been formally deprecated in v1.3.4 (removal scheduled for v2.0.0). See [`docs/adr/ADR-002-fedramp-removal.md`](docs/adr/ADR-002-fedramp-removal.md).

Model validation uses **substring matching** (case-insensitive) against the allowed
list, plus a global **forbidden list** (`gpt-4o`, `gpt-4o-mini`) that applies
regardless of mode. The forbidden list is enforced via `GLOBAL_FORBIDDEN_MODELS`
class variable, checked **before** mode-specific allowlists in `validate_model()`.

#### 3.1.4 Convenience Functions

```python
def create_security_context_for_mode(mode, has_connectivity=True, data_residency=None) -> SecurityContext
def quick_scan(query, mode=ComplianceMode.GENERAL) -> ScanResult
```

### 3.2 Offline Knowledge Base (`knowledge.py`)

**Source**: `aipea_offline_knowledge.py` (711 LOC in AgoraIV)
**Dependencies**: stdlib only (`sqlite3`, `zlib`, `hashlib`, `threading`, `pathlib`)
**Test coverage**: 28 tests *(AgoraIV extraction baseline; see CI for current)*

#### 3.2.1 Purpose

Provides **completely offline** knowledge storage for air-gapped environments:
submarines, classified facilities, field operations, no-signal areas. Zero network
calls — SQLite is the only storage backend.

#### 3.2.2 Knowledge Domains

```python
class KnowledgeDomain(Enum):
    MILITARY = "military"
    TECHNICAL = "technical"
    MEDICAL = "medical"
    INTELLIGENCE = "intelligence"
    LOGISTICS = "logistics"
    COMMUNICATIONS = "communications"
    CYBERSECURITY = "cybersecurity"
    ENGINEERING = "engineering"
    GENERAL = "general"
```

#### 3.2.3 Storage Tiers

| Tier | Capacity | Target Device |
|------|----------|---------------|
| ULTRA_COMPACT | 1 GB | Phones, IoT |
| COMPACT | 5 GB | Tablets |
| STANDARD | 20 GB | Laptops |
| EXTENDED | 100 GB | Workstations |

#### 3.2.4 Core Operations

```python
class OfflineKnowledgeBase:
    def __init__(self, db_path="aipea_knowledge.db", tier=StorageTier.STANDARD)

    async def add_knowledge(content, domain, classification="UNCLASSIFIED", relevance_score=0.5) -> str
    async def search(query, domain=None, limit=5) -> KnowledgeSearchResult
    async def get_by_id(node_id) -> KnowledgeNode | None
    async def update_relevance(node_id, new_score) -> bool
    async def delete_node(node_id) -> bool
    async def get_node_count() -> int
    async def get_storage_stats() -> dict
    async def get_domains_summary() -> dict[str, int]
    async def prune_low_relevance(threshold=0.1, max_delete=100) -> int
```

Key implementation details:
- **Compression**: zlib level 9 for all content. Typical 3-5x compression ratio.
- **Content-addressed IDs**: First 16 chars of SHA256 hash of content.
- **Thread safety**: `threading.RLock` protects all database operations.
  `check_same_thread=False` enables multi-thread access.
- **Access tracking**: Every `search()` call increments `access_count` and updates
  `last_accessed` for retrieved nodes.
- **Context manager**: Supports `with` statement for clean connection lifecycle.
- **Seed data**: `SEED_KNOWLEDGE` (20 entries across 7 domains) provides baseline
  knowledge for offline mode. Populated via `seed_knowledge_base(kb)` helper or
  `aipea seed-kb` CLI command.

#### 3.2.5 Schema

```sql
CREATE TABLE knowledge_nodes (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    compressed_content BLOB NOT NULL,
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP,
    relevance_score REAL DEFAULT 0.5,
    security_classification TEXT DEFAULT 'UNCLASSIFIED',
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_knowledge_domain ON knowledge_nodes(domain);
CREATE INDEX idx_knowledge_relevance ON knowledge_nodes(relevance_score DESC);
CREATE INDEX idx_knowledge_domain_relevance ON knowledge_nodes(domain, relevance_score DESC);
```

### 3.3 Search Providers (`search.py`)

**Source**: `aipea_search_providers.py` (1,071 LOC in AgoraIV)
**Dependencies**: stdlib + `httpx`
**Test coverage**: 42 tests *(AgoraIV extraction baseline; see CI for current)*

#### 3.3.1 Provider Architecture

All providers implement a common ABC:

```python
class SearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, num_results: int = 5) -> SearchContext: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...
```

#### 3.3.2 Providers

| Provider | API | Key Feature | Env Var |
|----------|-----|-------------|---------|
| **ExaSearchProvider** | `api.exa.ai/search` | Neural semantic search | `EXA_API_KEY` |
| **FirecrawlProvider** | `api.firecrawl.dev/v1/search` | Deep research + scraping | `FIRECRAWL_API_KEY` |
| **Context7Provider** | MCP (development-time) | Library documentation | N/A (returns empty) |

**Context7 design note**: Context7 is an MCP server invoked by Claude Code at
development time, not from Python runtime. The provider exists to satisfy the
`SearchProvider` interface uniformly but intentionally returns empty results.
This is by design, not a limitation.

#### 3.3.3 SearchOrchestrator

Combines providers via strategy selection:

| Strategy | Providers Used | Use Case |
|----------|---------------|----------|
| `quick_facts` | Exa only | Fast factual lookup |
| `deep_research` | Firecrawl deep research | Complex multi-source analysis |
| `multi_source` | Exa + Firecrawl merged | Cross-reference verification |

```python
class SearchOrchestrator:
    async def search(query, strategy="quick_facts", num_results=5) -> SearchContext
    async def search_technical(query, num_results=5) -> SearchContext
    def get_provider_status() -> dict[str, bool]
```

#### 3.3.4 Model-Specific Formatting

`SearchContext.formatted_for_model(model_type)` produces optimized output:

| Model Family | Format Style |
|-------------|-------------|
| OpenAI/GPT | Markdown with `#` headers and `**bold**` sections |
| Anthropic/Claude | XML tags (`<search_context>`, `<source>`, etc.) with HTML escaping |
| Gemini/Generic | Simple numbered list |

#### 3.3.5 Key Data Models

```python
@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    score: float = 0.0      # 0.0-1.0, clamped in __post_init__

@dataclass
class SearchContext:
    query: str
    results: list[SearchResult]
    timestamp: datetime
    source: str = "unknown"
    confidence: float = 0.0  # 0.0-1.0, clamped

    def is_empty(self) -> bool: ...
    def formatted_for_model(self, model_type: str) -> str: ...
    def merge_with(self, other: SearchContext) -> SearchContext: ...
```

---

## 4. Enhancement Engine

The enhancement engine combines query analysis, prompt formulation, and tiered
processing. In AgoraIV, these live across `pcw_query_analyzer.py` (961 LOC),
`pcw_prompt_engine.py` (1,685 LOC), and `agora_prompt_enhancement.py` (1,034 LOC).

### 4.1 Query Analyzer (`analyzer.py`)

**Source**: `pcw_query_analyzer.py` (renamed from `PCWQueryAnalyzer` to `QueryAnalyzer`)

#### 4.1.1 Query Classification

Pattern-matching classifier that scores queries against 6 types:

| Type | Example Patterns |
|------|-----------------|
| TECHNICAL | code, API, function, python, database, implement |
| RESEARCH | research, study, paper, analysis, evidence |
| CREATIVE | create, design, write, story, imagine |
| ANALYTICAL | analyze, evaluate, compare, problem, metrics |
| OPERATIONAL | how to, steps, procedure, install, guide |
| STRATEGIC | plan, strategy, roadmap, decision, forecast |
| UNKNOWN | (fallback when no patterns match) |

#### 4.1.2 Complexity Scoring

Composite score (0.0-1.0) based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| Base | 0.1 | Minimum complexity floor |
| Sentence count | +0.1/sentence (max 0.3) | Multiple sentences indicate complexity |
| Conditional patterns | +0.1 each | if/then, compare, explain why, etc. |
| Word count > 50 | +0.1 | Longer queries are more complex |
| Word count > 100 | +0.2 | Very long queries are significantly more complex |

The base was lowered from 0.3 to 0.1 (QG38-D6) to give OFFLINE tier a usable
[0.1, 0.3] routing band.

#### 4.1.3 Temporal Detection

5 pattern groups detect current-information needs:

```
latest|recent|current|today|now|this week|this month|this year
breaking|news|update|happening
20[2-9][0-9]                          # Years 2020-2099
yesterday|tomorrow|last week|last month|last year
upcoming|forthcoming|scheduled|planned
```

#### 4.1.4 Domain Detection

5 domain pattern groups (medical, legal, technical, financial, military) enable
specialized routing. Cross-domain queries (2+ domains) reduce confidence and
may trigger tier escalation.

#### 4.1.5 Search Strategy Selection

```
needs_current_info → QUICK_FACTS (default)
comparative terms  → MULTI_SOURCE
verification terms → MULTI_SOURCE
research + complex → DEEP_RESEARCH
complexity > 0.7   → DEEP_RESEARCH
otherwise          → QUICK_FACTS
```

#### 4.1.6 QueryAnalysis Result

```python
@dataclass
class QueryAnalysis:
    query: str
    query_type: QueryType
    complexity: float              # 0.0-1.0
    confidence: float              # 0.0-1.0
    needs_current_info: bool
    temporal_markers: list[str]
    domain_indicators: list[str]
    ambiguity_score: float         # 0.0-1.0
    detected_entities: list[str]
    suggested_tier: ProcessingTier | None
    search_strategy: SearchStrategy
```

### 4.2 Prompt Engine (`engine.py`)

**Source**: `pcw_prompt_engine.py` (renamed from `PCWPromptEngine` to `PromptEngine`)

#### 4.2.1 Three-Tier Processing

| Tier | Class | Latency | Confidence | Mechanism |
|------|-------|---------|------------|-----------|
| **OFFLINE** | `OfflineTierProcessor` | <2s | 0.70-0.82 | Pattern matching + templates, optional Ollama SLMs |
| **TACTICAL** | *(removed — see Note)* | — | — | — |
| **STRATEGIC** | *(removed — see Note)* | — | — | — |

> **Note (v1.2.0)**: `TacticalTierProcessor` and `StrategicTierProcessor` were removed as dead code.
> The enhancer bypassed both classes, routing directly to `formulate_search_aware_prompt()`.
> Enhancement depth is now determined by query complexity labeling and search routing,
> not by tier processor classes. The tier *labels* (OFFLINE, TACTICAL, STRATEGIC) remain
> as `ProcessingTier` enum values for metadata and routing purposes.

#### 4.2.2 Offline Tier (Tier 0)

Two modes:

1. **Template mode** (no Ollama): Pattern-classifies query → applies typed template
   with structured instructions. 7 templates (one per QueryType).

2. **Ollama mode** (with local SLMs): Uses pre-downloaded models for real inference.

| Model | Size | Params | Use Case |
|-------|------|--------|----------|
| `gemma3:270m` | 291 MB | 270M | Ultra-lightweight, edge devices |
| `gemma3:1b` | 815 MB | 1B | Lightweight, good quality/size tradeoff |
| `phi3:mini` | 2.2 GB | 3.8B | Higher quality, preferred when available |
| `gpt-oss-20b` | ~11 GB | 20B | Future: higher quality |
| `llama-3.3-70b` | ~40 GB | 70B | Future: highest quality |

Ollama integration:
- Models checked once per session (`_check_ollama_availability`)
- Prompt passed via stdin (prevents command injection)
- 60-second timeout, 128KB max prompt
- Falls back to templates on any failure

#### 4.2.3 Tactical Tier (Tier 1)

Enhances prompt with:
- Structured instruction template
- Search context integration (formatted for model type)
- Optional LLM disambiguation via orchestrator (if available)

#### 4.2.4 Strategic Tier (Tier 2)

When an orchestrator is available, executes a 4-step reasoning chain:

1. **Decompose**: LLM breaks query into 2-4 sub-questions
2. **Parallel analyze**: Each sub-question analyzed concurrently
3. **Synthesize**: Results merged into cohesive response
4. **Critique loop**: Up to 3 rounds of critique → refine until "APPROVED"

Without an orchestrator, falls back to a structured strategic template built
on top of the tactical result.

#### 4.2.5 Model-Specific Prompt Optimization

```python
async def formulate_search_aware_prompt(query, complexity, search_context, model_type, query_type=None) -> str
async def create_model_specific_prompt(base_prompt, model_type, search_context) -> str
```

Current date injection for temporal awareness:
```
Today's date is 2026-02-14 (year 2026).
```

Complexity instructions (simple/medium/complex) + model-specific style guidance
(structured for GPT, nuanced for Claude, comprehensive for Gemini).

### 4.3 Named Enhancement Strategies (v1.3.0)

The `strategies.py` module implements 6 named strategies with 6 pure-function
techniques. Strategies are selected automatically by `QueryType` or specified
explicitly via the `strategy` parameter on `enhance()` and `enhance_prompt()`.

**Strategies** (all shipped in v1.3.0):

| Strategy | Techniques | Auto-selected for |
|----------|-----------|-------------------|
| general | specification_extraction, constraint_identification | UNKNOWN |
| technical | specification_extraction, constraint_identification, metric_definition, task_decomposition | TECHNICAL, OPERATIONAL |
| research | specification_extraction, hypothesis_clarification, metric_definition | RESEARCH |
| creative | specification_extraction, hypothesis_clarification | CREATIVE |
| analytical | specification_extraction, constraint_identification, metric_definition, task_decomposition | ANALYTICAL |
| strategic | specification_extraction, constraint_identification, objective_hierarchy_construction, task_decomposition | STRATEGIC |

**Techniques** (pure functions, stdlib only):

| Technique | Purpose |
|-----------|---------|
| `specification_extraction` | Extract implicit requirements (comparisons, evaluations, implementations) |
| `constraint_identification` | Identify time, resource, scope, and technology constraints |
| `hypothesis_clarification` | Reformulate vague qualifiers and generalizations |
| `metric_definition` | Define measurable success criteria (performance, quality, scale) |
| `task_decomposition` | Break multi-concern queries into sub-tasks |
| `objective_hierarchy_construction` | Build goal trees for strategic/planning queries |

### 4.4 Quality Assessor (v1.3.0)

The `quality.py` module provides heuristic quality scoring for prompt
enhancements. `QualityAssessor.assess(original, enhanced)` returns a
`QualityScore` with 4 sub-scores and a weighted composite.

```python
from aipea.quality import QualityAssessor

score = QualityAssessor().assess(original_query, enhanced_prompt)
# score.clarity_improvement   — readability delta (0.0–1.0)
# score.specificity_gain      — unique content-word growth (0.0–1.0)
# score.information_density   — content-word ratio delta (0.0–1.0)
# score.instruction_quality   — step markers + constraint keywords (0.0–1.0)
# score.overall               — weighted composite (0.0–1.0)
```

Weights: clarity 0.25, specificity 0.30, density 0.20, instruction 0.25.

Quality scores are computed automatically in `enhance()` and attached to
`EnhancementResult.quality_score`.

### 4.5 Dialogical Clarification (v1.3.0)

`EnhancementResult.clarifications` provides advisory clarifying questions
(max 3) for ambiguous queries. The enhancement still proceeds best-effort.

Clarification triggers:
- `ambiguity_score > 0.6` → "Could you be more specific...?"
- No detected entities → "What specific [domain] topic...?"
- High complexity + no search strategy → "Summary or deep dive?"
- Short query (< 4 words) → "Could you provide more context?"
- Low confidence (< 0.4) → "Could you rephrase...?"

### 4.6 Semantic Search (v1.3.0)

`OfflineKnowledgeBase.search_semantic(query, top_k)` provides BM25-ranked
full-text search using the SQLite FTS5 index. The enhancement pipeline
prefers semantic search over domain-filtered search, falling back to
`search()` when BM25 returns no results.

---

## 5. Integration Contracts

### 5.1 Python SDK Interface

The primary public API:

```python
# Simple enhancement
from aipea import enhance_prompt, SecurityLevel, ComplianceMode

result = await enhance_prompt(
    query="What are the latest advances in quantum error correction?",
    model_id="claude-opus-4-6",
    security_level=SecurityLevel.UNCLASSIFIED,  # Optional, default UNCLASSIFIED
    compliance_mode=ComplianceMode.HIPAA,        # Optional, default None (uses enhancer default)
    force_offline=False,                         # Optional, default False
    include_search=True,                         # Optional, default True — skip search context
    format_for_model=True,                       # Optional, default True — skip model-specific formatting
    strategy="research",                         # Optional, default None (auto-select by QueryType)
)

# result.enhanced_prompt      → str (ready for LLM)
# result.processing_tier      → ProcessingTier.TACTICAL
# result.security_context     → SecurityContext(...)
# result.query_analysis       → QueryAnalysis(...)
# result.search_context       → SearchContext(...) or None
# result.enhancement_time_ms  → 127.3
# result.was_enhanced         → True
# result.enhancement_notes    → ["Online context gathered from exa: 3 results"]
```

```python
# Multi-model enhancement
from aipea import AIPEAEnhancer

enhancer = AIPEAEnhancer()
requests = await enhancer.enhance_for_models(
    query="Explain quantum computing",
    model_ids=["gpt-5.2", "claude-opus-4-6", "gemini-3-pro-preview"],
)
# requests["gpt-5.2"].enhanced_prompt → GPT-optimized prompt
# requests["claude-opus-4-6"].enhanced_prompt → Claude-optimized prompt
```

```python
# Direct security scanning
from aipea import quick_scan, ComplianceMode

result = quick_scan("My SSN is 123-45-6789", mode=ComplianceMode.HIPAA)
# result.has_pii() → True
# result.flags → ["pii_detected:ssn"]
```

### 5.2 Agora Adapter (existing pattern)

Lives in **AgoraIV** repo (not in AIPEA). After extraction:

```python
# agora_prompt_enhancement.py (in AgoraIV)
from aipea import AIPEAEnhancer, EnhancementResult, EnhancedRequest
from aipea import SecurityLevel, ComplianceMode, ProcessingTier

class AgoraPromptEnhancement:
    """Agora-specific adapter wrapping AIPEAEnhancer."""

    def __init__(self, ...):
        self._enhancer = AIPEAEnhancer(...)

    async def enhance(self, query, model_id, ...) -> EnhancementResult:
        return await self._enhancer.enhance(query, model_id, ...)

    async def enhance_for_models(self, query, model_ids, ...) -> dict[str, EnhancedRequest]:
        return await self._enhancer.enhance_for_models(query, model_ids, ...)

# Convenience functions remain for backward compatibility
async def enhance_prompt(query, model_id, security_level=UNCLASSIFIED,
                         compliance_mode=None, force_offline=False,
                         include_search=True, format_for_model=True,
                         strategy=None) -> EnhancementResult:
    return await get_enhancer().enhance(query, model_id, security_level, compliance_mode,
                                        force_offline, include_search, format_for_model)

async def enhance_for_agora(query, model_ids, security_level) -> dict[str, EnhancedRequest]:
    return await get_enhancer().enhance_for_models(query, model_ids, security_level)
```

### 5.3 AEGIS Adapter

Lives in **aegis-governance** repo at `src/integration/aipea_bridge.py`.
Maps AIPEA output to AEGIS gate evaluation input via `AIPEAGateAdapter`:

```python
# In aegis-governance repo
from integration.aipea_bridge import AIPEAGateAdapter

adapter = AIPEAGateAdapter(compliance_mode="general")
claim = await adapter.preprocess_claim("Evaluate this proposal")
# claim.enhanced_claim  → enriched text
# claim.query_type      → "technical" | "research" | ...
# claim.complexity      → 0.0-1.0
# claim.processing_tier → "offline" | "tactical" | "strategic"
```

AIPEA is an optional dependency — adapter returns passthrough results when not installed.

### 5.4 Generic Consumer Protocol

Any system can integrate AIPEA by implementing this minimal contract:

```python
from aipea import enhance_prompt, EnhancementResult

async def my_llm_call(query: str, model_id: str) -> str:
    # Step 1: Enhance
    result: EnhancementResult = await enhance_prompt(query, model_id)

    # Step 2: Check security
    if not result.was_enhanced:
        # Query was blocked or enhancement disabled
        return handle_blocked(result)

    # Step 3: Call LLM with enhanced prompt
    response = await call_llm(model_id, result.enhanced_prompt)

    return response
```

---

## 6. Processing Tiers

### 6.1 Tier 0 — Offline

| Property | Value |
|----------|-------|
| Latency | < 2 seconds |
| Availability | 100% (zero dependencies) |
| Connectivity | None required |
| Confidence | 0.70-0.82 |
| Mechanism | Pattern matching + templates, optional Ollama SLMs |
| Storage | SQLite with zlib compression |

**When used**:
- Security level >= SECRET
- Compliance mode == TACTICAL
- `force_offline=True`
- No connectivity (`has_connectivity=False`)
- Query complexity <= 0.3 AND no temporal needs

**Resources**: SQLite database (configurable tier: 1GB-100GB),
optional Ollama (291MB-40GB depending on model, including gemma3:1b at 815MB).

### 6.2 Tier 1 — Tactical

| Property | Value |
|----------|-------|
| Latency | 2-5 seconds |
| Availability | Requires network for search |
| Connectivity | Internet (Exa/Firecrawl APIs) |
| Confidence | 0.85-0.88 |
| Mechanism | Search enrichment + structured templates + optional LLM |

**When used**:
- Query complexity 0.3-0.7
- Temporal needs detected
- Domain-specific queries (medical, legal, financial)

**Resources**: Exa API key, Firecrawl API key (both optional — degrades gracefully).

### 6.3 Tier 2 — Strategic

| Property | Value |
|----------|-------|
| Latency | 5-15 seconds |
| Availability | Requires LLM orchestrator |
| Connectivity | Internet (LLM APIs) |
| Confidence | 0.92-0.98 |
| Mechanism | Multi-step: decompose → parallel analyze → synthesize → critique loop |

**When used**:
- Query complexity > 0.7
- Low confidence (< 0.5) after initial analysis
- Multiple domains detected (3+)

**Resources**: LLM orchestrator (e.g., Agora's ConsultationOrchestrator).
Falls back to structured template if no orchestrator available.

### 6.4 Tier Escalation

```
Low confidence (< 0.5) at any tier → escalate to next tier
OFFLINE → TACTICAL → STRATEGIC → (cap at STRATEGIC)
```

---

## 7. Security & Compliance

### 7.1 Security Levels

| Level | Value | Behavior |
|-------|-------|----------|
| UNCLASSIFIED | 0 | Standard processing |
| SENSITIVE | 1 | Standard processing with audit |
| CUI | 2 | Controlled handling |
| SECRET | 3 | **Force offline**, no external API calls |
| TOP_SECRET | 4 | **Force offline**, no external API calls |

### 7.2 Compliance Modes

See Section 3.1.3 (ComplianceHandler) for full details.

Key rule: **compliance mode + security level together determine routing**.
TACTICAL mode always forces offline. SECRET+ always forces offline.
HIPAA enables PHI scanning. GENERAL has no restrictions.

### 7.3 Model Allowlists

Per-compliance-mode allowlists use **substring matching** (case-insensitive):

| Mode | Allowed Models | Rationale |
|------|---------------|-----------|
| GENERAL | All (except forbidden) | No restrictions |
| HIPAA | `claude-opus-4-6`, `claude-opus-4-5`, `gpt-5.2` | BAA-covered families |
| TACTICAL | `llama-3.3-70b` | Local models only |

`FEDRAMP` previously had its own allowlist (`claude-opus-4-6`, `claude-opus-4-5`, `gpt-5.2`, billed as "FedRAMP authorized"). That list was never externally validated — the mode was a config-only stub. `FEDRAMP` is deprecated in v1.3.4 (ADR-002); the legacy allowlist is retained for back-compat through v1.x only.

**Global forbidden list**: `gpt-4o`, `gpt-4o-mini` (deprecated models).

### 7.4 Injection Prevention

10 injection patterns are **always blocked** regardless of compliance mode:

1. `(ignore|disregard|forget|override) (the|all|your|my|any|these|those|of)* (previous|prior|above|earlier|preceding|system|developer|assistant){1,3} instructions` — Prompt injection (strong-cue form; supports stacked cues like "ignore previous system instructions" and "ignore the above developer instructions"; filler restricted to determiners/qualifiers so "forget to print your instructions" is not matched)
2. `(ignore|disregard|forget|override) all (of|the|your|my|these|those|previous|prior|above|earlier|preceding|system|developer|assistant)* instructions` — Prompt injection (direct "all" form; filler allow-list includes role cues so "ignore all system instructions" blocks while "don't forget to send all instructions" does not)
3. `(ignore|disregard|forget|override) (everything|all) (above|below|before|earlier|preceding)(?=\s*[.!?,;:\n]|$)` — Prompt injection sibling ("ignore everything above"; phrase-end lookahead so "ignore all prior art" is not matched)
4. `</(system|user|assistant)>` — XML role tag injection
5. `[/(system|user|assistant|human)]` — Bracket-style role tags
6. `\n\s*(Human|Assistant|System):` — Conversation separator injection (with whitespace tolerance)
7. `DROP TABLE` — SQL injection
8. `UNION SELECT` — SQL injection
9. `{{.*}}` — Template injection (Jinja2/Handlebars)
10. `<script>` — XSS attempt

All queries are normalized before pattern matching to prevent homoglyph bypass attacks:
1. **NFKC normalization** — converts fullwidth characters and compatibility forms to ASCII equivalents
2. **Confusable character mapping** — translates 35 common Cyrillic/Greek homoglyphs to Latin (e.g., Cyrillic U+043E 'o' to Latin 'o')

Custom blocked patterns from `SecurityContext.blocked_patterns` are validated
for ReDoS safety before execution.

---

## 8. Configuration & Deployment

### 8.1 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EXA_API_KEY` | (none) | Exa search provider API key |
| `FIRECRAWL_API_KEY` | (none) | Firecrawl provider API key |
| `AIPEA_HTTP_TIMEOUT` | `30.0` | HTTP timeout for search providers (seconds) |
| `AIPEA_OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL for offline models |
| `AIPEA_DB_PATH` | `aipea_knowledge.db` | Path to offline knowledge SQLite database |
| `AIPEA_STORAGE_TIER` | `standard` | Storage tier: ultra_compact, compact, standard, extended |
| `AIPEA_DEFAULT_COMPLIANCE` | `general` | Default compliance mode: general, hipaa, tactical (`fedramp` is deprecated — see ADR-002) |
| `AIPEA_EXA_API_URL` | `https://api.exa.ai/search` | Exa API endpoint URL |
| `AIPEA_FIRECRAWL_API_URL` | `https://api.firecrawl.dev/v1/search` | Firecrawl API endpoint URL |

### 8.2 Configuration System

AIPEA uses a layered configuration system implemented in `config.py`:

**Priority chain** (highest wins):

```
Constructor args > Environment vars > .env (cwd) > ~/.aipea/config.toml > Defaults
```

**`AIPEAConfig` dataclass** (`from aipea import AIPEAConfig, load_config`):

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `exa_api_key` | `str` | `""` | Exa search provider key |
| `firecrawl_api_key` | `str` | `""` | Firecrawl provider key |
| `http_timeout` | `float` | `30.0` | HTTP timeout (seconds) |
| `ollama_host` | `str` | `"http://localhost:11434"` | Ollama server URL |
| `db_path` | `str` | `"aipea_knowledge.db"` | Offline knowledge DB path |
| `storage_tier` | `str` | `"standard"` | Storage tier name |
| `default_compliance` | `str` | `"general"` | Default compliance mode |
| `exa_api_url` | `str` | `"https://api.exa.ai/search"` | Exa API endpoint URL |
| `firecrawl_api_url` | `str` | `"https://api.firecrawl.dev/v1/search"` | Firecrawl API endpoint URL |

Helpers: `has_exa()`, `has_firecrawl()`, `redact_key(key)`.

**File locations**:

| Location | Scope | Format |
|----------|-------|--------|
| `.env` (cwd) | Project-local | `KEY=VALUE` (one per line) |
| `~/.aipea/config.toml` | Global | TOML `[aipea]` section |

Files are created with `0o600` permissions for security. The `_sources` dict
on `AIPEAConfig` tracks where each value was resolved from.

**CLI commands** (`pip install aipea[cli]`):

| Command | Purpose |
|---------|---------|
| `aipea configure [--global]` | Interactive setup wizard |
| `aipea check [--connectivity]` | Verify config and test API keys |
| `aipea doctor` | Full diagnostic (Python, deps, config, security, Ollama, knowledge base, connectivity) |
| `aipea info` | Quick library summary |
| `aipea seed-kb` | Populate offline knowledge base with 20 seed entries across 7 domains |

### 8.3 Embedded Library Mode (Primary)

AIPEA ships as a Python package installable via pip:

```bash
pip install aipea
```

```toml
# pyproject.toml
[project]
name = "aipea"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27.0",
]

[project.optional-dependencies]
cli = ["typer[all]>=0.12"]  # CLI tools (configure, check, doctor, info)
ollama = []  # No additional deps; ollama CLI must be installed separately

[project.scripts]
aipea = "aipea.cli:app"
```

Minimal dependency footprint: **stdlib + httpx**. This is intentional and
must be preserved. The `[cli]` extra adds Typer + Rich for the onboarding CLI.

### 8.4 Standalone Service Mode (Optional, Future)

For consumers that prefer HTTP over library import:

```bash
pip install aipea[server]
uvicorn aipea.server:app --port 9000
```

```
POST /enhance
{
    "query": "...",
    "model_id": "claude-opus-4-6",
    "compliance_mode": "general"
}
→ 200 { "enhanced_prompt": "...", "processing_tier": "tactical", ... }
```

This is **not built** in v1.0.0. Specified here for future reference.

---

## 9. Intentional Descopes

These features were in the original Agora V design but are intentionally
excluded from AIPEA v1.0.0. Each has a rationale based on production experience.

### 9.1 BDI Reasoning Engine

**Original design**: 187 LOC `BDIReasoningEngine` class with `perceive()`,
`deliberate()`, `plan()` methods implementing Belief-Desire-Intention architecture
for autonomous decision-making.

**Why descoped**: The 3-tier processing model (Offline → Tactical → Strategic)
provides equivalent routing capability with far less complexity. BDI's value
proposition — autonomous plan generation — is overkill for a preprocessing library
where the "plan" is always: analyze → enrich → format. The tier escalation logic
handles the deliberation BDI was designed for.

**What replaces it**: `QueryRouter.route()` + tier escalation in `QueryAnalyzer`.

### 9.2 Message Bus Architecture

**Original design**: 287 LOC `AgoraIntegrationProtocol` with `MessageBus`,
`CoordinationManager`, send-and-wait patterns, broadcast capability, swarm
participation, emergency protocols.

**Why descoped**: AIPEA is a **library, not a service**. Consumers call
`enhance_prompt()` directly — there's no need for message routing between components.
The original design assumed AIPEA would be an autonomous agent participating in
an Agora V agent swarm. In production, direct function calls are simpler, faster,
and easier to debug.

**What replaces it**: Direct Python imports. Consumer adapters (Section 5) handle
integration-specific concerns.

### 9.3 Market Configuration

**Original design**: 702 LOC `MarketConfigurationManager` with 5 market segments
(Consumer, Small Business, Enterprise, Government, Defense), per-segment pricing,
feature gating, and compliance mapping.

**Why descoped**: Premature. AIPEA is an internal library, not a SaaS product.
Market segmentation belongs in the product layer (Agora/AEGIS pricing), not the
preprocessing layer. The supported compliance modes (GENERAL, HIPAA, TACTICAL)
already handle the security/regulatory dimension that market configs were
partially addressing. (`FEDRAMP` was previously listed here but was deprecated
in v1.3.4; see ADR-002.)

**What replaces it**: `ComplianceMode` enum + `ComplianceHandler` configuration.

### 9.4 EKS/Terraform Infrastructure

**Original design**: ~1,000 LOC Terraform configuration for EKS deployment with
auto-scaling, disaster recovery, multi-region.

**Why descoped**: AIPEA ships as a pip-installable library. Infrastructure belongs
to the consumer. AgoraIV runs on ECS Fargate (not EKS) — the Terraform config
was never applicable to the actual deployment.

**What replaces it**: `pip install aipea` in the consumer's deployment pipeline.

### 9.5 YAML Configuration System

**Original design**: ~1,500 LOC YAML schema with validation, hot-reload,
environment overrides.

**Why descoped**: Python dataclasses + environment variables are sufficient for
a library's configuration surface. A YAML system adds complexity (schema
validation, file watching, hot reload) that provides no value when the library
is initialized once at import time.

**What replaces it**: Constructor arguments + environment variables (Section 8.1).

### 9.6 Resilience Test Suite

**Original design**: 1,037 LOC with 7 test categories (connectivity, adversarial,
load, security, degradation, recovery, compliance).

**Why descoped as a separate artifact**: The 209+ AIPEA-related tests in AgoraIV's
test suite already cover security scanning, compliance handling, search providers,
knowledge base, query analysis, and prompt formulation. The original resilience
tests were designed for a standalone service; as a library, AIPEA inherits the
consumer's resilience characteristics.

**What replaces it**: AgoraIV's existing test suite (extracted into `tests/`).

---

## 10. Future Roadmap

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the full roadmap with 6 prioritized features
(P1-P4), implementation sketches, and planned environment variables.

---

## 11. API Reference

### 11.1 Public Exports (`aipea/__init__.py`)

> **Note**: The actual `__init__.py` exports 50 symbols (as of ADR-004: 37 runtime
> classes/functions + 6 exception types (Wave C3) + `AdaptiveLearningEngine`,
> `LearningPolicy`, `LearningRecordResult` (Wave D1 + ADR-004) + 5 `FLAG_*`
> constants (ADR-004)).
> The listing below shows the full internal API surface (including non-exported
> internals) for reference. Symbols marked with `# (not in __all__)` are
> accessible but not part of the public API.

```python
# Main entry points
from aipea.enhancer import (
    AIPEAEnhancer,
    EnhancedRequest,      # Data model (lives in enhancer.py, not models.py)
    EnhancementResult,    # Data model (lives in enhancer.py, not models.py)
    enhance_prompt,
    get_enhancer,
    reset_enhancer,
)

# Adaptive learning (Wave D1) + compliance policy + ADR-004
from aipea.learning import AdaptiveLearningEngine, LearningPolicy, LearningRecordResult

# Shared data models
from aipea.models import QueryAnalysis

# Shared enums and canonical helpers
from aipea._types import (
    ProcessingTier, QueryType, SearchStrategy,
    QUERY_TYPE_PATTERNS,       # canonical query-type regex dict
    MODEL_FAMILY_MAP,          # model-id → family mapping
    get_model_family,          # canonical model family detector
)

# Security + ADR-004 flag constants
from aipea.security import (
    FLAG_PII_DETECTED,                # ADR-004
    FLAG_PHI_DETECTED,                # ADR-004
    FLAG_CLASSIFIED_MARKER,           # ADR-004
    FLAG_INJECTION_ATTEMPT,           # ADR-004
    FLAG_CUSTOM_BLOCKED,              # ADR-004
    SecurityLevel,
    ComplianceMode,
    SecurityContext,
    ScanResult,
    SecurityScanner,
    ComplianceHandler,
    create_security_context_for_mode,  # (not in __all__)
    quick_scan,
)

# Knowledge
from aipea.knowledge import (
    OfflineKnowledgeBase,
    KnowledgeNode,
    KnowledgeDomain,
    KnowledgeSearchResult,
    StorageTier,
)

# Search
from aipea.search import (
    SearchProvider,
    ExaSearchProvider,
    FirecrawlProvider,
    Context7Provider,
    SearchOrchestrator,
    SearchResult,
    ModelType,             # (not in __all__)
    create_empty_context,  # (not in __all__)
    parse_model_type,      # (not in __all__)
)

# Analysis
from aipea.analyzer import (
    QueryAnalyzer,
    QueryRouter,           # (not in __all__)
    analyze_query,         # (not in __all__)
    route_query,           # (not in __all__)
)

# Engine
from aipea.engine import (
    PromptEngine,
    OfflineTierProcessor,          # (not in __all__)
    # TacticalTierProcessor — REMOVED in v1.2.0 (dead code)
    # StrategicTierProcessor — REMOVED in v1.2.0 (dead code)
    TierProcessor,                 # (not in __all__)
    EnhancedQuery,                 # (not in __all__)
    SearchContext,                  # (not in __all__) — re-export of aipea.search.SearchContext
    OllamaOfflineClient,           # (not in __all__)
    OfflineModel,                  # (not in __all__)
    get_ollama_client,             # (not in __all__)
    get_prompt_engine,             # (not in __all__)
)

# Configuration
from aipea.config import (
    AIPEAConfig,
    load_config,
)
```

### 11.2 AIPEAEnhancer

```python
class AIPEAEnhancer:
    """Main facade for AIPEA prompt enhancement."""

    def __init__(
        self,
        enable_enhancement: bool = True,
        storage_tier: StorageTier = StorageTier.STANDARD,
        default_compliance: ComplianceMode = ComplianceMode.GENERAL,
        exa_api_key: str | None = None,
        firecrawl_api_key: str | None = None,
        enable_learning: bool = False,                          # Wave D1
        learning_policy: LearningPolicy | None = None,          # v1.5.0
    ) -> None: ...
    # enable_learning=True initialises AdaptiveLearningEngine backed by
    # AIPEA_LEARNING_DB_PATH (default: aipea_learning.db). When enabled,
    # enhance() consults the learning engine for strategy suggestions
    # (learned > caller override > default). Gracefully degrades if DB
    # init fails.

    async def enhance(
        self,
        query: str,
        model_id: str,
        security_level: SecurityLevel = SecurityLevel.UNCLASSIFIED,
        compliance_mode: ComplianceMode | None = None,
        force_offline: bool = False,
        include_search: bool = True,
        format_for_model: bool = True,
        strategy: str | None = None,
        embed_search_context: bool = True,
    ) -> EnhancementResult: ...

    async def enhance_for_models(
        self,
        query: str,
        model_ids: list[str],
        security_level: SecurityLevel = SecurityLevel.UNCLASSIFIED,
    ) -> dict[str, EnhancedRequest]: ...
    # enhance_for_models calls enhance(embed_search_context=False) once to
    # run the security scan, query analysis, and search-context fetch, then
    # rebuilds each model's prompt via formulate_search_aware_prompt() with
    # the cached search_context so every model gets its own query-section
    # format (GPT markdown, Claude XML, Gemini numbered). (wave 18 #90)

    async def record_feedback(                                  # Wave D1 + ADR-004
        self, result: EnhancementResult, score: float,
    ) -> None: ...
    # Records user feedback on an enhancement result for adaptive learning.
    # score in [-1.0, 1.0] (positive = good). No-op if learning is disabled.
    # Delegates to AdaptiveLearningEngine.arecord_feedback().
    # ADR-004: threads result.scan_result.flags as scan_flags to the engine.
    # Tainted feedback (PII/PHI/classified/injection) is recorded for audit
    # but excluded from strategy_performance averaging by default.

    def close(self) -> None: ...
    def __enter__(self) -> AIPEAEnhancer: ...
    def __exit__(self, *exc: object) -> None: ...
    # Supports context manager protocol for deterministic resource cleanup.
    # close() releases the offline knowledge base and learning engine
    # SQLite connections. Idempotent — safe to call multiple times.

    def get_status(self) -> dict[str, Any]: ...
    # Returns dict with keys: enhancement_enabled, storage_tier,
    # default_compliance, offline_knowledge_ready, search_orchestrator_ready,
    # queries_enhanced, queries_blocked, queries_passthrough,
    # avg_enhancement_time_ms, tier_distribution, compliance_distribution,
    # learning_enabled, learning_stats.                         # Wave D1
    def reset_stats(self) -> None: ...
```

### 11.3 EnhancementResult

```python
@dataclass
class EnhancementResult:
    original_query: str
    enhanced_prompt: str
    processing_tier: ProcessingTier
    security_context: SecurityContext
    query_analysis: QueryAnalysis
    search_context: SearchContext | None = None
    enhancement_time_ms: float = 0.0
    was_enhanced: bool = True
    enhancement_notes: list[str] = field(default_factory=list)
    clarifications: list[str] = field(default_factory=list)     # v1.3.0
    quality_score: QualityScore | None = None                   # v1.3.0
    strategy_used: str = ""                                     # Wave D1
    scan_result: ScanResult | None = None                       # ADR-004

    def to_dict(self) -> dict[str, Any]: ...
```

### 11.4 Model Family Detection

```python
# Model ID → family mapping (used for formatting)
MODEL_FAMILY_MAP = {
    "gpt-4": "openai",
    "gpt-5.2": "openai",
    "claude-opus-4-6": "claude",
    "claude-sonnet-4-5": "claude",
    "gemini-3-pro-preview": "gemini",
    "llama-3.3-70b": "llama",
    # ... (full list in _types.py)
}

OFFLINE_MODELS = {"gpt-oss-20b", "llama-3.3-70b", "llama-3.2-3b", "gemma-3n"}

def get_model_family(model_id: str) -> str: ...
def is_offline_model(model_id: str) -> bool: ...
```

---

## Appendix A: Gap Analysis Summary

| Category | Original Design | Production (AgoraIV) | Coverage |
|----------|----------------|---------------------|----------|
| Security scanning | 4 categories | 4 categories + ReDoS + model allowlists | **100%+** |
| Compliance modes | GDPR/CCPA/FedRAMP/FISMA/ITAR | GENERAL/HIPAA/TACTICAL (FEDRAMP deprecated v1.3.4, ADR-002) | **Narrower but honest** |
| Offline knowledge | 12 features | 8 features (CRUD, compression, search, tiers) | **67%** |
| Search providers | 3 providers | 3 providers (Context7 stub by design) | **100%** |
| Enhancement strategies | 6 named + QualityAssessor | Template-based classification | **~30%** |
| BDI reasoning | Full perceive/deliberate/plan | QueryRouter + tier escalation | **Alternative** |
| Integration protocol | Message bus + routing | Direct function calls | **Alternative** |
| Market configuration | 5 segments with feature gating | ComplianceMode enum | **0% (descoped)** |
| Test coverage | 7 resilience categories | 209+ tests, 13 files | **Exceeds** |

## Appendix B: File Lineage

| AIPEA Module | AgoraIV Source | LOC | Rename |
|-------------|---------------|-----|--------|
| `security.py` | `aipea_security_context.py` | 637 | Verbatim |
| `knowledge.py` | `aipea_offline_knowledge.py` | 711 | Verbatim |
| `search.py` | `aipea_search_providers.py` | 1,071 | Verbatim |
| `analyzer.py` | `pcw_query_analyzer.py` | 961 | `PCWQueryAnalyzer` → `QueryAnalyzer` |
| `engine.py` | `pcw_prompt_engine.py` | 1,685 | `PCWPromptEngine` → `PromptEngine` |
| `enhancer.py` | `agora_prompt_enhancement.py` | 1,034 | `AgoraPromptEnhancement` → `AIPEAEnhancer` |
| **Total** | | **6,099** | |

## Appendix C: Original Design Files (Provenance)

Stored in `docs/design-reference/` for historical reference:

| File | LOC | Purpose |
|------|-----|---------|
| `aipea-specification.md` | 373 | Master specification |
| `aipea-agent-framework.py` | 934 | BDI + unified agent framework |
| `aipea-enhancement-engine.py` | 617 | 6 strategies + quality assessor |
| `aipea-market-configs.py` | 702 | 5 market segments |
| `aipea-offline-knowledge.py` | 833 | KB + adaptive learning |
| `aipea-agora-integration.py` | 609 | Message bus + swarm |
| `aipea-config-management.txt` | ~1,500 | YAML config schema |
| `aipea-aws-deployment.txt` | ~1,000 | Terraform/EKS |
| `aipea-resilience-tests.py` | 1,037 | 7 test categories |
| **Total** | **~7,605** | |

---

*AIPEA Specification v1.6.0 — AI Prompt Engineer Agent*
*Undercurrent Holdings | 2026-04-15 (v1.6.0 released)*
