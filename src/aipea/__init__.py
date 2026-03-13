"""AIPEA — AI Prompt Engineer Agent.

A standalone Python library for prompt preprocessing, security screening,
query analysis, and context enrichment for LLM systems.

Usage:
    from aipea.security import SecurityScanner, SecurityContext
    from aipea.knowledge import OfflineKnowledgeBase, StorageTier
    from aipea.analyzer import QueryAnalyzer
    from aipea.engine import PromptEngine
    from aipea.enhancer import AIPEAEnhancer, enhance_prompt
"""

from __future__ import annotations

__version__ = "1.2.0"

# Configuration
# Core enums and types
from aipea._types import ProcessingTier, QueryType, SearchStrategy

# Query analysis
from aipea.analyzer import QueryAnalyzer
from aipea.config import AIPEAConfig, load_config

# Prompt engine
from aipea.engine import PromptEngine

# Enhancement facade
from aipea.enhancer import (
    AIPEAEnhancer,
    EnhancedRequest,
    EnhancementResult,
    enhance_prompt,
    get_enhancer,
    reset_enhancer,
)

# Knowledge base
from aipea.knowledge import (
    KnowledgeDomain,
    KnowledgeNode,
    KnowledgeSearchResult,
    OfflineKnowledgeBase,
    StorageTier,
)

# Data models
from aipea.models import QueryAnalysis

# Search
from aipea.search import (
    Context7Provider,
    ExaSearchProvider,
    FirecrawlProvider,
    SearchContext,
    SearchOrchestrator,
    SearchProvider,
    SearchResult,
)

# Security
from aipea.security import (
    ComplianceHandler,
    ComplianceMode,
    ScanResult,
    SecurityContext,
    SecurityLevel,
    SecurityScanner,
    quick_scan,
)

__all__ = [
    "AIPEAConfig",
    "AIPEAEnhancer",
    "ComplianceHandler",
    "ComplianceMode",
    "Context7Provider",
    "EnhancedRequest",
    "EnhancementResult",
    "ExaSearchProvider",
    "FirecrawlProvider",
    "KnowledgeDomain",
    "KnowledgeNode",
    "KnowledgeSearchResult",
    "OfflineKnowledgeBase",
    "ProcessingTier",
    "PromptEngine",
    "QueryAnalysis",
    "QueryAnalyzer",
    "QueryType",
    "ScanResult",
    "SearchContext",
    "SearchOrchestrator",
    "SearchProvider",
    "SearchResult",
    "SearchStrategy",
    "SecurityContext",
    "SecurityLevel",
    "SecurityScanner",
    "StorageTier",
    "__version__",
    "enhance_prompt",
    "get_enhancer",
    "load_config",
    "quick_scan",
    "reset_enhancer",
]
