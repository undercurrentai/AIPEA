# AIPEA Extraction — Next Steps

> **Context**: All steps complete. AIPEA extracted from AgoraIV v4.1.49, standalone package at v1.0.0, AgoraIV shims verified (2187 tests pass).
> **Date**: 2026-02-14
> **Prerequisite**: `/Projects/AIPEA/` exists with SPECIFICATION.md, CLAUDE.md, pyproject.toml, src/aipea/ scaffold

---

## Step 3: Copy Core Modules + Tests Verbatim (Effort: S) — COMPLETE

### What
Copy the 3 core AIPEA modules and their tests from AgoraIV into the standalone AIPEA repo **without any code changes**. These modules have zero Agora dependencies (confirmed: they import only stdlib + httpx).

### Files to Copy

| Source (AgoraIV) | Destination (AIPEA) | LOC |
|------------------|---------------------|-----|
| `aipea_security_context.py` | `src/aipea/security.py` | 637 |
| `aipea_offline_knowledge.py` | `src/aipea/knowledge.py` | 711 |
| `aipea_search_providers.py` | `src/aipea/search.py` | 1,071 |
| `tests/test_aipea_security_context.py` | `tests/test_security.py` | ~200 |
| `tests/test_aipea_offline_knowledge.py` | `tests/test_knowledge.py` | ~250 |
| `tests/test_aipea_search_providers.py` | `tests/test_search.py` | ~300 |
| `tests/test_aipea_ollama_integration.py` | `tests/test_ollama.py` | ~100 |

### Steps
```bash
# 1. Copy source modules (verbatim, no changes)
cp /Projects/AgoraIV/aipea_security_context.py /Projects/AIPEA/src/aipea/security.py
cp /Projects/AgoraIV/aipea_offline_knowledge.py /Projects/AIPEA/src/aipea/knowledge.py
cp /Projects/AgoraIV/aipea_search_providers.py /Projects/AIPEA/src/aipea/search.py

# 2. Copy test files
cp /Projects/AgoraIV/tests/test_aipea_security_context.py /Projects/AIPEA/tests/test_security.py
cp /Projects/AgoraIV/tests/test_aipea_offline_knowledge.py /Projects/AIPEA/tests/test_knowledge.py
cp /Projects/AgoraIV/tests/test_aipea_search_providers.py /Projects/AIPEA/tests/test_search.py
cp /Projects/AgoraIV/tests/test_aipea_ollama_integration.py /Projects/AIPEA/tests/test_ollama.py

# 3. Update imports in test files only (sed or manual)
#    Change: from aipea_security_context import ...
#    To:     from aipea.security import ...
#    (repeat for knowledge and search)

# 4. Install AIPEA in dev mode
cd /Projects/AIPEA && pip install -e ".[dev]"

# 5. Verify
pytest tests/ -v
```

### Verification
- `pytest tests/test_security.py -v` — all tests pass
- `pytest tests/test_knowledge.py -v` — all tests pass
- `pytest tests/test_search.py -v` — all tests pass
- `pytest tests/ -v` — full suite passes in isolation

### Gotchas
- Test files will need `from aipea.security import ...` instead of `from aipea_security_context import ...` — this is the ONLY change needed in test files
- Some tests may import `conftest.py` fixtures from AgoraIV — extract any needed fixtures into `/Projects/AIPEA/tests/conftest.py`
- The `aipea_offline_knowledge.py` creates SQLite files — ensure tests use `tmp_path` fixtures for cleanup

---

## Step 4: Generalize Facade + Engine + Analyzer (Effort: M) — COMPLETE

### What
Copy the 3 enhancement-layer modules from AgoraIV, rename classes to remove Agora/PCW prefixes, and update internal imports to use `aipea.*` package paths.

### Files to Copy and Modify

