# KNOWN_ISSUES.md — Bug Hunt Findings (Waves 1-12 + Quality Gate: 2026-03-09)

Issues found during hybrid bug hunts. Status: FIXED, DEFERRED, or INTENTIONAL.

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

### D10. `enhance_for_models` base model template baking — DOCUMENTED (#36)
- **Severity**: LOW | **Type**: Known limitation
- **Details**: Already tracked as deferred issue #36 in this file. The base enhancement uses the first model's family-specific template, which other models then receive with an additional layer of their own formatting.

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

### 56. Unicode homoglyph bypass of all injection patterns — DEFERRED
- **File**: `src/aipea/security.py:251-260`
- **Severity**: MEDIUM | **Confidence**: MEDIUM
- **Source**: Claude sweep agent (Opus deep sweep)
- **Rationale**: All injection patterns use ASCII characters only. Attackers can substitute Unicode confusable characters (e.g., Cyrillic `о` U+043E for Latin `o`) to evade detection while LLMs interpret them equivalently. Fix requires NFKC normalization plus confusable character mapping before scanning — non-trivial scope requiring dedicated implementation and testing.

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

### 47. `TacticalTierProcessor.process` `has_search_context` metadata inconsistency — DEFERRED
- **File**: `src/aipea/engine.py:1070-1132`
- **Severity**: LOW | **Confidence**: MEDIUM
- **Source**: Claude sweep agent
- **Rationale**: When a wrong-typed `search_context` is passed via the `context` dict, `has_search_context` metadata reports `True` before `EnhancedQuery.__post_init__` silently resets it to `None`. No crash occurs (the type guard catches it), and the metadata field is informational only. Fixing requires restructuring the metadata computation order relative to dataclass construction.

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

### 41. `aipea check` exits with code 1 when optional API keys are not configured — DEFERRED
- **File**: `src/aipea/cli.py:108-158`
- **Severity**: LOW | **Confidence**: MEDIUM
- **Source**: Claude sweep agent
- **Rationale**: The `check` command treats missing optional API keys (Exa, Firecrawl) as issues, causing exit code 1. This is borderline — scripts calling `aipea check` may interpret this as a failure even when the tool is properly configured for offline-only use. Fix would require distinguishing "error" issues from "warning" issues.

### 42. `doctor` connectivity section uses inconsistent output format — DEFERRED
- **File**: `src/aipea/cli.py:331-344`
- **Severity**: LOW | **Confidence**: HIGH
- **Source**: Claude sweep agent
- **Rationale**: Connectivity results print `"Exa: OK"` format while all other doctor checks use `"PASS label"` format via `_DoctorChecks.ok()`. Counting logic is correct but the visual inconsistency is fragile if refactored. Cosmetic issue only.

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

### 1. `_stats` dict not thread-safe on AIPEAEnhancer singleton — INTENTIONAL
- **File**: `src/aipea/enhancer.py:349-357`
- **Rationale**: Async model is single-threaded; stats are best-effort. Adding locks would add overhead to every enhance() call.

### 2. MODEL_FAMILY_MAP returns "gpt" instead of "openai" for GPT-5.x models — INTENTIONAL
- **File**: `src/aipea/enhancer.py:181-189`
- **Rationale**: Downstream code uses substring matching (`"gpt" in model_lower`), so `"gpt"` still matches correctly.

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

## Deferred Findings (1 bug remaining)

- **#56** Unicode homoglyph bypass (MEDIUM) — requires NFKC normalization implementation
