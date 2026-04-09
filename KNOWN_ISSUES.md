# KNOWN_ISSUES.md — Bug Hunt Findings (Waves 1-16 + Quality Gate: 2026-03-14)

Issues found during hybrid bug hunts. Status: FIXED, DEFERRED, or INTENTIONAL.

## Wave 16 Fixes (2026-03-14) — 4 bugs fixed, 3 deferred

### 75. AIPEAEnhancer leaks SQLite connection (no close/context manager) — FIXED
- **File**: `src/aipea/enhancer.py:326-336`
- **Severity**: MEDIUM | **Confidence**: 0.90
- **Source**: Claude sweep agent (facade/entry layer, wave 16)
- **Fix**: Added `close()` method that releases `_offline_kb` SQLite connection, plus `__enter__`/`__exit__` for context manager support. Idempotent — safe to call multiple times. `reset_enhancer()` now delegates to `close()`. 3 regression tests added.

### 76. dotenv parser mishandles quoted values with embedded matching quotes — FIXED
- **File**: `src/aipea/config.py:114-136`
- **Severity**: MEDIUM | **Confidence**: 0.80
- **Source**: Claude sweep agent (core modules, wave 16) + quality gate ultrathink
- **Fix**: Old code assumed `raw_value[-1]` was the closing quote, incorrectly stripping values like `'val1' 'val2'` to `val1' 'val2`. New code scans character by character for the first unescaped matching close-quote. Also fixed: unescape no longer runs on values with missing closing quotes. 6 regression tests added.

### 77. TOCTOU race in `_prune_low_relevance_sync` — FIXED
- **File**: `src/aipea/knowledge.py:940-969`
- **Severity**: MEDIUM | **Confidence**: 0.75
- **Source**: Claude sweep agent (core modules, wave 16)
- **Fix**: Old code used SELECT rowids + DELETE by re-evaluated subquery, which could diverge if data changed between queries (leaving orphaned FTS entries). New code SELECTs both `id` and `rowid`, then DELETEs by exact `id` list and cleans FTS by exact `rowid` list. 1 regression test added.

### 78. Doctor connectivity produces duplicate output lines — FIXED
- **File**: `src/aipea/cli.py:170-219,387-395`
- **Severity**: LOW | **Confidence**: 0.95
- **Source**: Claude sweep agent (facade/entry layer, wave 16)
- **Fix**: `_test_exa_connectivity` and `_test_firecrawl_connectivity` unconditionally printed status, then `_doctor_connectivity` also printed via `chk.ok()`/`chk.fail()`. Added `silent: bool = False` keyword param; doctor passes `silent=True`. 1 regression test added.

### Wave 16 — Deferred (3 LOW severity)

### 79. Exa API scores silently clamped to [0,1] instead of normalized — DEFERRED
- **File**: `src/aipea/search.py:583-589`
- **Severity**: LOW | **Confidence**: 0.70
- **Source**: Claude sweep agent (core modules, wave 16)
- **Rationale**: Already tracked as intentional design decision #11. Clamping produces acceptable results; normalization would require collecting all scores first.

### 80. Storage stats reads not atomic (node_count vs file_size) — DEFERRED
- **File**: `src/aipea/knowledge.py:884-896`
- **Severity**: LOW | **Confidence**: 0.60
- **Source**: Claude sweep agent (core modules, wave 16)
- **Rationale**: Stats are informational only. Minor inconsistency between node count and file size has no functional impact.

### 81. HTTP_TIMEOUT eager vs URL lazy resolution inconsistency — DEFERRED
- **File**: `src/aipea/search.py:113`
- **Severity**: LOW | **Confidence**: 0.55
- **Source**: Claude sweep agent (core modules, wave 16)
- **Rationale**: Timeout is frozen at import time (documented behavior), URLs are lazy. Inconsistent but functional — changing timeout to lazy would be a behavioral change.

## Wave 15 Fixes (2026-03-13) — 5 deferred issues resolved

### 56. Unicode homoglyph bypass of all injection patterns — FIXED (was DEFERRED)
- **File**: `src/aipea/security.py:32-71,474`
- **Severity**: MEDIUM | **Confidence**: 0.85
- **Source**: Claude sweep agent (Opus deep sweep, wave 12)
- **Fix**: Added NFKC normalization + cross-script confusable character mapping (`_CONFUSABLE_MAP` with 35 Cyrillic/Greek-to-Latin entries) before all security checks. Attackers substituting Cyrillic U+043E for Latin 'o' or fullwidth U+FF49 for Latin 'i' now correctly trigger injection detection. 4 regression tests added.

