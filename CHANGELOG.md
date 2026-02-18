# Changelog

All notable changes to AIPEA will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **config**: `AIPEAConfig` dataclass and `load_config()` with priority chain: env vars > `.env` > `~/.aipea/config.toml` > defaults
- **cli**: 4 CLI commands via `aipea[cli]` extra: `configure`, `check`, `doctor`, `info`
- **cli**: `python -m aipea` entry point via `__main__.py`
- **cli**: `aipea configure --global` saves to `~/.aipea/config.toml`
- **cli**: `aipea check --connectivity` tests API key validity
- **cli**: `aipea doctor` runs full diagnostic (Python, deps, config, security, connectivity)
- **search**: Config file fallback in `_get_api_key()` and `_resolve_http_timeout()` helpers
- 78 new tests (498 total, 90.92% coverage)

### Fixed
- 41 bugs across 10 bug-hunt waves + quality gate (see `KNOWN_ISSUES.md` for details)
- Quote injection in `save_dotenv()` and `save_toml_config()` config writers
- Dotenv parser unescape for `\"` and `\\` in double-quoted values
- `enhance()` offline tier enforcement when `force_offline=True` (#38)
- `float()` coercion guards for all dataclass `__post_init__` isnan checks (#39, #43)
- Newline/CR escaping in `save_dotenv`/`save_toml_config` (#40)

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
