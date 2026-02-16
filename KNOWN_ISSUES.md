# KNOWN_ISSUES.md — Bug Hunt Findings (Wave 1: 2026-02-15, Wave 2: 2026-02-15)

Issues found during hybrid bug hunts but deferred (low priority or design decisions).

## Wave 2 Deferred Findings (2026-02-15)

### 8. NaN values bypass `__post_init__` clamping in QueryAnalysis and SearchResult/SearchContext
- **File**: `src/aipea/models.py:41-60`, `src/aipea/search.py:100-134`
- **Severity**: LOW | **Confidence**: HIGH
- **Reason deferred**: Requires `float('nan')` to enter the system via direct construction or malformed API response. `max(0.0, min(1.0, nan))` returns `nan` in Python, so clamping is a no-op. Downstream NaN comparisons silently return False, causing unpredictable routing. Fix: add `math.isnan()` check before clamping.

### 9. `_check_ollama_availability` async race condition on concurrent first calls
- **File**: `src/aipea/engine.py:790-816`
- **Severity**: LOW | **Confidence**: HIGH
- **Reason deferred**: Sets `_ollama_checked = True` before first `await`, so concurrent callers skip initialization while first caller is still probing. Second caller falls back to templates. Fix: use `asyncio.Lock()` for double-checked locking.

### 10. `close()` does not acquire `_db_lock` during connection closure
- **File**: `src/aipea/knowledge.py:176-186`
- **Severity**: LOW | **Confidence**: MEDIUM
- **Reason deferred**: Only exploitable in multi-threaded access where shutdown races with active operations. `contextlib.suppress(Exception)` partially mitigates. Fix: acquire `_db_lock` in `close()`.

### 11. Exa API scores may not be in [0, 1] range causing log noise
- **File**: `src/aipea/search.py:422`
- **Severity**: LOW | **Confidence**: MEDIUM
- **Reason deferred**: Exa neural search scores are not guaranteed [0, 1]. `SearchResult.__post_init__` clamps but emits warning per result, creating log noise. Fix: normalize score before constructing SearchResult.

## Wave 1 Deferred Findings

### 1. `_stats` dict not thread-safe on AIPEAEnhancer singleton
- **File**: `src/aipea/enhancer.py:348-355, 843-894`
- **Severity**: MEDIUM | **Confidence**: MEDIUM
- **Reason deferred**: Stats are approximate by nature; adding locks would add overhead to every enhance() call. Document that stats are best-effort.

### 2. MODEL_FAMILY_MAP returns "gpt" instead of "openai" for GPT-5.x models
- **File**: `src/aipea/enhancer.py:187-189`
- **Severity**: LOW | **Confidence**: HIGH
- **Reason deferred**: Benign in practice — downstream code uses substring matching (`"gpt" in model_lower`), so `"gpt"` still matches. Would only matter if exact equality (`== "openai"`) were used.

### 3. `merge_with` produces non-zero confidence with zero results
- **File**: `src/aipea/search.py:272-280`
- **Severity**: LOW | **Confidence**: HIGH
- **Reason deferred**: Only triggered by constructing SearchContext with non-zero confidence but empty results, which doesn't happen in normal usage.

### 4. `_multi_source_search` runs providers sequentially instead of concurrently
- **File**: `src/aipea/search.py:954-955`
- **Severity**: LOW | **Confidence**: HIGH
- **Reason deferred**: Performance optimization, not a correctness bug. Would require adding `import asyncio` to search.py.

### 5. Classified markers "SECRET" and "CONFIDENTIAL" may cause false positives
- **File**: `src/aipea/security.py:239-245`
- **Severity**: MEDIUM | **Confidence**: MEDIUM
- **Reason deferred**: Design decision — these markers are only checked in TACTICAL mode. Users in TACTICAL mode are expected to be in military/defense contexts where these words have specific meaning.

### 6. Classified marker check only runs in TACTICAL mode
- **File**: `src/aipea/security.py:457-459`
- **Severity**: LOW | **Confidence**: MEDIUM
- **Reason deferred**: Intentional design — compliance modes have scoped checks. Running classified checks in all modes would generate noise in GENERAL usage.

### 7. OfflineKnowledgeBase async methods block the event loop on SQLite I/O
- **File**: `src/aipea/knowledge.py:285-644`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Reason deferred**: Architectural concern requiring significant refactor (wrap all methods with asyncio.to_thread or migrate to aiosqlite). The current approach works for low-concurrency use cases.