### 73. API URL env vars frozen at import time — FIXED (was DEFERRED)
- **File**: `src/aipea/search.py` (resolvers), `src/aipea/config.py` (fields)
- **Severity**: MEDIUM | **Confidence**: 0.80
- **Source**: Claude sweep agent (core modules, wave 14)
- **Fix**: Removed module-level `EXA_API_URL`/`FIRECRAWL_API_URL` constants. Added lazy resolvers `_resolve_exa_api_url()` and `_resolve_firecrawl_api_url()` that check env vars first, then fall back to `load_config()`. Added `exa_api_url`/`firecrawl_api_url` fields to `AIPEAConfig` with persistence in both `.env` and TOML formats. 7 regression tests added.

### 74. `enhance_for_models()` gives all models the same prompt formatted for the first model — FIXED (was DEFERRED)
- **File**: `src/aipea/enhancer.py:681-708`, `src/aipea/engine.py:920`
- **Severity**: MEDIUM | **Confidence**: 0.90
- **Source**: Claude sweep agent (engine/enhancer, wave 14)
- **Fix**: Added `embed_search_context: bool = True` parameter to `enhance()` and `formulate_search_aware_prompt()`. `enhance_for_models()` now calls `enhance(embed_search_context=False)` to get a clean base prompt, then passes `search_context` to `create_model_specific_prompt()` for per-model formatting (markdown for GPT, XML for Claude, numbered list for generic). 5 regression tests added.

### 41. `aipea check` exits with code 1 when optional API keys are not configured — FIXED (was DEFERRED)
- **File**: `src/aipea/cli.py`
- **Severity**: LOW | **Confidence**: MEDIUM
- **Source**: Claude sweep agent (wave 10)
- **Fix**: Split `issues` list into `errors` (connectivity failures) and `warnings` (missing optional keys). Only `errors` cause exit code 1. Missing API keys now show as warnings but exit 0. 3 regression tests added.

### 42. `doctor` connectivity section uses inconsistent output format — FIXED (was DEFERRED)
- **File**: `src/aipea/cli.py`
- **Severity**: LOW | **Confidence**: HIGH
- **Source**: Claude sweep agent (wave 10)
- **Fix**: Extracted `_doctor_connectivity()` helper that routes through `_DoctorChecks.ok()`/`.fail()`/`.warn()` methods for consistent PASS/WARN/FAIL output format. 1 regression test added.

## Wave 14 Fixes (2026-03-13) — 10 issues resolved

### 64. `task_decomposition` counting/splitting pattern mismatch — FIXED
- **File**: `src/aipea/strategies.py:176,186`
- **Severity**: MEDIUM | **Confidence**: 0.90
- **Source**: Claude sweep agent (types/strategies/CLI)
- **Fix**: Counting regex included `plus` and `as well as` but split regex did not, causing queries like "Build X plus deploy Y plus test Z" to produce a single "Sub-task 1" with the entire query. Added `plus|as\s+well\s+as` to the split pattern. 2 regression tests added.

### 65. `ExaSearchProvider.search()` missing empty query guard — FIXED
- **File**: `src/aipea/search.py:501-520`
- **Severity**: MEDIUM | **Confidence**: 0.85
- **Source**: Claude sweep agent (core modules)
- **Fix**: `FirecrawlProvider.search()` guarded against empty/whitespace queries but `ExaSearchProvider.search()` did not, causing wasteful API calls. Added matching guard. 3 regression tests added.

### 66. `.env` permissions check misses write/execute bits — FIXED
- **File**: `src/aipea/cli.py:306`
- **Severity**: MEDIUM | **Confidence**: 0.85
- **Source**: Claude sweep agent (types/strategies/CLI)
- **Fix**: Doctor security check only tested `S_IRGRP | S_IROTH` (group/other read), missing write and execute bits. A file with mode `0o620` would pass as "safe". Now checks all 6 group/other permission bits.

### 67. `.gitignore` check uses substring match — FIXED
- **File**: `src/aipea/cli.py:296`
- **Severity**: LOW | **Confidence**: 0.80
- **Source**: Claude sweep agent (types/strategies/CLI)
- **Fix**: `if ".env" in content` matched `.env.example`, `.env.local`, or comments mentioning `.env`. Changed to line-by-line parsing that only matches exact `.env` or `/.env` entries.

