# AIPEA Roadmap

> **Consolidated**: All roadmap items are now tracked in [`TODO.md`](../TODO.md).
> This file is retained for historical context on feature design rationale.

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

## P5: Investor Review Follow-ups (2026-04-11)

**Origin**: Independent investor-perspective review of AIPEA v1.3.2
([docs/claude/audits/investor-review-2026-04-11.md](claude/audits/investor-review-2026-04-11.md))
scored the project 39/45 (87%). The five items below close the gaps that
separated it from a 95%+ score. They are ordered by leverage, not by sequencing;
some are engineering work, some are process/BD work.

### P5a: Second-reviewer coverage on security-critical modules — **HIGHEST LEVERAGE**

**Problem**: Bus-factor 1. Every commit traces to a single human; no external
code review appears on any PR. This is the single largest investor objection.

**Action**:
- Contract a part-time senior reviewer (security background) for ~4 hrs/week.
- Add a `CODEOWNERS` file requiring their review on:
  - `src/aipea/security.py`
  - `src/aipea/__init__.py` (public API surface)
  - `pyproject.toml` (dependency changes)
- Document review SLA in `CONTRIBUTING.md`.

**Effort**: Process change + ongoing contractor cost.
**Blocks**: Nothing. Do this first.

### P5b: Resolve FedRAMP — ship it or stop claiming it

**Problem**: `ComplianceMode.FEDRAMP` is prominent in README but
`src/aipea/security.py:610-626` honestly labels it as a stub. A government
evaluator will spot this inside the first hour. The current state is the worst
of both worlds.

**Decision fork**:
- **Path A (commercial)**: Find a design-partner org that needs FedRAMP.
  Scope minimum-viable enforcement (model allowlist, audit-trail hook,
  encryption-at-rest contract) built *with their input*, ship as v1.4.0.
- **Path B (honest)**: Remove `FEDRAMP` from `ComplianceMode`, strike it from
  the README, write an ADR in `docs/adr/` explaining why.

**Effort**: A = months (requires external customer); B = one afternoon.
**Blocks**: A investor narrative ("regulated AI market wedge") if not resolved.

### P5c: Custom exception hierarchy and tightened CLI error handling

**Problem**: Genuine broad `except Exception:` swallows at `src/aipea/cli.py:191`,
`:220`, `:283`, and `:438`. `cli.py:391` is a residual fallback after a
specific `subprocess.TimeoutExpired` catch and is a weaker candidate.
`config.py:444` is a cleanup-and-reraise pattern (`except Exception: ... raise`)
and is *not* a swallow — out of scope. Consumers (Agora IV, AEGIS) can't
discriminate failure modes because no custom exception types exist. This is the
only consistent code-quality complaint in the self-assessment.

**Action**:
1. Create `src/aipea/errors.py` with an `AIPEAError` base plus five subclasses:
   `SecurityScanError`, `EnhancementError`, `KnowledgeStoreError`,
   `SearchProviderError`, `ConfigError`.
2. Walk each genuine `except Exception:` swallow and replace with specific
   types. `cli.py:283` should catch `importlib.metadata.PackageNotFoundError`.
   Keep one outermost catch-all in CLI command handlers (logs full traceback
   at DEBUG, friendly message at ERROR) — but only one, at the boundary.
3. Add one regression test per converted block. Wave 19 is already taken by
   PR #14 (`fix/bug-hunt-wave-19`); file this under the next open wave number.

**Effort**: 1–2 days.
**Result**: Pushes code craftsmanship from 4/5 toward 5/5 in a subsequent
self-assessment.

### P5d: Promote mutation testing to gating + add performance regression suite

**Problem**: 91.79% line coverage doesn't prove operator correctness. `mutmut`
currently runs nightly with `continue-on-error`. No latency SLOs exist, so
semantic search and FTS paths can degrade silently.

**Action**:
1. **Mutation**: Resolve the enum-trampoline issue noted in `KNOWN_ISSUES.md`.
   Move `mutmut` into a dedicated CI job with a mutation-score floor. Ratchet
   the floor up 1% per release from current baseline; don't aim for 100%.
   `mutmut` is already a dev dep, so no approval needed for this half.
2. **Performance**: Add `benchmarks/` with a `pytest-benchmark` suite measuring
   `enhance_prompt()` p50/p95 latency per tier (Offline / Tactical / Strategic)
   against ~10 representative queries. Check in a baseline JSON. Add a CI job
   that fails if p95 regresses by more than 20% versus baseline.

> **Dependency gate**: `pytest-benchmark` is a new dev dependency and
> `CLAUDE.md §2.2` / §6.4 require ASK-first approval before adding any new
> dependency. Treat that approval as the first step of this roadmap item.

**Effort**: ~1 week.
**Result**: Catches the slow drift that 752 unit tests won't.

### P5e: Build a commercial validation surface (non-engineering)

**Problem**: The compliance scaffolding (NIST AI RMF, EU AI Act, OPA/Rego) is
sized for enterprise but there's no visible evidence enterprises are buying.
An investor's first two questions — "who is using it?" and "who is about to?" —
have no discoverable answers in this repo.

**Action**:
1. Create `case-studies/` with two anonymized integration write-ups
   (Agora IV first; AEGIS second). Include real latency, security-finding,
   and compliance-mode numbers.
2. Add `docs/metrics.md` linking PyPI download trends, GitHub stars, dependent
   repo count. Even small numbers, honestly reported, beat no numbers.
3. Open GitHub Discussions and commit to one weekly office-hours slot.
4. Identify three design-partner orgs (one HIPAA, one TACTICAL/defense, one
   general SaaS); write a one-page outreach pitch for each; send them.

**Effort**: 2–3 weeks of focused BD work.
**Why it's on the technical roadmap**: The codebase can't do BD work for you,
but BD outcomes constrain which features (P5b Path A, P3b adaptive learning)
are worth building.

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

*AIPEA Roadmap | Extracted from SPECIFICATION.md Section 10 | Updated 2026-04-11*
