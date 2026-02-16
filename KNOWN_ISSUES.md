# KNOWN_ISSUES.md — Bug Hunt Findings (2026-02-15)

Issues found during hybrid bug hunt but deferred (low priority or design decisions).

## Deferred Findings

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