### 68. Connectivity tests hardcode API URLs — FIXED
- **File**: `src/aipea/cli.py:167-168,186-187`
- **Severity**: LOW | **Confidence**: 0.75
- **Source**: Claude sweep agent (types/strategies/CLI)
- **Fix**: `_test_exa_connectivity` and `_test_firecrawl_connectivity` hardcoded the default API URLs, ignoring `AIPEA_EXA_API_URL` and `AIPEA_FIRECRAWL_API_URL` env vars. Now reads from `os.environ.get()` with same defaults.

### 69. `_sync_fts_index` only rebuilds when fts_count < node_count — FIXED
- **File**: `src/aipea/knowledge.py:319`
- **Severity**: LOW | **Confidence**: 0.75
- **Source**: Claude sweep agent (core modules)
- **Fix**: Orphan FTS entries (fts_count > node_count) never triggered a rebuild. Changed `<` to `!=`. 1 regression test added.

### 70. `add_knowledge` upsert overwrites user-tuned `relevance_score` — FIXED
- **File**: `src/aipea/knowledge.py:715-720`
- **Severity**: MEDIUM | **Confidence**: 0.75
- **Source**: Claude sweep agent (core modules)
- **Fix**: `ON CONFLICT(id) DO UPDATE SET` included `relevance_score = excluded.relevance_score`, silently overwriting manually tuned scores during re-seed. Removed `relevance_score` from the UPDATE SET clause. 1 regression test added.

### 71. `OFFLINE_MODELS` set inconsistent with `OfflineModel` enum — FIXED
- **File**: `src/aipea/enhancer.py:196-201`
- **Severity**: LOW | **Confidence**: 0.85
- **Source**: Claude sweep agent (engine/enhancer)
- **Fix**: `OFFLINE_MODELS` lacked Ollama Tier 1 models (`gemma3:1b`, `gemma3:270m`, `phi3:mini`). `is_offline_model("gemma3:1b")` returned `False` despite the model being available offline via Ollama. Added all 3 Tier 1 models to the set. 2 regression tests added.

### 72. `_escape_config_value` does not escape TOML-illegal control characters — FIXED
- **File**: `src/aipea/config.py:351-353`
- **Severity**: LOW | **Confidence**: 0.70
- **Source**: Claude sweep agent (core modules)
- **Fix**: Control characters U+0000-U+0008, U+000B-U+000C, U+000E-U+001F, U+007F were not escaped, potentially producing unparsable TOML files. Added `\uXXXX` escaping for illegal control chars while preserving allowed tab (U+0009). 5 regression tests added.

### 73. API URL env vars frozen at import time — FIXED (wave 15)
- **File**: `src/aipea/search.py:40-41`
- **Severity**: MEDIUM | **Confidence**: 0.80
- **Source**: Claude sweep agent (core modules)
- **Fix**: See wave 15 entry above.

## Wave 14 — Deferred (resolved in wave 15)

### 74. `enhance_for_models()` gives all models the same prompt formatted for the first model — FIXED (wave 15)
- **File**: `src/aipea/enhancer.py:672-711`
- **Severity**: MEDIUM | **Confidence**: 0.90
- **Source**: Claude sweep agent (engine/enhancer)
- **Fix**: See wave 15 entry above.

## Wave 13 Fixes (2026-03-13) — 7 issues resolved

### 57. FTS index not cleaned up on node deletion — FIXED
- **File**: `src/aipea/knowledge.py:841`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Claude sweep agent (foundation modules)
- **Fix**: `_delete_node_sync` deleted from `knowledge_nodes` but not from `knowledge_fts`, leaving orphaned FTS entries. Added rowid lookup before DELETE + FTS cleanup with `contextlib.suppress(sqlite3.OperationalError)`.

### 58. `prune_low_relevance` does not clean up FTS entries for pruned nodes — FIXED
- **File**: `src/aipea/knowledge.py:941`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Claude sweep agent (foundation modules)
- **Fix**: Same class as #57. `_prune_low_relevance_sync` now fetches rowids before deletion and cleans up corresponding FTS entries. Regression test verifies FTS count matches node count after pruning.

