# AIPEA Logic Coherence Findings

> Audit date: 2026-03-13 | Codebase: v1.2.0 | 7,288 LOC, 12 modules

---

## Finding 1 — CRITICAL: Global Forbidden Model List Missing

**Module**: security.py (ComplianceHandler), enhancer.py
**Spec reference**: SPECIFICATION.md section 3.1.3 (lines ~280, ~885)
**Evidence**:
- Spec documents a global forbidden model list (e.g., `gpt-4o`, `gpt-4o-mini`) that should block certain models across ALL compliance modes
- `security.py:567-573`: GENERAL mode sets `self.allowed_models = []` (empty = all allowed)
- `security.py:587-588`: `validate_model()` returns `True` when `allowed_models` is empty
- `enhancer.py:434`: Comment says "Enforce compliance-mode model restrictions and global forbidden list" but no global list exists
- **No code anywhere implements a global forbidden model list**
- GENERAL mode permits every model including those the spec forbids

**Impact**: Models the spec explicitly forbids can be used in GENERAL mode without restriction
**Remediation**: Add a `GLOBAL_FORBIDDEN_MODELS` set to `ComplianceHandler` and check it in `validate_model()` before the mode-specific allowlist
**Resolution**: ✅ RESOLVED — Added `GLOBAL_FORBIDDEN_MODELS: ClassVar[set[str]]` to `ComplianceHandler`; `validate_model()` checks it before mode-specific allowlist. Tests updated across security, enhancer, and live test suites.

---

## Finding 2 — HIGH: Duplicate QUERY_TYPE_PATTERNS Divergence

**Module**: analyzer.py:403-435, engine.py:479-510
**Evidence**:
- `analyzer.py` `QUERY_TYPE_PATTERNS[TECHNICAL]` has **4 patterns**:
  1. `code|program|api|function|class|method|debug|error|exception`
  2. `python|javascript|java|c++|rust|golang|typescript`
  3. `database|sql|query|schema|table|index`
  4. `implement|develop|build|create|design` **(missing in engine)**
