# Changelog

All notable changes to AIPEA will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.1] - 2026-03-15

### Changed
- **enhancer**: `enhance()` and `enhance_prompt()` accept `embed_search_context: bool` parameter for controlling search context injection (#74)
- **engine**: `formulate_search_aware_prompt()` accepts `embed_search_context: bool` parameter (#74)
- **config**: `exa_api_url` and `firecrawl_api_url` fields added to `AIPEAConfig` with full config chain support (#73)

### Fixed
- **enhancer**: `AIPEAEnhancer` now supports `close()` and context manager protocol (`with AIPEAEnhancer() as e:`) for deterministic SQLite connection cleanup (#75)
- **config**: dotenv parser correctly handles quoted values with embedded matching quotes (e.g., `KEY='val1' 'val2'`) and no longer unescapes values with missing closing quotes (#76)
- **knowledge**: `_prune_low_relevance_sync` deletes by exact IDs instead of re-evaluating criteria, preventing TOCTOU race between SELECT and DELETE that could orphan FTS entries (#77)
- **cli**: `doctor` connectivity checks no longer produce duplicate output — `silent=True` suppresses raw status lines when called from doctor format (#78)
- **security**: Unicode homoglyph bypass — NFKC normalization + 35-entry confusable character map (Cyrillic/Greek to Latin) applied before all security checks; prevents injection evasion via visually similar characters (#56)
- **search**: API URLs no longer frozen at import time — lazy resolvers `_resolve_exa_api_url()` and `_resolve_firecrawl_api_url()` respect runtime config changes (#73)
- **enhancer**: `enhance_for_models()` now produces distinct per-model search context formatting (markdown for GPT, XML for Claude, numbered list for generic) instead of baking the first model's format into all outputs (#74)
- **cli**: `aipea check` exits 0 when optional API keys are missing (warnings), exits 1 only on connectivity failures (errors) (#41)
- **cli**: Doctor connectivity section uses consistent PASS/WARN/FAIL format via `_DoctorChecks` helper (#42)
- **knowledge**: FTS index entries now cleaned up when nodes are deleted via `delete_node()` or pruned via `prune_low_relevance()` — prevents orphaned FTS data accumulation (#57, #58)
- **knowledge**: `search_semantic()` now updates `access_count` and `last_accessed` for retrieved nodes, matching `search()` behavior (#61)
- **knowledge**: `_sync_fts_index` now rebuilds when FTS count exceeds node count (orphan cleanup), not just when fewer (#69)
- **knowledge**: `add_knowledge` upsert no longer overwrites user-tuned `relevance_score` during re-seed (#70)
- **enhancer**: `ValueError` from Ollama prompt length validation now caught in `_try_ollama_enhancement()` — gracefully falls back to template-based enhancement instead of crashing (#59)
- **engine**: `ValueError` from Ollama prompt length validation now caught in `OfflineTierProcessor.process()` — defense-in-depth (#59)
- **enhancer**: `OFFLINE_MODELS` set now includes all Ollama Tier 1 models (`gemma3:1b`, `gemma3:270m`, `phi3:mini`) (#71)
- **enhancer**: Clarification overlap filter changed from word-level to whole-string containment — analyzer suggestions no longer incorrectly filtered by common English words (#62)
- **cli**: `seed-kb` command now respects configured `AIPEA_DB_PATH` when `--db` is not explicitly provided (#60)
- **cli**: `_doctor_knowledge_base` now uses context manager for `OfflineKnowledgeBase` — prevents connection leak on exception (#63)
- **cli**: `.env` permissions check now tests all 6 group/other bits (was only testing read) (#66)
- **cli**: `.gitignore` check uses line-by-line parsing instead of substring match — no longer false-positives on `.env.example` (#67, #72-configure)
- **cli**: Connectivity tests read API URLs from environment variables instead of hardcoding defaults (#68)
- **search**: `ExaSearchProvider.search()` now guards against empty/whitespace queries (matching Firecrawl) (#65)
- **strategies**: `task_decomposition` split regex now includes `plus` and `as well as` conjunctions (matching count regex) (#64)
- **config**: `_escape_config_value` now escapes TOML-illegal control characters (U+0000-U+0008, U+000B-U+000C, U+000E-U+001F, U+007F) (#72)
- 51 regression tests added across waves 14-16 (752 total, 91.79% coverage)
- All deferred bugs from waves 1-15 resolved

## [1.3.0] - 2026-03-13

### Added
- **enhancer**: Degradation feedback in `enhancement_notes` — reports when offline KB is missing ("run 'aipea seed-kb'"), when no search providers are configured ("aipea configure"), and when Ollama is unavailable ("using template-based enhancement")
- **cli**: Provider descriptions with signup URLs in `aipea configure` (Exa, Firecrawl) and skip hints showing API keys are optional
- **cli**: "Next Steps" panel after `aipea configure` with context-aware guidance
- **cli**: "Recommendations" panel after `aipea doctor` summary with actionable next steps
- **cli**: Platform-specific Ollama install hints in doctor (macOS: brew, Linux: curl, other: URL)
- **README**: "Getting Started" section with 3 paths (Minimal, Search Providers, Ollama) emphasizing zero-config baseline
- **strategies**: New `strategies.py` module — named enhancement strategies with 6 technique functions (specification_extraction, constraint_identification, hypothesis_clarification, metric_definition, task_decomposition, objective_hierarchy_construction) and 6 strategy presets (general, technical, research, creative, analytical, strategic) [P2a roadmap]
- **quality**: New `quality.py` module — heuristic quality assessor scoring clarity, specificity, information density, and instruction quality improvements between original and enhanced prompts [P3a roadmap]
- **enhancer**: `clarifications: list[str]` field on `EnhancementResult` — advisory clarifying questions for ambiguous queries (max 3), generated from ambiguity score, entity count, and complexity signals [P1 roadmap]
- **enhancer**: `quality_score: QualityScore | None` field on `EnhancementResult` — automatic quality assessment of each enhancement
- **enhancer**: `strategy: str | None` parameter on `enhance()` and `enhance_prompt()` — allows explicit strategy selection
- **knowledge**: `search_semantic()` method on `OfflineKnowledgeBase` — BM25-ranked full-text search using FTS5 [P2b roadmap]
- **config**: 4 new configuration fields: `ollama_host`, `db_path`, `storage_tier`, `default_compliance` — all following the standard env var > .env > TOML > default priority chain
- **config**: 6 new environment variables: `AIPEA_OLLAMA_HOST`, `AIPEA_DB_PATH`, `AIPEA_STORAGE_TIER`, `AIPEA_DEFAULT_COMPLIANCE`, `AIPEA_EXA_API_URL`, `AIPEA_FIRECRAWL_API_URL`
- **knowledge**: FTS5 full-text search with query-aware matching and automatic fallback to relevance-score ordering
- **security**: `GLOBAL_FORBIDDEN_MODELS` class variable on `ComplianceHandler` — blocks `gpt-4o` and `gpt-4o-mini` in ALL compliance modes
- **enhancer**: Thread-safe `_stats_lock` protecting all statistics mutations
- **enhancer**: FEDRAMP stub warning when FEDRAMP compliance mode is selected
- **engine**: Warning logs when non-default `max_tokens`/`temperature` passed to `OllamaOfflineClient.generate()`
- 76 new tests (698 total, 91.42% coverage)

### Changed
- **cli**: `_ollama_install_hint()` helper extracted for DRY platform-specific install commands (3 call sites)
- **_types**: `QUERY_TYPE_PATTERNS` and `get_model_family()` centralized as single source of truth (was duplicated in analyzer.py, engine.py, enhancer.py, search.py)
- **analyzer**: `QueryRouter` methods promoted from private to public: `calculate_complexity()`, `detect_temporal_needs()`, `identify_domain()`, `calculate_confidence()`
- **enhancer**: Complexity scoring now uses actual `analysis.complexity` score instead of tier-based mapping
- **enhancer**: Domain defaults changed: OPERATIONAL and STRATEGIC now map to `GENERAL` (was `LOGISTICS` and `MILITARY`)
- **enhancer**: Offline context retrieval now prefers `search_semantic()` (BM25) over `search()` with automatic fallback
- **knowledge**: `OfflineKnowledgeBase.search()` now returns `KnowledgeSearchResult` instead of `list[KnowledgeNode]`
- **knowledge**: Constructor accepts `AIPEA_DB_PATH` env var for database path
- **engine**: `TierProcessor` ABC docstring documents planned Tactical/Strategic subclasses
- **engine**: `formulate_search_aware_prompt()` and `_process_with_templates()` apply strategy technique chains
- **search**: `EXA_API_URL` and `FIRECRAWL_API_URL` now configurable via environment variables
- Logger calls across knowledge.py, search.py, engine.py converted from f-strings to lazy %-formatting (36 sites)
- Narrowed broad `except Exception` blocks to specific exception types (15 sites)
- Added input validation on public API entry points (5 sites)

### Removed
- **engine**: `CLAUDE_CODE_AVAILABLE` placeholder flag (dead code, SDK does not exist)
- **_types**: `ProcessingTier.confidence_threshold` property (dead code, never used)

## [1.2.0] - 2026-03-13

### Added
- **enhancer**: Ollama LLM integration in offline enhancement path — `_try_ollama_enhancement()` uses local SLMs when available, falls back to templates gracefully
- **enhancer**: Cached `OfflineTierProcessor` instance to avoid per-call 18-regex recompilation
- **enhancer**: `include_search` and `format_for_model` optional params on `enhance()` and `enhance_prompt()` — consumers can now skip search context or model-specific formatting independently
- **enhancer**: `_scan_search_results()` filters web search results for prompt injection before inclusion in enhanced prompts (defense-in-depth)
- **enhancer**: `_gather_context_for_enhance()` extracted from `enhance()` to reduce cyclomatic complexity
- **knowledge**: `SEED_KNOWLEDGE` expanded from 13 to 20 entries across 7 domains — added MILITARY (2: COMSEC, tactical decision frameworks), LOGISTICS (1: field sustainment), COMMUNICATIONS (2: network architecture, secure messaging), MEDICAL (1: clinical decision support), GENERAL (1: data privacy by design)
- **knowledge**: `seed_knowledge_base()` helper for populating offline KB
- **cli**: `aipea seed-kb` command to populate knowledge base with seed data
- **cli**: `_doctor_ollama()` diagnostic section — checks Ollama availability, model count, best model
- **cli**: `_doctor_knowledge_base()` diagnostic section — checks KB node count, domain summary
- **engine**: `gemma3:1b` (815MB, 1B params) added to `OfflineModel` enum and Tier 1 preference order
- 89 new tests (622 total, 91.97% coverage)

### Changed
- **enhancer**: Offline tier now attempts Ollama LLM enhancement before falling back to template-only mode
- **engine**: `get_best_available_model()` preference order updated: phi3:mini > gemma3:1b > gemma3:270m
- **engine**: `_get_prompt_template()` no longer accepts `model_type` parameter — content-only enrichment, no behavioral directives
- **engine**: `create_model_specific_prompt()` simplified to return base prompt with optional search context (no behavioral wrapping)
- **engine**: Search context framing changed from "Relevant Search Context:" to provenance-aware "[Supplementary Context from Web Search — not part of the user's original query...]"

### Removed
- **engine**: `TacticalTierProcessor` class (~150 lines) — dead code, never called by enhancer
- **engine**: `StrategicTierProcessor` class (~200 lines) — dead code, never called by enhancer
- **engine**: `PromptEngine.enhance_query()` method (~30 lines) — unused router for deleted tier processors
- **engine**: Model behavioral directives ("You excel at...") from prompt templates — preprocessor should enrich content, not prescribe response style

### Fixed
- **enhancer**: `TYPE_CHECKING` import for `OfflineTierProcessor` resolves Pyright attribute access diagnostic
- **security**: FEDRAMP compliance mode now logs explicit warning that it is an unsupported stub with config-only behavior (no data residency, no FIPS, no continuous monitoring)
- **enhancer**: Wire 5 unused `_`-prefixed parameters in `_gather_online_context`, `_create_passthrough_result`, and `_create_blocked_result` — `security_context` now logged for audit trail, `model_id`/`scan_result`/`compliance_mode` enrich `enhancement_notes` with structured metadata
- **governance**: Complete 3 TODO placeholders in `ai/system-register.yaml` (EU AI Act classification) and `ai/model-card.yaml` (fairness probes, red team summary)

## [1.1.0] - 2026-03-09

### Added
- **enhancer**: `enhance_prompt()` convenience function now accepts `compliance_mode` and `force_offline` params (D1)
- **security**: `quick_scan` exported from root `__init__.py` — `from aipea import quick_scan` now works (D9)
- **search**: `SearchContext` exported from root `__init__.py` as public API
- **search**: Backward-compatibility properties on `SearchContext` (`search_timestamp`, `sources`, `confidence_score`, `query_type`)
- **config**: `AIPEAConfig` dataclass and `load_config()` with priority chain: env vars > `.env` > `~/.aipea/config.toml` > defaults
- **cli**: 4 CLI commands via `aipea[cli]` extra: `configure`, `check`, `doctor`, `info`
- **cli**: `python -m aipea` entry point via `__main__.py`
- **cli**: `aipea configure --global` saves to `~/.aipea/config.toml`
- **cli**: `aipea check --connectivity` tests API key validity
- **cli**: `aipea doctor` runs full diagnostic (Python, deps, config, security, connectivity)
- **search**: Config file fallback in `_get_api_key()` and `_resolve_http_timeout()` helpers
- 196 new tests (533 total, 90.24% coverage)

### Changed
- **engine**: Unified dual `SearchContext` classes — legacy class deleted from `engine.py`, re-exports `aipea.search.SearchContext` (D5)
- **enhancer**: Removed `SearchContext.from_aipea_context()` conversion — passes AIPEA SearchContext directly to PromptEngine (D5)
- **spec**: Section 5.1 updated with full 5-param `enhance_prompt()` signature (D1)
- **spec**: New Section 8.2 documents configuration system priority chain (D8)
- **spec**: Section 11.1 `quick_scan` no longer marked as `(not in __all__)` (D9)
- **ci**: All GitHub Actions SHA-pinned for supply chain security
- **ci**: trivy-action bumped to 0.34.0 (CVE-2026-26189 fix)
- **ci**: Checkov migrated from `-q` to `--compact`, CKV_GHA_7 skipped (false positive)
- **ci**: mutmut migrated to v3.x config-based `[tool.mutmut]` in pyproject.toml
- **ci**: Added `permissions: contents: read` to compliance-nightly and scaffold-checks workflows
- **ci**: Added CodeQL analysis, dependency-review, Dependabot, CODEOWNERS, PR template

### Fixed
- 46 bugs across 12 bug-hunt waves + quality gates (see `KNOWN_ISSUES.md` for details)
- Quote injection in `save_dotenv()` and `save_toml_config()` config writers
- Dotenv parser unescape for `\"` and `\\` in double-quoted values
- `enhance()` offline tier enforcement when `force_offline=True` (#38)
- `float()` coercion guards for all dataclass `__post_init__` isnan checks (#39, #43)
- Newline/CR escaping in `save_dotenv`/`save_toml_config` (#40)
- Conversation separator injection bypass via leading whitespace (#51)
- `save_dotenv` silently destroying non-AIPEA keys in `.env` files (#52)
- `aipea check --connectivity` exit code not reflecting failures (#53)
- `_escape_markdown` missing `#`, `*`, `_`, `~` escaping for rogue header injection (#54)
- `_escape_plaintext` only escaping first line of multi-line text (#55)

## [1.0.0] - 2026-02-14

### Added
- Initial release — extracted from Agora IV production (v4.1.49)
- **security**: PII/PHI detection, classification markers, injection prevention, HIPAA/Tactical compliance
- **analyzer**: Query complexity scoring, domain detection, temporal awareness, tier routing
- **search**: Multi-provider orchestration (Exa, Firecrawl, Context7) with strategy selection
- **knowledge**: Offline SQLite knowledge base with domain-aware retrieval and storage tiers
- **engine**: Model-specific prompt formatting, Ollama client, tier-based processing
- **enhancer**: High-level facade (`enhance_prompt`) coordinating the full pipeline
- **_types**: Shared enums (ProcessingTier, QueryType, SearchStrategy)
- **models**: Data models (QueryAnalysis)
- 337 tests passing, 92.28% coverage
- CI via GitHub Actions (lint, type check, test)
- Strict mypy and Ruff configuration
- SPECIFICATION.md (complete system specification)

### Origin
- 6 production modules (5,923 LOC) extracted from Agora IV into 9 standalone modules (6,192 LOC)
- Original Agora IV files replaced with thin re-export shims (338 LOC) for backward compatibility
- Initially vendored into Agora IV at `vendor/aipea/` for zero-downtime migration (replaced by PyPI install in v1.3.0+)