### 59. Uncaught `ValueError` from Ollama prompt length validation crashes enhancement pipeline — FIXED
- **File**: `src/aipea/enhancer.py:1030`, `src/aipea/engine.py:688`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Claude sweep agent (facade/entry points)
- **Fix**: `OllamaOfflineClient.generate()` raises `ValueError` when prompt exceeds `_MAX_PROMPT_BYTES`, but both `OfflineTierProcessor.process()` and `_try_ollama_enhancement()` only caught `(RuntimeError, OSError)`. Added `ValueError` to both exception tuples for graceful template-based fallback.

### 60. `seed-kb` command ignores configured `AIPEA_DB_PATH` — FIXED
- **File**: `src/aipea/cli.py:623-626`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Claude sweep agent (facade/entry points)
- **Fix**: The `--db` option had hardcoded default `"aipea_knowledge.db"` instead of reading `load_config().db_path`. Changed to empty string default with `if not db_path: db_path = load_config().db_path` fallback. Backward compatible (same default when no custom config).

### 61. `search_semantic` does not update access counts for retrieved nodes — FIXED
- **File**: `src/aipea/knowledge.py:400-459`
- **Severity**: LOW | **Confidence**: HIGH
- **Source**: Claude sweep agent (foundation modules)
- **Fix**: `_search_semantic_sync` never incremented `access_count` or updated `last_accessed`, unlike `_search_sync`. Nodes retrieved only via semantic search appeared "less accessed" and were pruned more aggressively. Added matching access tracking logic.

### 62. Overly broad word-level overlap check filters out nearly all analyzer suggestions — FIXED
- **File**: `src/aipea/enhancer.py:372`
- **Severity**: LOW | **Confidence**: HIGH
- **Source**: Claude sweep agent (facade/entry points)
- **Fix**: The dedup check `any(s.lower() in c.lower() for c in clarifications for s in suggestion.split())` split suggestions into individual words, causing common words like "more", "to", "could" to match existing clarifications. Changed to whole-string containment check: `suggestion_lower in c.lower() or c.lower() in suggestion_lower`.

### 63. Resource leak — KB connection not closed on exception in `_doctor_knowledge_base` — FIXED
- **File**: `src/aipea/cli.py:366-369`
- **Severity**: LOW | **Confidence**: HIGH
- **Source**: Claude sweep agent (facade/entry points)
- **Fix**: `OfflineKnowledgeBase` was created and `close()` called only on the success path. If `_get_node_count_sync()` or `_get_domains_summary_sync()` raised, the connection leaked. Changed to `with` context manager.

## Spec-Code Drift (2026-03-09 docs-sync audit) — 11 items

Drift between `SPECIFICATION.md` and the live implementation. Items marked RESOLVED
were fixed in the spec during this audit. Items marked FUTURE require code changes.

### D1. `enhance_prompt()` facade missing `compliance_mode` and `force_offline` params — RESOLVED
- **File**: `src/aipea/enhancer.py`
- **Severity**: HIGH | **Type**: Code gap
- **Details**: The convenience function `enhance_prompt(query, model_id, security_level)` only exposed 3 params.
- **Fix**: Added `compliance_mode: ComplianceMode | None = None` and `force_offline: bool = False` as optional params. Updated SPECIFICATION.md Section 5.1 to show full 5-param signature. 3 regression tests added.

### D2. Spec used string types for enum parameters — RESOLVED
- **Severity**: HIGH | **Type**: Spec error
- **Details**: Spec Section 5.1 showed `security_level="UNCLASSIFIED"` and `compliance_mode="general"` (bare strings) but code uses `SecurityLevel.UNCLASSIFIED` and `ComplianceMode.GENERAL` (enum types). Passing strings would cause runtime `TypeError`.
- **Fix**: Updated spec examples to use proper enum imports.

### D3. HIPAA/FedRAMP model allowlists missing `claude-opus-4-5` — RESOLVED
- **Severity**: MEDIUM | **Type**: Spec stale
- **Details**: Code added `claude-opus-4-5` to both HIPAA and FedRAMP allowlists (security.py:537,558) but spec Section 7.3 only listed `claude-opus-4-6` and `gpt-5.2`.
- **Fix**: Updated spec model allowlist table.

### D4. `AIPEAEnhancer.__init__` undocumented `exa_api_key`/`firecrawl_api_key` params — RESOLVED
- **Severity**: MEDIUM | **Type**: Spec stale
- **Details**: Constructor accepts optional API key injection params (enhancer.py:304-305) not reflected in spec Section 11.2.
- **Fix**: Updated spec API reference.

