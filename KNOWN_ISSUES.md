# KNOWN_ISSUES.md — Bug Hunt Findings (Waves 1-7 + Quality Gate: 2026-02-16)

Issues found during hybrid bug hunts. Status: FIXED, DEFERRED, or INTENTIONAL.

## Wave 7 Fixes (2026-02-16) — 3 issues resolved

### 28. NaN `confidence_score` bypasses clamping in `engine.py` `SearchContext` — FIXED
- **File**: `src/aipea/engine.py:391-394`
- **Severity**: LOW | **Confidence**: HIGH
- **Fix**: Added `math.isnan()` guard before clamping, matching the pattern used in `models.py` and `search.py` (issue #8). NaN values now default to 0.0.

### 29. NaN `confidence` bypasses clamping in `engine.py` `EnhancedQuery` — FIXED
- **File**: `src/aipea/engine.py:583-585`
- **Severity**: LOW | **Confidence**: HIGH
- **Fix**: Added `math.isnan()` guard before clamping. Same class of bug as #28, both missed during #8 fix.

### 30. `enhance_for_models` runs unnecessary base enhancement when no models are compliant — FIXED
- **File**: `src/aipea/enhancer.py:585-597`
- **Severity**: LOW | **Confidence**: HIGH
- **Source**: Codex gpt-5.3-codex
- **Fix**: Pre-filter `model_ids` to compliance-approved models and return early if none are compliant, avoiding unnecessary processing and side effects.

## Wave 6 Fixes (2026-02-16) — 12 issues resolved

### 4. `_multi_source_search` runs providers sequentially instead of concurrently — FIXED
- **File**: `src/aipea/search.py`
- **Fix**: Replaced sequential `await` calls with `asyncio.gather()` for concurrent execution.

### 8. NaN values bypass `__post_init__` clamping — FIXED
- **Files**: `src/aipea/models.py`, `src/aipea/search.py`
- **Fix**: Added `math.isnan()` checks before clamping in `QueryAnalysis`, `SearchResult`, and `SearchContext`.

### 9. `_check_ollama_availability` async race condition — FIXED
- **File**: `src/aipea/engine.py`
- **Fix**: Added `asyncio.Lock()` with double-checked locking to prevent concurrent first-call races.

### 10. `close()` does not acquire `_db_lock` — FIXED
- **File**: `src/aipea/knowledge.py`
- **Fix**: Wrapped `close()` body with `self._db_lock` acquisition.

### 15. `num_results=0` produces confidence `0.0` despite returned results — FIXED
- **File**: `src/aipea/search.py`
- **Fix**: Clamped `num_results = max(1, num_results)` at start of both `ExaSearchProvider.search` and `FirecrawlProvider.search`.

### 17. Blocked/passthrough paths skip `compliance_distribution` stats update — FIXED
- **File**: `src/aipea/enhancer.py`
- **Fix**: Added `compliance_distribution` increment before each early return (passthrough, model-blocked, security-blocked).

### 18. Unreachable temporal suggestion branch — FIXED
- **File**: `src/aipea/analyzer.py`
- **Fix**: Removed the dead `if analysis.needs_current_info and not analysis.temporal_markers:` block from `suggest_enhancements`.

### 21. Dead `_should_escalate` method never called — FIXED
- **File**: `src/aipea/analyzer.py`
- **Fix**: Deleted the entire `_should_escalate` method (~35 lines of dead code).

### 23. `_detect_entities` recompiles regex per call — FIXED
- **File**: `src/aipea/analyzer.py`
- **Fix**: Moved `cap_pattern` and `tech_pattern` compilation to `QueryAnalyzer.__init__` as instance attributes.

### 24. `\r` carriage return bypasses conversation separator injection detection — FIXED
- **File**: `src/aipea/security.py:253`
- **Fix**: Changed `\n` to `[\r\n]` in injection pattern to detect carriage return bypasses.

### 25. `search()` limit parameter allows negative values (LIMIT -1 returns all rows) — FIXED
- **File**: `src/aipea/knowledge.py:310`
- **Fix**: Added `limit = max(1, limit)` clamp before SQL query.

### 26. `HTTP_TIMEOUT` accepts `inf`, `nan`, negative, and zero values — FIXED
- **File**: `src/aipea/search.py:43-44`
- **Fix**: Added validation `0 < _raw_timeout < float("inf")`, defaults to 30.0 on invalid.

### 27. `_is_regex_safe` fails to detect character class nested quantifier ReDoS — FIXED
- **File**: `src/aipea/security.py`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Fix**: Added char-class-in-quantified-group detection to `_is_regex_safe()` and `_DANGEROUS_PATTERNS`. Patterns like `([^)]+)+` are now rejected before compilation. See also #19 (possessive quantifier false positives remain deferred).

## Intentional Design Decisions (documented, not bugs)

### 1. `_stats` dict not thread-safe on AIPEAEnhancer singleton — INTENTIONAL
- **File**: `src/aipea/enhancer.py:349-357`
- **Rationale**: Async model is single-threaded; stats are best-effort. Adding locks would add overhead to every enhance() call.

### 2. MODEL_FAMILY_MAP returns "gpt" instead of "openai" for GPT-5.x models — INTENTIONAL
- **File**: `src/aipea/enhancer.py:187-189`
- **Rationale**: Downstream code uses substring matching (`"gpt" in model_lower`), so `"gpt"` still matches correctly.

### 3. `merge_with` produces non-zero confidence with zero results — INTENTIONAL
- **File**: `src/aipea/search.py:269-289`
- **Rationale**: Only triggered by constructing SearchContext with non-zero confidence but empty results, which doesn't happen in normal usage.

### 5. Classified markers "SECRET"/"CONFIDENTIAL" may cause false positives — INTENTIONAL
- **File**: `src/aipea/security.py:240-246`
- **Rationale**: TACTICAL mode is for military/defense contexts where these words have specific meaning. Conservative by design.

### 6. Classified marker check only runs in TACTICAL mode — INTENTIONAL
- **File**: `src/aipea/security.py:465-468`
- **Rationale**: Intentional scoping per compliance mode. Running classified checks in all modes would generate noise in GENERAL usage.

### 11. Exa API scores may not be in [0, 1] range causing log noise — INTENTIONAL
- **File**: `src/aipea/search.py:103-110`
- **Rationale**: Clamping already handles this; log noise is minor and useful for monitoring.

## Deferred Findings (9 remaining)

### 7. OfflineKnowledgeBase async methods block the event loop on SQLite I/O
- **File**: `src/aipea/knowledge.py:285-644`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Reason deferred**: Architectural concern requiring significant refactor (wrap all methods with asyncio.to_thread or migrate to aiosqlite). The current approach works for low-concurrency use cases.

### 12. Duplicate `SearchStrategy` enum in `_types.py` and `search.py` creates silent type mismatch
- **File**: `src/aipea/_types.py:46-52`, `src/aipea/search.py:54-63`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Reason deferred**: Architectural issue requiring coordinated rename. `_types.SearchStrategy` (auto() int values, has NONE) vs `search.SearchStrategy` (string values, no NONE). `engine.py` re-exports the wrong one. Fix: unify into single enum or rename the `search.py` version to `_OrchestratorStrategy`.

### 13. `engine.py` re-exports `SearchStrategy` from `search.py` instead of `_types.py`
- **File**: `src/aipea/engine.py:43, 1700`
- **Severity**: LOW | **Confidence**: HIGH
- **Reason deferred**: Consequence of #12. Blocked until enum unification.

### 14. No test for publicly-exported `SearchStrategy` from `_types`
- **File**: `tests/test_search.py:40-51`
- **Severity**: LOW | **Confidence**: HIGH
- **Reason deferred**: Blocked by #12 (enum unification).

### 16. OpenAI/Generic formatters lack markdown escaping vs Anthropic formatter
- **File**: `src/aipea/search.py:184-209, 245-267`
- **Severity**: LOW | **Confidence**: MEDIUM
- **Reason deferred**: Cosmetic inconsistency, low impact.

### 19. `_is_regex_safe` rejects possessive quantifiers valid in Python 3.11+
- **File**: `src/aipea/security.py:277-286`
- **Severity**: LOW | **Confidence**: MEDIUM
- **Reason deferred**: No current patterns use possessive quantifiers. Security-sensitive change. Note: the related false *negative* (char class patterns bypassing detection) was fixed in #27.

### 20. Unvalidated `search_context` type in `EnhancedQuery`
- **File**: `src/aipea/engine.py:1020-1078`
- **Severity**: LOW | **Confidence**: MEDIUM
- **Reason deferred**: Low confidence, edge case.

### 22. `QueryAnalysis.to_dict()` serialization inconsistency for search_strategy
- **File**: `src/aipea/models.py:75`
- **Severity**: LOW | **Confidence**: HIGH
- **Reason deferred**: Blocked by #12 (SearchStrategy enum unification).

### 31. `_classify_query_type` tie-breaking depends on dict insertion order
- **File**: `src/aipea/analyzer.py:526-536`
- **Severity**: LOW | **Confidence**: MEDIUM
- **Reason deferred**: When two QueryType values match the same number of patterns, `max()` returns the first inserted key (TECHNICAL wins by default). Not a crash or security issue — it's a design decision about implicit priority. Same pattern exists in `engine.py:789`.