| Source (AgoraIV) | Destination (AIPEA) | Key Renames |
|------------------|---------------------|-------------|
| `pcw_query_analyzer.py` | `src/aipea/analyzer.py` | `PCWQueryAnalyzer` → `QueryAnalyzer` |
| `pcw_prompt_engine.py` | `src/aipea/engine.py` | `PCWPromptEngine` → `PromptEngine` |
| `agora_prompt_enhancement.py` | `src/aipea/enhancer.py` | `AgoraPromptEnhancement` → `AIPEAEnhancer` |

### Detailed Changes

#### `src/aipea/analyzer.py` (from `pcw_query_analyzer.py`)
```python
# Change imports:
#   from aipea_security_context import SecurityContext, SecurityScanner
#   from pcw_prompt_engine import ProcessingTier, QueryType
# To:
#   from aipea.security import SecurityContext, SecurityScanner
#   from aipea._types import ProcessingTier, QueryType

# Rename class:
#   class PCWQueryAnalyzer → class QueryAnalyzer

# Keep convenience functions, update class refs:
#   def analyze_query(...): analyzer = QueryAnalyzer() ...
```

#### `src/aipea/engine.py` (from `pcw_prompt_engine.py`)
```python
# Change imports:
#   from aipea_search_providers import ...
# To:
#   from aipea.search import ...

# Move enums to _types.py (already done in scaffold):
#   ProcessingTier, QueryType → aipea._types
#   Import from there instead of defining locally

# Rename class:
#   class PCWPromptEngine → class PromptEngine

# Keep OllamaOfflineClient, OfflineModel, tier processors as-is
```

#### `src/aipea/enhancer.py` (from `agora_prompt_enhancement.py`)
```python
# Change imports:
#   from aipea_offline_knowledge import ... → from aipea.knowledge import ...
#   from aipea_search_providers import ... → from aipea.search import ...
#   from aipea_security_context import ... → from aipea.security import ...
#   from pcw_prompt_engine import ... → from aipea.engine import ...
#   from pcw_query_analyzer import ... → from aipea.analyzer import ...

# Rename class:
#   class AgoraPromptEnhancement → class AIPEAEnhancer

# Remove Agora-specific convenience:
#   Remove: enhance_for_agora() (stays in AgoraIV adapter)
#   Keep:   enhance_prompt() (module-level entry point)

# Update singleton:
#   get_enhancer() → get_enhancer() (same pattern, new class name)
```

#### `src/aipea/__init__.py` (update public API)
```python
# Populate with actual exports:
from aipea.enhancer import AIPEAEnhancer, enhance, enhance_for_models
from aipea.models import EnhancementResult, EnhancedRequest
from aipea.security import SecurityLevel, ComplianceMode, SecurityContext, ...
from aipea.knowledge import OfflineKnowledgeBase, KnowledgeDomain, StorageTier, ...
from aipea.search import SearchOrchestrator, SearchResult, SearchContext, ...
from aipea.analyzer import QueryAnalyzer, QueryAnalysis, SearchStrategy, ...
from aipea._types import ProcessingTier, QueryType
```

#### Copy and adapt tests
```bash
# Extract AIPEA-relevant tests from AgoraIV test files:
# tests/test_pcw_query_analyzer.py → tests/test_analyzer.py
# tests/test_pcw_prompt_engine.py → tests/test_engine.py
# tests/test_agora_prompt_enhancement.py → tests/test_enhancer.py
# Update all imports to aipea.* package paths
```

### Verification
```bash
cd /Projects/AIPEA
pytest tests/ -v --cov=src/aipea --cov-report=term-missing
# Expected: all tests pass, coverage >= 75%
```

### Gotchas
- `pcw_prompt_engine.py` re-exports several items from `aipea_search_providers.py` — ensure these re-exports are preserved in `engine.py` OR moved to `__init__.py`
- `SearchContext` exists in BOTH `search.py` (AIPEA native) and `engine.py` (legacy wrapper) — the legacy `SearchContext` class in engine.py has a `from_aipea_context()` classmethod for conversion. Keep both, alias as `LegacySearchContext` in exports.
- `_types.py` already has `ProcessingTier`, `QueryType`, `SearchStrategy` — remove duplicates from `engine.py` and `analyzer.py`, import from `_types.py` instead
- The `models.py` scaffold has placeholder `Any` types for `SecurityContext` — replace with actual imports once `security.py` is in place