### D5. Dual `SearchContext` architecture underspecified — RESOLVED
- **Severity**: MEDIUM | **Type**: Spec gap
- **Details**: Two `SearchContext` classes existed with ~200 LOC of duplicated logic.
- **Fix**: Deleted legacy `SearchContext` from `engine.py` (~200 lines). `engine.py` now re-exports `aipea.search.SearchContext` for backward compatibility. Added 4 read-only compat properties (`search_timestamp`, `sources`, `confidence_score`, `query_type`) to the AIPEA class. Removed `from_aipea_context()` conversion in `enhancer.py`. Engine tests rewritten to use AIPEA SearchContext constructor.

### D6. AEGIS adapter example used string `compliance_mode` — RESOLVED
- **Severity**: MEDIUM | **Type**: Spec error
- **Details**: Spec Section 5.3 AEGIS adapter example passed `compliance_mode="general"` to `enhance_prompt()`, which doesn't accept that param at all.
- **Fix**: Removed the invalid parameter from the example.

### D7. Injection pattern 4 outdated (whitespace bypass fix) — RESOLVED
- **Severity**: MEDIUM | **Type**: Spec stale
- **Details**: Spec Section 7.4 documented the old pattern `\n(Human|Assistant|System):` without the whitespace tolerance added in wave 12 (#51).
- **Fix**: Updated to `\n\s*(Human|Assistant|System):`.

### D8. Config module (`AIPEAConfig`, `load_config`) priority chain underdocumented — RESOLVED
- **Severity**: LOW | **Type**: Spec gap
- **Details**: Spec Section 8.1 only documented env vars.
- **Fix**: Added new Section 8.2 (Configuration System) to SPECIFICATION.md documenting the priority chain, `AIPEAConfig` fields, file locations, permissions, source tracking, and CLI commands. Renumbered existing 8.2→8.3, 8.3→8.4.

### D9. `quick_scan` function referenced in spec but not in `__all__` — RESOLVED
- **Severity**: LOW | **Type**: Spec aspirational
- **Details**: `quick_scan` existed in security.py but was not importable from root.
- **Fix**: Added `quick_scan` to `__init__.py` imports and `__all__`. Removed `(not in __all__)` annotation from spec Section 11.1. Regression test verifies `from aipea import quick_scan` works.

### D10. `enhance_for_models` base model template baking — FIXED (wave 15, #74)
- **Severity**: LOW | **Type**: Known limitation
- **Details**: Already tracked as deferred issue #36. Fixed in wave 15 (#74) with `embed_search_context` parameter and per-model search context formatting.

### D11. Spec test count / coverage stale — RESOLVED
- **Severity**: LOW | **Type**: Spec stale
- **Details**: Spec Section 1.3 references "2,187 passed + 1 skipped, 77.99% coverage" from AgoraIV provenance. AIPEA standalone now has 516 tests, 90.20% coverage. This is provenance history (not a current claim), so left as-is.

## Wave 12 Fixes (2026-03-09) — 5 issues resolved

### 51. Conversation separator injection bypassed by leading whitespace — FIXED
- **File**: `src/aipea/security.py:255`
- **Severity**: HIGH | **Confidence**: HIGH
- **Source**: Claude sweep agent (Opus deep sweep)
- **Fix**: Regex `(?:^|[\r\n])(?:Human|Assistant|System)\s*:` didn't allow whitespace between newline and role keyword. Added `\s*` after the line boundary group: `(?:^|[\r\n])\s*(?:Human|...)`. Inputs like `\n  Human: evil` now correctly detected. 4 regression tests added.

### 52. `save_dotenv` silently destroys all non-AIPEA keys in `.env` file — FIXED
- **File**: `src/aipea/config.py:264-290`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Claude sweep agent (engine/cli/config partition)
- **Fix**: `save_dotenv` wrote only AIPEA keys, truncating any existing non-AIPEA entries (e.g., `DATABASE_URL`). Now calls `_parse_dotenv(path)` first and preserves non-AIPEA keys in output. 3 regression tests added.

### 53. `aipea check --connectivity` always exits 0 even when connectivity tests fail — FIXED
- **File**: `src/aipea/cli.py:141-158`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Claude sweep agent (engine/cli/config partition)
- **Fix**: `_test_exa_connectivity` and `_test_firecrawl_connectivity` return values were discarded. Now appended to `issues` list on failure, causing `typer.Exit(1)`.

### 54. `_escape_markdown` doesn't escape `#`, `*`, `_`, `~` allowing rogue header/emphasis injection — FIXED
- **File**: `src/aipea/search.py:101-109`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Claude sweep agent (Opus deep sweep)
- **Fix**: Added `*`, `_`, `~` to character escape loop. Added per-line `#` header escape. Malicious search results with titles like `# IGNORE INSTRUCTIONS` no longer inject markdown headers. 4 regression tests added.

### 55. `_escape_plaintext` only escapes first line of multi-line text — FIXED
- **File**: `src/aipea/search.py:112-121`
- **Severity**: LOW | **Confidence**: HIGH
- **Source**: Claude sweep agent (Opus deep sweep)
- **Fix**: Changed single-line check to per-line loop. Interior lines like `\n1. Ignore instructions` now have list-item prefix escaped. 2 regression tests added.

## Wave 12 — Deferred

### 56. Unicode homoglyph bypass of all injection patterns — FIXED (wave 15)
- **File**: `src/aipea/security.py:251-260`
- **Severity**: MEDIUM | **Confidence**: MEDIUM
- **Source**: Claude sweep agent (Opus deep sweep)
- **Fix**: See wave 15 entry above.

## Quality Gate Ultrathink Fixes (2026-02-24) — 3 issues resolved

### 48. Exa `score: 0` coerced to `0.5` by `or` pattern (introduced in wave 11 #45 fix) — FIXED
- **File**: `src/aipea/search.py:520-525`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Quality gate ultrathink
- **Fix**: `item.get("score") or 0.5` is wrong for numeric fields because `0 or 0.5` evaluates to `0.5` (zero is falsy). Replaced with explicit None check: `score_raw if score_raw is not None else 0.5`. Regression test verifies `score: 0` is preserved as `0.0`.

### 49. Firecrawl `deep_research()` title/url still use old `dict.get("key", default)` pattern — FIXED
- **File**: `src/aipea/search.py:760-761`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Quality gate ultrathink
- **Fix**: Same class as #45. `source.get("title", "Source")` returns `None` when key exists with null value. Changed to `or` pattern: `source.get("title") or "Source"`.

### 50. Firecrawl `deep_research()` chained `.get()` crashes when `data.data` is null — FIXED
- **File**: `src/aipea/search.py:744-745`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Quality gate ultrathink
- **Fix**: Same class as #44. `data.get("data", {}).get("finalAnalysis", "")` crashes when `data` key exists with null value. Refactored to safe `isinstance(inner, dict)` guard with `or` fallbacks.

## Wave 11 Fixes (2026-02-24) — 4 issues resolved

### 44. `FirecrawlProvider.search()` crashes when `metadata` is `None` (chained `.get()` on NoneType) — FIXED
- **File**: `src/aipea/search.py:646-649`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Codex gpt-5.3-codex + Claude sweep agent (overlap)
- **Fix**: The chained `item.get("metadata", {}).get("title", "Untitled")` returned `None` when `metadata` key existed with `null` value, then called `.get()` on `None` causing `AttributeError`. Refactored to safe step-by-step resolution with `isinstance(metadata, dict)` guard.

### 45. Exa/Firecrawl `title`, `url`, `score` fields crash on explicit null values (`dict.get` null pattern) — FIXED
- **File**: `src/aipea/search.py:521-524,653`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Claude sweep agent
- **Fix**: Same class as #34/#37. `item.get("title", "Untitled")` returns `None` when key exists with null value, not the fallback default. Changed all provider field extractions to use `or` pattern: `item.get("title") or "Untitled"`, `item.get("url") or ""`, `item.get("score") or 0.5`.

### 46. Search formatters (`_format_openai`, `_format_anthropic`, `_format_generic`) crash on `None` result fields — FIXED
- **File**: `src/aipea/search.py:280-281,311-313,341-342`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Claude sweep agent
- **Fix**: Defense-in-depth: all three formatter methods now guard against `None` title/url/snippet with `or "Untitled"` / `or ""` fallbacks before passing to escape functions (`_escape_markdown`, `html.escape`, `_escape_plaintext`). Prevents `AttributeError` on `NoneType.replace()`.

## Wave 11 — Deferred

### 47. `TacticalTierProcessor.process` `has_search_context` metadata inconsistency — RESOLVED (class deleted)
- **File**: `src/aipea/engine.py` (formerly lines 1070-1132)
- **Severity**: LOW | **Confidence**: MEDIUM
- **Source**: Claude sweep agent
- **Resolution**: `TacticalTierProcessor` was removed as dead code in the gap analysis remediation (v1.2.0). The class was never called by the enhancer pipeline. Issue is moot.

## Quality Gate Ultrathink Fix (2026-02-18)

### 43. `search.py:SearchContext` confidence field missing `float()` coercion guard (same class as #39) — FIXED
- **File**: `src/aipea/search.py:208-216`
- **Severity**: LOW | **Confidence**: HIGH
- **Source**: Quality gate ultrathink sweep
- **Fix**: `SearchContext.__post_init__` in `search.py` called `math.isnan(self.confidence)` without `float()` coercion, crashing on `None`/`str` inputs. Same pattern as #39 (engine.py/models.py) but missed in `search.py`. Added `try/except (TypeError, ValueError)` with `float()` coercion. 2 regression tests added.

## Wave 10 Fixes (2026-02-17) — 3 issues resolved

### 38. `enhance()` doesn't enforce `ProcessingTier.OFFLINE` when `force_offline=True` — FIXED
- **File**: `src/aipea/enhancer.py:502-504`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Codex gpt-5.3-codex
- **Fix**: When security scan returns `force_offline=True`, offline context is used but `processing_tier` was still taken from `analysis.suggested_tier`. Added explicit override: `if offline_required: processing_tier = ProcessingTier.OFFLINE`. Regression test asserts `result.processing_tier == ProcessingTier.OFFLINE`.

### 39. `SearchContext`/`EnhancedQuery`/`QueryAnalysis` crash on non-numeric score types (TypeError on `math.isnan`) — FIXED
- **File**: `src/aipea/engine.py:395,600`, `src/aipea/models.py:42-50`
- **Severity**: LOW | **Confidence**: MEDIUM
- **Source**: Claude sweep agent
- **Fix**: Same class as #33 but in different dataclasses. Added `try/except (TypeError, ValueError)` with `float()` coercion before `math.isnan()` calls, matching the pattern already applied to `SearchResult.__post_init__` in search.py. Passing `confidence_score=None` or `confidence="0.5"` now coerces gracefully instead of crashing.

### 40. `save_dotenv`/`save_toml_config` don't escape newline/carriage return in values — FIXED
- **File**: `src/aipea/config.py:259-261`
- **Severity**: LOW | **Confidence**: HIGH
- **Source**: Claude sweep agent
- **Fix**: Extracted `_escape_config_value()` helper that escapes `\`, `"`, `\n`, and `\r`. Updated `_parse_dotenv` unescape logic to handle `\n` and `\r` for round-trip correctness. Regression tests verify both escaped output and round-trip fidelity.

## Wave 10 — Deferred

### 41. `aipea check` exits with code 1 when optional API keys are not configured — FIXED (wave 15)
- **File**: `src/aipea/cli.py:108-158`
- **Severity**: LOW | **Confidence**: MEDIUM
- **Source**: Claude sweep agent
- **Fix**: See wave 15 entry above.

### 42. `doctor` connectivity section uses inconsistent output format — FIXED (wave 15)
- **File**: `src/aipea/cli.py:331-344`
- **Severity**: LOW | **Confidence**: HIGH
- **Source**: Claude sweep agent
- **Fix**: See wave 15 entry above.

## Wave 9 Fixes (2026-02-17) — 3 issues resolved

### 34. `ExaSearchProvider.search()` crashes on `text: null` Exa results (TypeError on slice) — FIXED
- **File**: `src/aipea/search.py:506-509`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Codex gpt-5.3-codex
- **Fix**: When Exa returns `{"text": null}`, `item.get("text")` returns `None` (key exists), not the fallback. `None[:1000]` raised `TypeError`. Refactored to explicit null check with `summary` fallback and safe `str()` conversion before slicing.

### 35. `enhance_for_models` returns empty dict when enhancement is disabled (passthrough conflated with blocked) — FIXED
- **File**: `src/aipea/enhancer.py:615-622`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Claude sweep agent
- **Fix**: The `if not base_result.was_enhanced:` check conflated passthrough results (enhancement disabled, valid query) with blocked results (security threat). Added `original_query != enhanced_prompt` condition to distinguish passthrough (prompt equals query) from blocked (prompt is the block message). Passthrough queries now proceed to per-model formatting.

### 37. `FirecrawlProvider.search()` and `deep_research()` crash on null markdown/content (same class as #34) — FIXED
- **File**: `src/aipea/search.py:635,749`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Quality gate ultrathink (wave 9)
- **Fix**: Same pattern as #34. `item.get("markdown")` and `source.get("content")` return `None` when the key exists with a null value, then `None[:1000]` raises `TypeError`. Fixed with `or ""` fallback and `str()` safety conversion. Regression test added.

## Wave 9 — Deferred

### 36. `enhance_for_models` bakes base model's family-specific prompt template into other models — FIXED (wave 15, #74)
- **File**: `src/aipea/enhancer.py:604-632`
- **Severity**: LOW | **Confidence**: MEDIUM
- **Source**: Claude sweep agent
- **Fix**: Resolved by wave 15 fix #74. `enhance_for_models()` now calls `enhance(embed_search_context=False)` for a clean base prompt, then applies per-model search context formatting via `create_model_specific_prompt(search_context=...)`.

## Wave 8 Fixes (2026-02-16) — 2 issues resolved

### 32. `api_key` PII pattern misses common API key formats — FIXED
- **File**: `src/aipea/security.py:228`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Source**: Claude sweep agent
- **Fix**: Split single `api_key` pattern into three separate patterns: `api_key` (catches `api_key=VALUE` with `:=` separators), `sk_key` (catches `sk-` prefixed keys including `sk-proj-`), and `bearer_token` (catches `bearer TOKEN` with dots/dashes). The original pattern required 20+ alphanumeric chars immediately after the prefix, missing separator characters and modern key formats.

### 33. `SearchResult.__post_init__` crashes on non-numeric score (TypeError on `math.isnan`) — FIXED
- **File**: `src/aipea/search.py:166`
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
- **File**: `src/aipea/search.py:54`
- **Fix**: Added validation `0 < val < float("inf")`, defaults to 30.0 on invalid.

### 27. `_is_regex_safe` fails to detect character class nested quantifier ReDoS — FIXED
- **File**: `src/aipea/security.py`
- **Severity**: MEDIUM | **Confidence**: HIGH
- **Fix**: Added char-class-in-quantified-group detection to `_is_regex_safe()` and `_DANGEROUS_PATTERNS`. Patterns like `([^)]+)+` are now rejected before compilation. See also #19 (possessive quantifier false positives remain deferred).

## Intentional Design Decisions (documented, not bugs)

### 1. `_stats` dict not thread-safe on AIPEAEnhancer singleton — RESOLVED
- **File**: `src/aipea/enhancer.py`
- **Resolution**: Thread-safe `_stats_lock = threading.Lock()` added in coherence audit remediation (F14, 2026-03-13). All `_stats` mutations and reads now wrapped in `with self._stats_lock:`.

### 2. MODEL_FAMILY_MAP returns "gpt" instead of "openai" for GPT-5.x models — RESOLVED
- **File**: `src/aipea/_types.py`
- **Resolution**: Canonical `get_model_family()` moved to `_types.py` in coherence audit remediation (F7, 2026-03-13). GPT-5.x now returns `"openai"` consistently. Both `enhancer.py` and `search.py` use the centralized detector.

### 3. `merge_with` produces non-zero confidence with zero results — INTENTIONAL
- **File**: `src/aipea/search.py:345-365`
- **Rationale**: Only triggered by constructing SearchContext with non-zero confidence but empty results, which doesn't happen in normal usage.

### 5. Classified markers "SECRET"/"CONFIDENTIAL" may cause false positives — INTENTIONAL
- **File**: `src/aipea/security.py:242-248`
- **Rationale**: TACTICAL mode is for military/defense contexts where these words have specific meaning. Conservative by design.

### 6. Classified marker check only runs in TACTICAL mode — INTENTIONAL
- **File**: `src/aipea/security.py:467-470`
- **Rationale**: Intentional scoping per compliance mode. Running classified checks in all modes would generate noise in GENERAL usage.

### 11. Exa API scores may not be in [0, 1] range causing log noise — INTENTIONAL
- **File**: `src/aipea/search.py:166-182`
- **Rationale**: Clamping already handles this; log noise is minor and useful for monitoring.

## Deferred Findings (3 LOW severity remaining)

Wave 16 deferred: #79 (Exa score clamping), #80 (stats atomicity), #81 (timeout eagerness). All LOW severity with no functional impact.

---
*Last updated: 2026-04-09 (Post-Wave 16 — 3 deferred LOW bugs remain, 752 passing tests, 91.79% coverage)*