- `engine.py` `QUERY_PATTERNS[TECHNICAL]` has **3 patterns** (missing #4)
- Both use `max()` with `QUERY_TYPE_PRIORITY` for tie-breaking
- A query like "implement a REST API" scores TECHNICAL=2 in analyzer (patterns 1+4) but TECHNICAL=1 in engine (pattern 1 only), potentially classifying differently when competing with OPERATIONAL (which matches "implement")

**Impact**: Same query can classify as different types depending on whether analyzer or engine classifies it
**Remediation**: Extract a single canonical pattern set, or have engine import analyzer's patterns
**Resolution**: ✅ RESOLVED — Extracted `QUERY_TYPE_PATTERNS` to `_types.py` as the single source of truth. Both `analyzer.py` and `engine.py` now import from `_types`.

---

## Finding 3 — HIGH: Knowledge Base Search Ignores Query Text

**Module**: knowledge.py:313-348
**Evidence**:
- `_search_sync()` SQL is `ORDER BY relevance_score DESC` with optional `WHERE domain = ?`
- The `query` parameter is used only for logging: `logger.debug(f"Searching knowledge base: query_len={len(query)}")`
- No FTS, no LIKE clause, no textual matching of any kind
- Code docstring acknowledges this: "Note: This is a simple relevance-based search. In production, a more sophisticated text search (FTS5) or embedding-based similarity search would be used."
- Result: searching for "Python async patterns" returns the same top-N nodes as searching for "military communication protocols" (if same domain or no domain filter)

**Impact**: Offline context enrichment returns irrelevant results for specific queries
**Remediation**: Add SQLite FTS5 virtual table for textual matching, or at minimum a LIKE filter
**Resolution**: ✅ RESOLVED — Added FTS5 virtual table (`knowledge_fts`) with auto-sync on insert and migration rebuild. `_search_sync()` now tries FTS MATCH first, falls back to relevance_score ordering.

---

## Finding 4 — MEDIUM: Private Method Access Across Class Boundaries

**Module**: analyzer.py:492-501
**Evidence**:
- `QueryAnalyzer.analyze()` directly calls private methods on `self._router`:
  - Line 492: `self._router._calculate_complexity(query)`
  - Line 495: `self._router._detect_temporal_needs(query)`
  - Line 498: `self._router._identify_domain(query)`
  - Line 501: `self._router._calculate_confidence(query, complexity, domains)`
- These are underscore-prefixed methods, indicating they are implementation details of `QueryRouter`

**Impact**: Tight coupling between QueryAnalyzer and QueryRouter internals; refactoring QueryRouter private methods would break QueryAnalyzer
**Remediation**: Promote these to public methods on QueryRouter, or add a dedicated analysis method that returns all needed values
**Resolution**: ✅ RESOLVED — Promoted `_calculate_complexity`, `_detect_temporal_needs`, `_identify_domain`, `_calculate_confidence` to public methods. Updated all callers and tests.

---

## Finding 5 — MEDIUM: Complexity-Tier Conflation in Offline Mode

**Module**: enhancer.py:521-526
**Evidence**:
- `complexity_map = {ProcessingTier.OFFLINE: "simple", ProcessingTier.TACTICAL: "medium", ProcessingTier.STRATEGIC: "complex"}`
- When `offline_required=True`, `processing_tier` is forced to `OFFLINE` (line 508)
- This means `complexity` is always `"simple"` for offline queries
- A complex query forced offline by security level gets the "simple" template: "This is a straightforward query requiring a direct, accurate response"
- The actual query analysis may show `complexity=0.85` but the template ignores this

**Impact**: Complex queries processed offline receive inappropriately simplified prompt templates
**Remediation**: Use the actual `analysis.complexity` score to select the template, independent of processing tier
**Resolution**: ✅ RESOLVED — Replaced tier-based `complexity_map` with `analysis.complexity` score thresholds (≥0.7 complex, ≥0.4 medium, else simple).

---

## Finding 6 — MEDIUM: Military-Contextual Domain Mapping Defaults

**Module**: enhancer.py:869-877
**Evidence**:
- `domain_map` for offline context:
  - `QueryType.OPERATIONAL` → `KnowledgeDomain.LOGISTICS`
  - `QueryType.STRATEGIC` → `KnowledgeDomain.MILITARY`
  - `QueryType.RESEARCH` → `KnowledgeDomain.GENERAL`
- An operational query like "how to configure AWS Lambda" maps to LOGISTICS domain
- A strategic query like "long-term React migration plan" maps to MILITARY domain
- These defaults reflect AIPEA's military/defense origin but are inappropriate for general-purpose use

**Impact**: Non-military operational/strategic queries retrieve irrelevant offline knowledge
**Remediation**: Default OPERATIONAL and STRATEGIC to GENERAL, or use domain indicators from query analysis to select the appropriate KnowledgeDomain
**Resolution**: ✅ RESOLVED — Changed OPERATIONAL→GENERAL and STRATEGIC→GENERAL in `domain_map`.

---

## Finding 7 — MEDIUM: Dual Model-Family Detection Systems

**Module**: enhancer.py:224-249, search.py:268-297
**Evidence**:
- `enhancer.get_model_family()` detects: openai, claude, gemini, llama, general (5 families)
- `search.SearchContext.formatted_for_model()` detects: openai/gpt, claude/anthropic, generic (3 families)
- Divergence examples:
  - "llama-3.3-70b" → `get_model_family` returns "llama", `formatted_for_model` uses generic format
  - "gemma-3n" → `get_model_family` returns "gemini", `formatted_for_model` uses generic format
- Also `search.parse_model_type()` returns `ModelType` enum (4 values) — a third detection system

**Impact**: Model-specific formatting may not be applied consistently across the pipeline
**Remediation**: Centralize model detection into a single function used by both enhancer and search
**Resolution**: ✅ RESOLVED — Moved `get_model_family()` and `MODEL_FAMILY_MAP` to `_types.py`. Both `enhancer.py` and `search.py` now import from `_types`.

---

## Finding 8 — MEDIUM: `__all__` Export Count Drift

**Module**: __init__.py:73-108
**Evidence**:
- `__init__.py` `__all__` contains **34 symbols** (counted from source)
- SPECIFICATION.md section 11.1 states **32 symbols**
- The 2 extra symbols added since the spec was written are likely `EnhancedRequest` and `reset_enhancer` (added during the offline KB and Ollama integration work)

**Impact**: Spec is stale; consumers relying on spec may miss new exports
**Remediation**: Update SPECIFICATION.md section 11.1 to reflect 34 exports
**Resolution**: ✅ RESOLVED — Updated SPECIFICATION.md section 11.1 from "32 symbols" to "34 symbols".

---

## Finding 9 — LOW: ProcessingTier.confidence_threshold Unused

**Module**: _types.py:23-31
**Evidence**:
- `ProcessingTier.confidence_threshold` property defined with per-tier values (0.70, 0.85, 0.95)
- Grep across entire `src/aipea/` directory: only referenced in `_types.py` itself
- Not used in analyzer, engine, enhancer, or any other module
- Likely intended for confidence-based tier escalation but never wired in

**Impact**: Dead code; consumers may assume confidence thresholds are enforced when they are not
**Remediation**: Either wire into tier escalation logic or remove the property
**Resolution**: ✅ RESOLVED — Removed `confidence_threshold` property from `ProcessingTier` enum.

---

## Finding 10 — LOW: KnowledgeSearchResult Exported but Never Constructed

**Module**: knowledge.py:110-126, __init__.py:43,85
**Evidence**:
- `KnowledgeSearchResult` dataclass defined in knowledge.py with fields: nodes, query, domain_filter, total_matches
- Exported in knowledge.py `__all__` and re-exported in `__init__.py` `__all__`
- Grep shows it is never instantiated anywhere in the codebase
- `OfflineKnowledgeBase.search()` returns `list[KnowledgeNode]`, not `KnowledgeSearchResult`

**Impact**: Dead export; consumers might expect it to be returned from search but it never is
**Remediation**: Either use it as the return type for search() or remove from exports
**Resolution**: ✅ RESOLVED — `OfflineKnowledgeBase.search()` now returns `KnowledgeSearchResult`. All callers updated to use `.nodes` attribute.

---

## Finding 11 — LOW: TierProcessor ABC Has Single Implementation

**Module**: engine.py:424-457
**Evidence**:
- `TierProcessor` ABC defines `process()` and `tier` abstract methods
- Only `OfflineTierProcessor` implements it (engine.py:464)
- Original design had Tactical and Strategic processors (removed during extraction from Agora)
- The ABC adds no value with a single implementation

**Impact**: Over-abstraction; adds cognitive overhead without benefit
**Remediation**: Keep if Tactical/Strategic processors are on the roadmap (they are per docs/ROADMAP.md), otherwise collapse into OfflineTierProcessor
**Resolution**: ✅ RESOLVED — Added docstring to `TierProcessor` ABC documenting planned subclasses (ROADMAP.md P2/P3).

---

## Finding 12 — LOW: OllamaOfflineClient.generate() Silently Ignores Parameters

**Module**: engine.py:268-274
**Evidence**:
- `generate()` accepts `max_tokens: int = 512` and `temperature: float = 0.7`
- Neither parameter is passed to the `ollama run` subprocess command
- Comment states: "reserved for future REST API migration"
- The `ollama run` CLI does not support these flags; they would require the REST API

**Impact**: Callers may set max_tokens/temperature expecting them to have effect; they don't
**Remediation**: Document in the docstring that these are currently ignored, or raise a warning when non-default values are passed
**Resolution**: ✅ RESOLVED — Added `logger.warning()` when non-default `max_tokens` or `temperature` values are passed to `generate()`.

---

## Finding 13 — LOW: FEDRAMP Scan Path Identical to GENERAL

**Module**: security.py:442-483
**Evidence**:
- `SecurityScanner.scan()` dispatches extra checks for:
  - HIPAA: `_check_phi()` (line 460-461)
  - TACTICAL: `_check_classified_markers()` (line 464-466)
  - FEDRAMP: no specific checks
- FEDRAMP mode only differs in `ComplianceHandler` config (allowed_models, retention days)
- The scan itself runs identically to GENERAL mode
- `ComplianceHandler._configure_for_mode()` FEDRAMP branch has a comment: "UNSUPPORTED STUB"

**Impact**: FEDRAMP users may expect FEDRAMP-specific security scanning that doesn't exist
**Remediation**: Document clearly in enhancer and public API docs that FEDRAMP is a configuration-only stub
**Resolution**: ✅ RESOLVED — Added `logger.warning()` in `enhance()` when FEDRAMP mode is selected, documenting it as an unsupported stub.

---

## Finding 14 — LOW: _stats Dict Mutated Without Thread Locks

**Module**: enhancer.py:354-362, 421-422, 436-437, 546-549
**Evidence**:
- `self._stats` is a plain dict with integer/float counters
- Mutated with `+= 1` operations in `enhance()` (lines 421, 436, 546-548)
- No lock protection around mutations
- `_update_avg_time()` (line 1064-1078) reads and writes `_stats` without locking
- Under CPython GIL, simple dict operations are atomic, but:
  - `+= 1` is NOT atomic (it's a read-modify-write)
  - Multiple async tasks could interleave in pathological cases
  - This assumption breaks if AIPEA ever runs on non-CPython runtimes

**Impact**: Potential race condition in stats tracking (cosmetic, not security-critical)
**Remediation**: Use `threading.Lock` around stats mutations, or use `collections.Counter` with atomic operations
**Resolution**: ✅ RESOLVED — Added `_stats_lock = threading.Lock()` to `AIPEAEnhancer.__init__()`. All `_stats` mutations and reads wrapped in `with self._stats_lock:`.