---

## Step 5: Write AgoraIV Adapter Shims (Effort: M) — COMPLETE

### What
Replace AgoraIV's AIPEA modules with thin re-export shims that import from the `aipea` package. This preserves all existing import paths so AgoraIV's 2,187+ tests pass without changes.

### Prerequisite
- AIPEA package installed in AgoraIV's venv: `pip install -e /Projects/AIPEA`
- Add `aipea` to AgoraIV's `requirements_agora_production.txt`

### Shim Files to Create (in AgoraIV)

#### `aipea_security_context.py` (shim)
```python
"""AIPEA Security Context — re-export shim.

This module re-exports all symbols from the standalone aipea.security
package for backward compatibility with existing AgoraIV imports.
"""
from aipea.security import *  # noqa: F401, F403
from aipea.security import __all__
```

#### `aipea_offline_knowledge.py` (shim)
```python
"""AIPEA Offline Knowledge — re-export shim."""
from aipea.knowledge import *  # noqa: F401, F403
from aipea.knowledge import __all__
```

#### `aipea_search_providers.py` (shim)
```python
"""AIPEA Search Providers — re-export shim."""
from aipea.search import *  # noqa: F401, F403
from aipea.search import __all__
```

#### `pcw_query_analyzer.py` (shim)
```python
"""PCW Query Analyzer — re-export shim.

Re-exports QueryAnalyzer as PCWQueryAnalyzer for backward compatibility.
"""
from aipea.analyzer import QueryAnalyzer as PCWQueryAnalyzer  # noqa: F401
from aipea.analyzer import QueryAnalysis, QueryRouter, SearchStrategy  # noqa: F401
from aipea.analyzer import analyze_query, route_query  # noqa: F401
from aipea._types import ProcessingTier, QueryType  # noqa: F401
```

#### `pcw_prompt_engine.py` (shim)
```python
"""PCW Prompt Engine — re-export shim.

Re-exports PromptEngine as PCWPromptEngine for backward compatibility.
"""
from aipea.engine import PromptEngine as PCWPromptEngine  # noqa: F401
from aipea.engine import (  # noqa: F401
    SearchContext, EnhancedQuery, TierProcessor,
    OfflineTierProcessor, TacticalTierProcessor, StrategicTierProcessor,
    OllamaOfflineClient, OllamaModelInfo, OfflineModel,
    get_ollama_client, get_prompt_engine,
    CLAUDE_CODE_AVAILABLE,
)
from aipea._types import ProcessingTier, QueryType  # noqa: F401
from aipea.search import (  # noqa: F401
    SearchResult, SearchStrategy, ModelType, SearchOrchestrator,
    create_empty_context,
)
from aipea.search import SearchContext as AIPEASearchContext  # noqa: F401
```

#### `agora_prompt_enhancement.py` (thin adapter, NOT a pure shim)
```python
"""Agora Prompt Enhancement — Agora-specific adapter wrapping AIPEAEnhancer.

This module provides the Agora-specific interface (AgoraPromptEnhancement)
and convenience functions (enhance_for_agora) that wrap the generic
AIPEAEnhancer from the aipea package.
"""
from aipea import AIPEAEnhancer
from aipea.models import EnhancementResult, EnhancedRequest
from aipea.security import SecurityLevel, ComplianceMode
from aipea._types import ProcessingTier, QueryType
from aipea.knowledge import StorageTier

class AgoraPromptEnhancement(AIPEAEnhancer):
    """Agora-specific prompt enhancement (inherits from AIPEAEnhancer)."""
    pass  # All methods inherited; add Agora-specific overrides here if needed

# Agora-specific convenience functions
async def enhance_for_agora(query, model_ids, security_level=SecurityLevel.UNCLASSIFIED):
    """Multi-model enhancement for Agora's dialogue system."""
    from aipea.enhancer import get_enhancer
    return await get_enhancer().enhance_for_models(query, model_ids, security_level)

# Re-exports for backward compat
from aipea.enhancer import enhance_prompt, get_enhancer, reset_enhancer  # noqa: F401
from aipea.enhancer import get_model_family, is_offline_model  # noqa: F401
```

