# KNOWN_ISSUES.md — Bug Hunt Findings (Waves 1-9 + Quality Gate: 2026-02-17)

Issues found during hybrid bug hunts. Status: FIXED, DEFERRED, or INTENTIONAL.

## Wave 9 Fixes (2026-02-17) — 2 issues resolved

### 34. `ExaSearchProvider.search()` crashes on `text: null` Exa results (TypeError on slice) — FIXED
- **File**: `src/aipea/search.py:458-462`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Codex gpt-5.3-codex
- **Fix**: When Exa returns `{"text": null}`, `item.get("text")` returns `None` (key exists), not the fallback. `None[:1000]` raised `TypeError`. Refactored to explicit null check with `summary` fallback and safe `str()` conversion before slicing.

### 35. `enhance_for_models` returns empty dict when enhancement is disabled (passthrough conflated with blocked) — FIXED
- **File**: `src/aipea/enhancer.py:615-622`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Claude sweep agent
- **Fix**: The `if not base_result.was_enhanced:` check conflated passthrough results (enhancement disabled, valid query) with blocked results (security threat). Added `original_query != enhanced_prompt` condition to distinguish passthrough (prompt equals query) from blocked (prompt is the block message). Passthrough queries now proceed to per-model formatting.

### 37. `FirecrawlProvider.search()` and `deep_research()` crash on null markdown/content (same class as #34) — FIXED
- **File**: `src/aipea/search.py:588,702`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Quality gate ultrathink (wave 9)
- **Fix**: Same pattern as #34. `item.get("markdown")` and `source.get("content")` return `None` when the key exists with a null value, then `None[:1000]` raises `TypeError`. Fixed with `or ""` fallback and `str()` safety conversion. Regression test added.

## Wave 9 — Deferred

### 36. `enhance_for_models` bakes base model's family-specific prompt template into other models — DEFERRED
- **File**: `src/aipea/enhancer.py:604-632`
- **Severity**: LOW | **Confidence**: MEDIUM
- **Source**: Claude sweep agent
- **Rationale**: The base enhancement at line 605 formats the prompt with `base_model`'s family-specific template. Non-base models receive this same prompt with an additional layer of their own family instructions via `create_model_specific_prompt`. This means non-base models get mismatched instructions (inner layer from base model family, outer layer from their own). The impact is cosmetic (slightly redundant/mismatched soft instructions), not causing crashes or data loss. Fix would require per-model enhancement or a "generic" base template.

## Wave 8 Fixes (2026-02-16) — 2 issues resolved

### 32. `api_key` PII pattern misses common API key formats — FIXED
- **File**: `src/aipea/security.py:228`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Claude sweep agent
- **Fix**: Split single `api_key` pattern into three separate patterns: `api_key` (catches `api_key=VALUE` with `:=` separators), `sk_key` (catches `sk-` prefixed keys including `sk-proj-`), and `bearer_token` (catches `bearer TOKEN` with dots/dashes). The original pattern required 20+ alphanumeric chars immediately after the prefix, missing separator characters and modern key formats.

### 33. `SearchResult.__post_init__` crashes on non-numeric score (TypeError on `math.isnan`) — FIXED
- **File**: `src/aipea/search.py:121`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Codex gpt-5.3-codex
- **Fix**: Added `try/except (TypeError, ValueError)` guard before NaN check, coercing non-numeric scores to `0.0` via `float()`. Prevents `TypeError` when upstream provider returns `score: null` (Python `None`), which previously caused the entire provider search to silently degrade to empty results via the broad exception handler.

## Wave 8 — False Positive

### `add_knowledge` ON CONFLICT doesn't update `last_accessed` — NOT A BUG
- **File**: `src/aipea/knowledge.py:472-477`
- **Source**: Claude sweep agent
- **Rationale**: `last_accessed` tracks search access, not re-insertion. Existing regression test `TestAddKnowledgeLastAccessedPreservation::test_readd_does_not_update_last_accessed` explicitly asserts this behavior. Re-adding content is an idempotent operation, not an "access".

## Deferred Issue Resolution (2026-02-16) — 9 issues resolved

### 7. OfflineKnowledgeBase async methods block the event loop on SQLite I/O — FIXED
- **File**: `src/aipea/knowledge.py`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Fix**: Wrapped all 9 async methods with `asyncio.to_thread()`, extracting synchronous DB work into private `_sync_*` methods. The `threading.RLock` serializes concurrent thread pool calls. `check_same_thread=False` was already set.

### 12. Duplicate `SearchStrategy` enum in `_types.py` and `search.py` — FIXED
- **File**: `src/aipea/_types.py:46-52`, `src/aipea/search.py` (removed)
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Fix**: Unified to single `SearchStrategy` in `_types.py` with string values (`"none"`, `"quick_facts"`, etc.). Removed duplicate enum from `search.py`. All consumers now import from `_types.py`.

### 13. `engine.py` re-exports `SearchStrategy` from `search.py` instead of `_types.py` — FIXED
- **File**: `src/aipea/engine.py:39`
- **Severity**: LOW | **Confidence**: HIGH
- **Fix**: Changed import from `aipea.search` to `aipea._types` for `SearchStrategy`. Resolved as part of #12 unification.

