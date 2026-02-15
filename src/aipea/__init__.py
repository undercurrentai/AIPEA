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

__version__ = "1.0.0"

# Core enums and types
from aipea._types import ProcessingTier, QueryType, SearchStrategy

# Data models
from aipea.models import QueryAnalysis

# Security
from aipea.security import (
    ComplianceHandler,
    ComplianceMode,
    ScanResult,
    SecurityContext,
    SecurityLevel,
    SecurityScanner,
)

# Knowledge base
from aipea.knowledge import (
    KnowledgeDomain,
    KnowledgeNode,
    KnowledgeSearchResult,
    OfflineKnowledgeBase,
    StorageTier,
)

# Search
from aipea.search import (
    Context7Provider,
    ExaSearchProvider,
    FirecrawlProvider,
    SearchOrchestrator,
    SearchProvider,
    SearchResult,
)

# Query analysis
from aipea.analyzer import QueryAnalyzer

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

__all__ = [
    "__version__",
    # Enums & types
    "ProcessingTier",
    "QueryType",
    "SearchStrategy",
    # Data models
    "QueryAnalysis",
    "EnhancementResult",
    "EnhancedRequest",
    # Security
    "SecurityLevel",
    "ComplianceMode",
    "SecurityContext",
    "SecurityScanner",
    "ScanResult",
    "ComplianceHandler",
    # Knowledge
    "KnowledgeDomain",
    "KnowledgeNode",
    "KnowledgeSearchResult",
    "OfflineKnowledgeBase",
    "StorageTier",
    # Search
    "SearchProvider",
    "SearchResult",
    "SearchOrchestrator",
    "ExaSearchProvider",
    "FirecrawlProvider",
    "Context7Provider",
    # Analyzer
    "QueryAnalyzer",
    # Engine
    "PromptEngine",
    # Enhancer
    "AIPEAEnhancer",
    "enhance_prompt",
    "get_enhancer",
    "reset_enhancer",
]