### Verification
```bash
cd /Projects/AgoraIV
source venv_agora/bin/activate
pip install -e /Projects/AIPEA
make test  # ALL 2,187+ tests must pass
make lint  # Zero errors (noqa comments handle F401/F403)
make type  # May need type: ignore for wildcard imports
```

### Gotchas
- `make lint` will flag `F401` (unused imports) and `F403` (wildcard imports) — use `# noqa` comments
- `make type` with mypy strict may reject wildcard re-exports — use explicit re-exports if needed
- AgoraIV's `conftest.py` sets `AGORA_ENV=test` — ensure this doesn't interfere with AIPEA imports
- Some test files may import internal/private names (e.g., `_compiled_pii`) — these need to be re-exported or tests adjusted

---

## Step 6: Copy Original Design Files (Effort: S) — COMPLETE

### What
Copy the original Agora V/AIPEA/ design files into `docs/design-reference/` for provenance and historical reference.

### Files to Copy

| Source | Destination |
|--------|-------------|
| `Agora V/AIPEA/aipea-specification.md` | `docs/design-reference/aipea-specification.md` |
| `Agora V/AIPEA/aipea-agent-framework.py` | `docs/design-reference/aipea-agent-framework.py` |
| `Agora V/AIPEA/aipea-enhancement-engine.py` | `docs/design-reference/aipea-enhancement-engine.py` |
| `Agora V/AIPEA/aipea-market-configs.py` | `docs/design-reference/aipea-market-configs.py` |
| `Agora V/AIPEA/aipea-offline-knowledge.py` | `docs/design-reference/aipea-offline-knowledge.py` |
| `Agora V/AIPEA/aipea-agora-integration.py` | `docs/design-reference/aipea-agora-integration.py` |
| `Agora V/AIPEA/aipea-config-management.txt` | `docs/design-reference/aipea-config-management.txt` |
| `Agora V/AIPEA/aipea-aws-deployment.txt` | `docs/design-reference/aipea-aws-deployment.txt` |
| `Agora V/AIPEA/aipea-resilience-tests.py` | `docs/design-reference/aipea-resilience-tests.py` |

### Steps
```bash
# The actual path may vary — the Explore agent found them at:
SRC="/Users/joshuakirby/Desktop/Undercurrent-Holdings/Projects/Agora/Agora V/AIPEA"
DST="/Users/joshuakirby/Desktop/Undercurrent-Holdings/Projects/AIPEA/docs/design-reference"

cp "$SRC/aipea-specification.md" "$DST/"
cp "$SRC/aipea-agent-framework.py" "$DST/"
cp "$SRC/aipea-enhancement-engine.py" "$DST/"
cp "$SRC/aipea-market-configs.py" "$DST/"
cp "$SRC/aipea-offline-knowledge.py" "$DST/"
cp "$SRC/aipea-agora-integration.py" "$DST/"
cp "$SRC/aipea-config-management.txt" "$DST/"
cp "$SRC/aipea-aws-deployment.txt" "$DST/"
cp "$SRC/aipea-resilience-tests.py" "$DST/"
```

### Verification
- `ls docs/design-reference/` shows 9 files
- Files are read-only reference (never modified in AIPEA repo)

---

## Step 7: End-to-End Verification (Effort: S) — COMPLETE

### What
Verify that both the standalone AIPEA repo and AgoraIV work correctly after extraction.