### 14. No test for publicly-exported `SearchStrategy` from `_types` — FIXED
- **File**: `tests/test_search.py`
- **Severity**: LOW | **Confidence**: HIGH
- **Fix**: Added `test_public_api_import` test verifying `from aipea import SearchStrategy` works, has 4 members including NONE, and uses string values. Updated existing tests for 4-member enum.

### 16. OpenAI/Generic formatters lack escaping vs Anthropic formatter — FIXED
- **File**: `src/aipea/search.py`
- **Severity**: LOW | **Confidence**: MEDIUM
- **Fix**: Added `_escape_markdown()` for OpenAI formatter (escapes `|`, `[`, `]`, `` ` ``) and `_escape_plaintext()` for generic formatter (escapes leading digit-period patterns). Anthropic formatter already had `html.escape()`.

### 19. `_is_regex_safe` rejects possessive quantifiers valid in Python 3.11+ — FIXED
- **File**: `src/aipea/security.py:279`
- **Severity**: LOW | **Confidence**: MEDIUM
- **Fix**: Removed the overly-broad `r"\+\+"` pattern from `_DANGEROUS_PATTERNS`. The existing nested quantifier detection and compilation check already catch actual dangerous patterns. Possessive quantifiers like `\d++` are now accepted.

### 20. Unvalidated `search_context` type in `EnhancedQuery` — FIXED
- **File**: `src/aipea/engine.py:596-604`
- **Severity**: LOW | **Confidence**: MEDIUM
- **Fix**: Added runtime type guard in `__post_init__()` — if `search_context` is not `None` and not a `SearchContext` instance, it's logged and set to `None`.

### 22. `QueryAnalysis.to_dict()` serialization inconsistency for search_strategy — FIXED
- **File**: `src/aipea/models.py:87`
- **Severity**: LOW | **Confidence**: HIGH
- **Fix**: Changed `.name` to `.value` for `search_strategy` serialization. Now returns `"quick_facts"` (string value) instead of `"QUICK_FACTS"` (enum name), consistent with other enum serialization in `to_dict()`.

### 31. `_classify_query_type` tie-breaking depends on dict insertion order — FIXED
- **File**: `src/aipea/analyzer.py:536-539`, `src/aipea/engine.py:810-813`
- **Severity**: LOW | **Confidence**: MEDIUM
- **Fix**: Added `QUERY_TYPE_PRIORITY` dict in `_types.py` with explicit priority ordering (TECHNICAL > RESEARCH > ANALYTICAL > ...). The `max()` call now uses `(score, -priority)` as the sort key for deterministic tie-breaking. Both `analyzer.py` and `engine.py` import from the single source of truth.

## Wave 7 Fixes (2026-02-16) — 3 issues resolved

### 28. NaN `confidence_score` bypasses clamping in `engine.py` `SearchContext` — FIXED
- **File**: `src/aipea/engine.py:395`
- **Severity**: LOW | **Confidence**: HIGH
- **Fix**: Added `math.isnan()` guard before clamping, matching the pattern used in `models.py` and `search.py` (issue #8). NaN values now default to 0.0.

### 29. NaN `confidence` bypasses clamping in `engine.py` `EnhancedQuery` — FIXED
- **File**: `src/aipea/engine.py:588`
- **Severity**: LOW | **Confidence**: HIGH
- **Fix**: Added `math.isnan()` guard before clamping. Same class of bug as #28, both missed during #8 fix.

### 30. `enhance_for_models` runs unnecessary base enhancement when no models are compliant — FIXED
- **File**: `src/aipea/enhancer.py:555`
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
- **File**: `src/aipea/security.py:255`
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
- **File**: `src/aipea/enhancer.py:181-189`
- **Rationale**: Downstream code uses substring matching (`"gpt" in model_lower`), so `"gpt"` still matches correctly.

### 3. `merge_with` produces non-zero confidence with zero results — INTENTIONAL
- **File**: `src/aipea/search.py:298-318`
- **Rationale**: Only triggered by constructing SearchContext with non-zero confidence but empty results, which doesn't happen in normal usage.

### 5. Classified markers "SECRET"/"CONFIDENTIAL" may cause false positives — INTENTIONAL
- **File**: `src/aipea/security.py:242-248`
- **Rationale**: TACTICAL mode is for military/defense contexts where these words have specific meaning. Conservative by design.

### 6. Classified marker check only runs in TACTICAL mode — INTENTIONAL
- **File**: `src/aipea/security.py:467-470`
- **Rationale**: Intentional scoping per compliance mode. Running classified checks in all modes would generate noise in GENERAL usage.

### 11. Exa API scores may not be in [0, 1] range causing log noise — INTENTIONAL
- **File**: `src/aipea/search.py:101-118`
- **Rationale**: Clamping already handles this; log noise is minor and useful for monitoring.

## Deferred Findings (0 remaining)

All previously deferred issues have been resolved. See "Deferred Issue Resolution" section above.
