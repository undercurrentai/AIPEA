# Changelog

All notable changes to AIPEA will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- Vendored back into Agora IV at `vendor/aipea/` for zero-downtime migration