### AIPEA Standalone Verification
```bash
cd /Projects/AIPEA
pip install -e ".[dev]"

# Unit tests
pytest tests/ -v --cov=src/aipea --cov-report=term-missing

# Expected:
# - All tests pass
# - Coverage >= 75%
# - Zero import errors

# Lint
ruff check src/ tests/
ruff format --check src/ tests/

# Type check
mypy src/aipea/
```

### AgoraIV Verification (after Step 5 shims)
```bash
cd /Projects/AgoraIV
source venv_agora/bin/activate

# Full validation
make all  # fmt, lint, type, test, sec

# Expected:
# - 2,187+ tests pass (zero regressions)
# - Coverage >= 75%
# - Zero lint errors
# - Zero type errors
# - Zero security issues
```

### Cross-Verification Checklist (verified 2026-02-14)
- [x] `from aipea import enhance_prompt` works in a fresh Python session
- [x] `from aipea.security import SecurityScanner` works
- [x] `from aipea.knowledge import OfflineKnowledgeBase` works
- [x] `from aipea.search import SearchOrchestrator` works
- [x] AgoraIV `from aipea_security_context import SecurityScanner` still works (shim)
- [x] AgoraIV `from pcw_query_analyzer import PCWQueryAnalyzer` still works (shim)
- [x] AgoraIV `from pcw_prompt_engine import PCWPromptEngine` still works (shim)
- [x] AgoraIV `from agora_prompt_enhancement import enhance_prompt` still works (adapter)
- [x] `make test` in AgoraIV: 2187 passed + 1 skipped, 0 failures (77.99% coverage)
- [x] `pytest tests/` in AIPEA: 144 passed, 15 skipped (Ollama), 0 failures

---

## Execution Order

```
Step 3 (copy core)
    │
    ▼
Step 4 (generalize)  ←── depends on Step 3 (modules must exist)
    │
    ▼
Step 5 (AgoraIV shims)  ←── depends on Step 4 (AIPEA package must be complete)
    │
    ▼
Step 6 (design reference)  ←── independent, can run anytime
    │
    ▼
Step 7 (verification)  ←── depends on Steps 3-5 all complete
```

Steps 3 and 6 can be parallelized. Steps 4→5→7 are sequential.

---

---

## DEFERRED: Future Work

The following items are documented for future implementation. They are not blocking current functionality.

### AEGIS Adapter Implementation

| Aspect | Detail |
|--------|--------|
| **Status** | DEFERRED — specification complete, not yet implemented |
| **Spec** | `docs/integration/aegis-adapter.md` (83 lines, complete integration pattern) |
| **Also in** | `SPECIFICATION.md:725-747` (Section 5.3) |
| **Includes** | Field mapping table (AIPEA → AEGIS), example code, installation instructions |
| **Trigger** | Implement when AEGIS integration is scheduled |
| **Dependencies** | AEGIS system must exist and have a stable API |

### PyPI Publication

| Aspect | Detail |
|--------|--------|
| **Status** | DEFERRED — workflow created, one-time PyPI setup pending |
| **Workflow** | `.github/workflows/publish.yml` (trusted publisher OIDC, no API tokens) |
| **Build tool** | `hatch build` (hatchling backend) |
| **Current install** | `pip install -e /Projects/AIPEA` (local editable) or vendored at `AgoraIV/vendor/aipea/` |
| **Steps to publish** | See CLAUDE.md Section 6.5 (Release to PyPI playbook) |
| **One-time setup** | (1) Register on PyPI, (2) `hatch build && hatch publish` for initial upload, (3) Configure trusted publisher on PyPI, (4) Create GitHub `release` environment |
| **Priority** | Ready when stable — workflow and playbook are in place |

### engine.py Test Coverage

| Aspect | Detail |
|--------|--------|
| **Status** | COMPLETE — coverage improved from 49% to 99% (73 new tests + 10 mock-based Ollama tests) |
| **Overall AIPEA coverage** | 90.92% (498 passed, 15 skipped) |
| **Date** | 2026-02-17 |

---

*AIPEA Extraction — Next Steps v1.0.0 | 2026-02-14*
