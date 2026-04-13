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

__version__ = "1.4.0"

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

# Exception hierarchy
from aipea.errors import (
    AIPEAError,
    ConfigError,
    EnhancementError,
    KnowledgeStoreError,
    SearchProviderError,
    SecurityScanError,
)

# Knowledge base
from aipea.knowledge import (
    KnowledgeDomain,
    KnowledgeNode,
    KnowledgeSearchResult,
    OfflineKnowledgeBase,
    StorageTier,
)

# Adaptive learning
from aipea.learning import AdaptiveLearningEngine

# Data models
from aipea.models import QueryAnalysis

# Quality assessment
from aipea.quality import QualityAssessor, QualityScore

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
    "AIPEAError",
    "AdaptiveLearningEngine",
    "ComplianceHandler",
    "ComplianceMode",
    "ConfigError",
    "Context7Provider",
    "EnhancedRequest",
    "EnhancementError",
    "EnhancementResult",
    "ExaSearchProvider",
    "FirecrawlProvider",
    "KnowledgeDomain",
    "KnowledgeNode",
    "KnowledgeSearchResult",
    "KnowledgeStoreError",
    "OfflineKnowledgeBase",
    "ProcessingTier",
    "PromptEngine",
    "QualityAssessor",
    "QualityScore",
    "QueryAnalysis",
    "QueryAnalyzer",
    "QueryType",
    "ScanResult",
    "SearchContext",
    "SearchOrchestrator",
    "SearchProvider",
    "SearchProviderError",
    "SearchResult",
    "SearchStrategy",
    "SecurityContext",
    "SecurityLevel",
    "SecurityScanError",
    "SecurityScanner",
    "StorageTier",
    "__version__",
    "enhance_prompt",
    "get_enhancer",
    "load_config",
    "quick_scan",
    "reset_enhancer",
]
