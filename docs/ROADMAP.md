# AIPEA Roadmap

Future features ordered by priority. Each item references its origin in the Agora V design.

Extracted from SPECIFICATION.md Section 10 to keep the spec as pure ground truth
for what IS implemented, and this document as a living roadmap for what's PLANNED.

---

## P1: Dialogical Clarification (advisory mode) — IMPLEMENTED in v1.3.0

**Implemented in**: v1.3.0

**Origin**: Production observation — AIPEA's analyzer already computes signals
that indicate a query needs clarification, but those signals are consumed silently
by the enhancement pipeline. Inspired by Deep Research interfaces (Claude, ChatGPT)
that ask clarifying questions before beginning work.

**Problem**: AIPEA currently polishes vague queries into *confidently vague* prompts.
The analyzer knows when a query is ambiguous (`ambiguity_score`), short, missing
entities (`detected_entities`), or lacking domain specificity — and
`suggest_enhancements()` already generates human-readable suggestions. But none of
this reaches the consumer.

**Design constraint**: AIPEA is a library, not a chatbot. It cannot pause and ask
the user questions — the consumer (Agora, AEGIS, CLI) owns the conversation. The
solution must preserve the single-call, non-blocking API model.

**Proposed approach**: Generate clarifying questions and attach them to the result
alongside the best-effort enhancement. The consumer decides what to do with them.

```python
result = await enhancer.enhance("quantum computing", model_id="claude-opus-4-6")

result.enhanced_prompt        # Still works — best-effort enhancement
result.clarifications         # NEW: list of suggested clarifying questions
# e.g., ["Which aspect? (error correction, algorithms, hardware)",
#        "What's your background level on this topic?",
#        "Academic research or practical application?"]
```

Consumer integration patterns:
- **Agora**: Show clarifications to user, collect answers, re-call `enhance()` with
  enriched query
- **AEGIS**: Ignore clarifications, use best-effort prompt directly
- **CLI tool**: Print clarifications as follow-up suggestions

**Implementation sketch**:
- Add `clarifications: list[str]` field to `EnhancementResult` (default: empty list)
- In the enhancement pipeline (after `QueryAnalyzer.analyze()`), generate questions
  from existing signals:
  - High `ambiguity_score` → "Could you be more specific about...?"
  - Low `detected_entities` count → "What specific [domain] topic?"
  - High `complexity` + no search strategy → "Are you looking for a summary
    or a deep dive?"
  - `suggest_enhancements()` output → reformulate as questions
- Threshold: only generate clarifications when `ambiguity_score > 0.6` or
  `len(detected_entities) == 0` to avoid noise on clear queries

**What already exists**:
- `QueryAnalysis.ambiguity_score` — computed for every query
- `QueryAnalysis.complexity` — computed for every query
- `QueryAnalysis.detected_entities` — entity extraction per query
- `QueryAnalyzer.suggest_enhancements()` — generates text suggestions
- `enhancement_notes: list[str]` on `EnhancementResult` — precedent for advisory output

**Bridges**: P2 (`hypothesis_clarification` technique) and P4
(`specificity_gain` metric). Asking clarifications *before* enhancement is how
you improve specificity at the source.

---

## P2a: Named Enhancement Strategies (6 types) — IMPLEMENTED in v1.3.0

**Implemented in**: v1.3.0 | **Origin**: `aipea-enhancement-engine.py` lines 78-503

Expand from template-based classification to named strategies with technique
libraries:

```python
class EnhancementStrategy:
    name: str                    # e.g., "technical"
    techniques: list[str]        # e.g., ["specification_extraction", "constraint_identification"]
    context_requirements: list   # Required context for this strategy
    output_format: str           # Expected output structure
```

Techniques to implement:
- `specification_extraction` — Extract implicit requirements from query
- `constraint_identification` — Identify explicit and implicit constraints
- `hypothesis_clarification` — Reformulate ambiguous claims as testable hypotheses
- `metric_definition` — Define measurable success criteria
- `task_decomposition` — Break complex queries into sub-tasks
- `objective_hierarchy_construction` — Build goal tree from strategic queries

---

## P2b: Semantic Search in Offline KB — IMPLEMENTED in v1.3.0

**Implemented in**: v1.3.0 | **Origin**: `aipea-offline-knowledge.py` lines 632-747

Add semantic similarity search using SQLite FTS5 or lightweight embeddings:

```python
async def search_semantic(self, query: str, top_k: int = 5) -> list[KnowledgeNode]:
    """Search using TF-IDF or lightweight embeddings for better relevance."""
```

Current `search()` uses domain filter + relevance score ordering. Embedding
search would enable content-based similarity without external dependencies
(using SQLite FTS5 for token-level matching).

---

## P3a: Quality Assessor — IMPLEMENTED in v1.3.0

**Implemented in**: v1.3.0 | **Origin**: `aipea-enhancement-engine.py` lines 562-589

Measure enhancement effectiveness:

```python
class QualityAssessor:
    def assess(self, original: str, enhanced: str) -> QualityScore:
        ...

@dataclass
class QualityScore:
    clarity_improvement: float      # 0.0-1.0
    specificity_gain: float         # 0.0-1.0
    information_density: float      # 0.0-1.0
    instruction_quality: float      # 0.0-1.0
    overall: float                  # Weighted composite
```

---

## P3b: Adaptive Learning Engine (planned for v1.4.0)

**Origin**: `aipea-offline-knowledge.py` AdaptiveLearningEngine class

Learn from user feedback to improve enhancement quality over time:

```python
class AdaptiveLearningEngine:
    async def learn_from_feedback(self, query, enhanced, feedback_score): ...
    async def get_best_strategy(self, query_type) -> str: ...
```

Requires:
- Learning event storage (additional SQLite table)
- Pattern extraction from successful enhancements
- Strategy performance tracking

---

## P4: BDI Reasoning (conditional)

**Origin**: `aipea-agent-framework.py` lines 103-290

Only pursue if AIPEA evolves from a preprocessing library into an autonomous
agent participating in multi-agent orchestration. Current tier escalation logic
handles the routing/deliberation that BDI was designed for. Revisit if/when
AIPEA needs to:

- Autonomously decide when to enhance vs. pass through
- Coordinate with other agents (not just respond to consumer calls)
- Maintain persistent beliefs across sessions

---

## Environment Variables (v1.3.0)

All planned environment variables are now implemented. Each follows the standard
priority chain: env var > `.env` file > `~/.aipea/config.toml` > default.

| Variable | Default | Description | Since |
|----------|---------|-------------|-------|
| `AIPEA_DB_PATH` | `aipea_knowledge.db` | Path to offline knowledge SQLite database | v1.3.0 |
| `AIPEA_STORAGE_TIER` | `standard` | Storage tier: ultra_compact, compact, standard, extended | v1.3.0 |
| `AIPEA_DEFAULT_COMPLIANCE` | `general` | Default compliance mode | v1.3.0 |
| `AIPEA_OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL for offline models | v1.3.0 |
| `AIPEA_EXA_API_URL` | `https://api.exa.ai/search` | Exa API endpoint URL | v1.3.0 |
| `AIPEA_FIRECRAWL_API_URL` | `https://api.firecrawl.dev/v1/search` | Firecrawl API endpoint URL | v1.3.0 |

---

*AIPEA Roadmap | Extracted from SPECIFICATION.md Section 10 | Updated 2026-03-13*
