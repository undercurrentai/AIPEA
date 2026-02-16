"""AIPEA Enhancer - Prompt enhancement facade.

This module provides the main interface for AI Prompt Engineer Agent (AIPEA)
functionality. It coordinates security scanning, query analysis,
search orchestration, and prompt formulation into a single, elegant API.

Key Features:
    - Enhancement ENABLED by default with automatic agentic routing
    - Security-aware processing (forces offline for classified content)
    - Multi-model support with model-specific prompt formatting
    - Seamless offline/online mode switching
    - Compliance handling (HIPAA, General, Tactical)

Usage:
    ```python
    from aipea.enhancer import enhance_prompt, SecurityLevel

    # Simple enhancement
    result = await enhance_prompt(
        "What are the latest AI developments?",
        model_id="gpt-4"
    )
    print(result.enhanced_prompt)

    # With security context
    result = await enhance_prompt(
        "Analyze tactical deployment options",
        model_id="gpt-oss-20b",
        security_level=SecurityLevel.SECRET
    )
    # Automatically routes to offline mode
    ```

Architecture:
    - Connectivity: Offline (air-gapped) vs Online (cloud)
    - Security: UNCLASSIFIED, CONFIDENTIAL, SECRET, TOP_SECRET
    - Compliance: GENERAL, HIPAA, TACTICAL
    - Processing: OFFLINE (<2s), TACTICAL (2-5s), STRATEGIC (5-15s)

Version: 1.0.0
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from aipea._types import ProcessingTier, QueryType, SearchStrategy
from aipea.analyzer import QueryAnalyzer
from aipea.engine import PromptEngine, SearchContext
from aipea.knowledge import KnowledgeDomain, OfflineKnowledgeBase, StorageTier
from aipea.models import QueryAnalysis
from aipea.search import SearchContext as AIPEASearchContext
from aipea.search import SearchOrchestrator, SearchResult, create_empty_context
from aipea.security import (
    ComplianceHandler,
    ComplianceMode,
    ScanResult,
    SecurityContext,
    SecurityLevel,
    SecurityScanner,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class EnhancementResult:
    """Complete result of prompt enhancement.

    Contains all metadata about the enhancement process including the
    enhanced prompt, processing tier used, security context, and timing.

    Attributes:
        original_query: The original user query
        enhanced_prompt: The enhanced prompt ready for model consumption
        processing_tier: The tier used for processing (OFFLINE, TACTICAL, STRATEGIC)
        security_context: Security context applied during enhancement
        query_analysis: Full analysis of the query
        search_context: Optional search context used for enhancement
        enhancement_time_ms: Time taken for enhancement in milliseconds
        was_enhanced: Whether enhancement was actually performed
        enhancement_notes: List of notes/warnings from the enhancement process
    """

    original_query: str
    enhanced_prompt: str
    processing_tier: ProcessingTier
    security_context: SecurityContext
    query_analysis: QueryAnalysis
    search_context: AIPEASearchContext | None = None
    enhancement_time_ms: float = 0.0
    was_enhanced: bool = True
    enhancement_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for logging/storage.

        Returns:
            Dictionary representation of all enhancement result fields
        """
        return {
            "original_query": self.original_query,
            "enhanced_prompt": self.enhanced_prompt,
            "processing_tier": self.processing_tier.value,
            "security_context": self.security_context.to_dict(),
            "query_analysis": self.query_analysis.to_dict(),
            "search_context": (
                {
                    "query": self.search_context.query,
                    "source": self.search_context.source,
                    "confidence": self.search_context.confidence,
                    "result_count": len(self.search_context.results),
                }
                if self.search_context
                else None
            ),
            "enhancement_time_ms": self.enhancement_time_ms,
            "was_enhanced": self.was_enhanced,
            "enhancement_notes": self.enhancement_notes,
        }


@dataclass
class EnhancedRequest:
    """Enhanced request ready for model consumption.

    Provides a standardized format for passing enhanced prompts to
    different AI models with appropriate metadata.

    Attributes:
        query: The original query
        enhanced_prompt: The enhanced prompt ready for the model
        model_id: Target model identifier (gpt-4, claude-3-opus, gemini-2, etc.)
        security_level: Security classification level
        compliance_mode: Compliance mode applied
        processing_tier: Processing tier used
        metadata: Additional metadata for the request
    """

    query: str
    enhanced_prompt: str
    model_id: str
    security_level: SecurityLevel
    compliance_mode: ComplianceMode
    processing_tier: ProcessingTier
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of the enhanced request
        """
        return {
            "query": self.query,
            "enhanced_prompt": self.enhanced_prompt,
            "model_id": self.model_id,
            "security_level": self.security_level.name,
            "compliance_mode": self.compliance_mode.value,
            "processing_tier": self.processing_tier.value,
            "metadata": self.metadata,
        }


# =============================================================================
# MODEL ID MAPPING
# =============================================================================


# Model ID to model family mapping for formatting
MODEL_FAMILY_MAP: dict[str, str] = {
    # OpenAI models
    "gpt-4": "openai",
    "gpt-4o": "openai",
    "gpt-4-turbo": "openai",
    "gpt-3.5-turbo": "openai",
    "gpt-5.1": "gpt",
    "gpt-5.2": "gpt",
    "gpt-5.2-pro": "gpt",
    "gpt-oss-20b": "openai",  # Offline OpenAI SLM
    # Anthropic models
    "claude-3-opus": "claude",
    "claude-3-sonnet": "claude",
    "claude-3-haiku": "claude",
    "claude-3.5-sonnet": "claude",
    "claude-3.5-haiku": "claude",
    "claude-opus-4-6": "claude",
    "claude-sonnet-4-5": "claude",
    "claude-haiku-4-5": "claude",
    # Google models
    "gemini-2": "gemini",
    "gemini-2-flash": "gemini",
    "gemini-1.5-pro": "gemini",
    "gemini-1.5-flash": "gemini",
    "gemini-3-pro-preview": "gemini",
    "gemini-3-flash-preview": "gemini",
    "gemma-3n": "gemini",  # Offline Google SLM
    # Meta models (offline)
    "llama-3.3-70b": "llama",
    "llama-3.2-3b": "llama",
}

# Offline-capable models
OFFLINE_MODELS: set[str] = {
    "gpt-oss-20b",
    "llama-3.3-70b",
    "llama-3.2-3b",
    "gemma-3n",
}


def get_model_family(model_id: str) -> str:
    """Get the model family for a given model ID.

    Args:
        model_id: The model identifier

    Returns:
        Model family string (openai, claude, gemini, llama, or general)
    """
    model_lower = model_id.lower()

    # Check exact match first
    if model_lower in MODEL_FAMILY_MAP:
        return MODEL_FAMILY_MAP[model_lower]

    # Check partial matches
    if "gpt" in model_lower or "openai" in model_lower:
        return "openai"
    elif "claude" in model_lower or "anthropic" in model_lower:
        return "claude"
    elif "gemini" in model_lower or "gemma" in model_lower:
        return "gemini"
    elif "llama" in model_lower:
        return "llama"
    else:
        return "general"


def is_offline_model(model_id: str) -> bool:
    """Check if a model is offline-capable.

    Args:
        model_id: The model identifier

    Returns:
        True if the model can run offline
    """
    return model_id.lower() in OFFLINE_MODELS


# =============================================================================
# MAIN FACADE CLASS
# =============================================================================


class AIPEAEnhancer:
    """
    Main facade for AIPEA prompt enhancement.

    Coordinates all AIPEA subsystems:
    - Security scanning and compliance handling
    - Query analysis and routing
    - Search orchestration (when online)
    - Offline knowledge retrieval (when air-gapped)
    - Prompt formulation with model-specific formatting

    Enhancement is ENABLED by default with automatic agentic routing.

    Example:
        >>> enhancer = AIPEAEnhancer()
        >>> result = await enhancer.enhance(
        ...     "What are the latest Python features?",
        ...     model_id="gpt-4"
        ... )
        >>> print(result.enhanced_prompt)

    Attributes:
        _enable_enhancement: Whether enhancement is enabled
        _storage_tier: Storage tier for offline knowledge base
        _default_compliance: Default compliance mode
        _security_scanner: Security scanner instance
        _query_analyzer: Query analyzer instance
        _prompt_engine: Prompt engine instance
        _search_orchestrator: Search orchestrator instance (if online enabled)
        _offline_kb: Offline knowledge base instance (if storage enabled)
    """

    def __init__(
        self,
        enable_enhancement: bool = True,
        storage_tier: StorageTier = StorageTier.STANDARD,
        default_compliance: ComplianceMode = ComplianceMode.GENERAL,
        exa_api_key: str | None = None,
        firecrawl_api_key: str | None = None,
    ) -> None:
        """Initialize the prompt enhancement facade.

        Args:
            enable_enhancement: Whether to enable enhancement (default True)
            storage_tier: Storage tier for offline knowledge base
            default_compliance: Default compliance mode for requests
            exa_api_key: Optional API key for Exa search provider
            firecrawl_api_key: Optional API key for Firecrawl provider
        """
        self._enable_enhancement = enable_enhancement
        self._storage_tier = storage_tier
        self._default_compliance = default_compliance

        # Initialize core components
        self._security_scanner = SecurityScanner()
        self._query_analyzer = QueryAnalyzer()
        self._prompt_engine = PromptEngine()

        # Initialize search orchestrator (online mode)
        # Placeholder: actual API keys would enable real search
        self._search_orchestrator: SearchOrchestrator | None = None
        if enable_enhancement:
            self._search_orchestrator = SearchOrchestrator(
                exa_enabled=True,
                firecrawl_enabled=True,
                context7_enabled=True,
                exa_api_key=exa_api_key,
                firecrawl_api_key=firecrawl_api_key,
            )

        # Initialize offline knowledge base
        self._offline_kb: OfflineKnowledgeBase | None = None
        if enable_enhancement:
            try:
                self._offline_kb = OfflineKnowledgeBase(
                    db_path="aipea_knowledge.db",
                    tier=storage_tier,
                )
            except Exception as e:
                logger.warning("Failed to initialize offline knowledge base: %s", e)
                self._offline_kb = None

        # Statistics tracking
        self._stats: dict[str, Any] = {
            "queries_enhanced": 0,
            "queries_blocked": 0,
            "queries_passthrough": 0,
            "avg_enhancement_time_ms": 0.0,
            "tier_distribution": {tier.value: 0 for tier in ProcessingTier},
            "compliance_distribution": {mode.value: 0 for mode in ComplianceMode},
        }

        logger.info(
            "AIPEAEnhancer initialized: enabled=%s, storage_tier=%s, compliance=%s",
            enable_enhancement,
            storage_tier.tier_name,
            default_compliance.value,
        )

    async def enhance(
        self,
        query: str,
        model_id: str,
        security_level: SecurityLevel = SecurityLevel.UNCLASSIFIED,
        compliance_mode: ComplianceMode | None = None,
        force_offline: bool = False,
    ) -> EnhancementResult:
        """
        Enhance a query for optimal model consumption.

        Automatic agentic routing:
        1. Security scan -> Block if dangerous
        2. Analyze query -> Determine tier and strategy
        3. Route based on security/connectivity
        4. Gather context (search or offline knowledge)
        5. Formulate enhanced prompt for target model

        Args:
            query: User's original query
            model_id: Target model (gpt-4, claude-3-opus, gemini-2, etc.)
            security_level: Classification level (forces offline if SECRET+)
            compliance_mode: HIPAA, GENERAL, or auto-detect
            force_offline: Force air-gapped mode regardless of security

        Returns:
            EnhancementResult with enhanced prompt and metadata

        Example:
            >>> result = await enhancer.enhance(
            ...     "Explain quantum computing",
            ...     model_id="claude-3-opus"
            ... )
            >>> print(result.enhanced_prompt)
        """
        start_time = time.perf_counter()
        enhancement_notes: list[str] = []

        # Use default compliance if not specified
        if compliance_mode is None:
            compliance_mode = self._default_compliance

        # If enhancement is disabled, pass through
        if not self._enable_enhancement:
            self._stats["queries_passthrough"] += 1
            return self._create_passthrough_result(
                query, model_id, security_level, compliance_mode, start_time
            )

        # Step 1: Create security context
        compliance_handler = ComplianceHandler(compliance_mode)
        security_context = compliance_handler.create_security_context(
            has_connectivity=not force_offline,
        )
        security_context.security_level = security_level

        # Enforce compliance-mode model restrictions and global forbidden list
        if not compliance_handler.validate_model(model_id):
            self._stats["queries_blocked"] += 1
            enhancement_notes.append(
                f"Model '{model_id}' is not allowed in compliance mode '{compliance_mode.value}'"
            )
            return self._create_blocked_result(
                query=query,
                model_id=model_id,
                security_context=security_context,
                scan_result=ScanResult(
                    flags=[f"model_not_allowed:{model_id}"],
                    is_blocked=True,
                ),
                compliance_mode=compliance_mode,
                start_time=start_time,
                enhancement_notes=enhancement_notes,
            )

        # Step 2: Security scan
        scan_result = self._security_scanner.scan(query, security_context)

        if scan_result.is_blocked:
            self._stats["queries_blocked"] += 1
            enhancement_notes.append(
                f"Query blocked due to security scan: {', '.join(scan_result.flags)}"
            )
            return self._create_blocked_result(
                query,
                model_id,
                security_context,
                scan_result,
                compliance_mode,
                start_time,
                enhancement_notes,
            )

        # Add scan flags to notes if any
        if scan_result.has_flags():
            enhancement_notes.append(f"Security flags detected: {', '.join(scan_result.flags)}")

        # Propagate scanner's force_offline recommendation (e.g. classified markers)
        if scan_result.force_offline:
            force_offline = True

        # Step 3: Analyze query
        analysis = self._query_analyzer.analyze(query, security_context)

        # Step 4: Determine if offline mode is required
        offline_required = self._is_offline_required(
            security_level,
            compliance_mode,
            force_offline,
        )

        if offline_required:
            enhancement_notes.append("Processing in offline mode due to security/connectivity")

        # Step 5: Gather context
        search_context: AIPEASearchContext | None = None

        if offline_required:
            search_context = await self._gather_offline_context(query, analysis)
            if search_context and not search_context.is_empty():
                enhancement_notes.append(
                    f"Offline context gathered: {len(search_context.results)} results"
                )
        else:
            search_context = await self._gather_online_context(query, analysis, security_context)
            if search_context and not search_context.is_empty():
                enhancement_notes.append(
                    f"Online context gathered from {search_context.source}: "
                    f"{len(search_context.results)} results"
                )

        # Step 6: Determine processing tier
        processing_tier = analysis.suggested_tier or ProcessingTier.OFFLINE

        # Step 7: Formulate enhanced prompt
        model_family = get_model_family(model_id)

        # Convert AIPEA search context to legacy format for prompt engine
        legacy_search_context: SearchContext | None = None
        if search_context and not search_context.is_empty():
            legacy_search_context = SearchContext.from_aipea_context(search_context)

        # Determine complexity string from tier
        complexity_map = {
            ProcessingTier.OFFLINE: "simple",
            ProcessingTier.TACTICAL: "medium",
            ProcessingTier.STRATEGIC: "complex",
        }
        complexity = complexity_map.get(processing_tier, "medium")

        # Formulate the enhanced prompt
        enhanced_prompt = await self._prompt_engine.formulate_search_aware_prompt(
            query=query,
            complexity=complexity,
            search_context=legacy_search_context,
            model_type=model_family,
        )

        # Calculate timing
        enhancement_time_ms = (time.perf_counter() - start_time) * 1000

        # Update statistics
        self._stats["queries_enhanced"] += 1
        self._stats["tier_distribution"][processing_tier.value] += 1
        self._stats["compliance_distribution"][compliance_mode.value] += 1
        self._update_avg_time(enhancement_time_ms)

        logger.info(
            "Query enhanced: tier=%s, model=%s, time=%.2fms",
            processing_tier.value,
            model_id,
            enhancement_time_ms,
        )

        return EnhancementResult(
            original_query=query,
            enhanced_prompt=enhanced_prompt,
            processing_tier=processing_tier,
            security_context=security_context,
            query_analysis=analysis,
            search_context=search_context,
            enhancement_time_ms=enhancement_time_ms,
            was_enhanced=True,
            enhancement_notes=enhancement_notes,
        )

    async def enhance_for_models(
        self,
        query: str,
        model_ids: list[str],
        security_level: SecurityLevel = SecurityLevel.UNCLASSIFIED,
    ) -> dict[str, EnhancedRequest]:
        """
        Enhance query for multiple models simultaneously.

        Prepares prompts optimized for each participating model
        in a multi-model dialogue system.

        Args:
            query: The user's original query
            model_ids: List of target model identifiers
            security_level: Classification level for the query

        Returns:
            Dictionary mapping model_id to EnhancedRequest

        Example:
            >>> requests = await enhancer.enhance_for_models(
            ...     "Explain quantum computing",
            ...     model_ids=["gpt-4", "claude-3-opus", "gemini-2"]
            ... )
            >>> for model_id, request in requests.items():
            ...     print(f"{model_id}: {len(request.enhanced_prompt)} chars")
        """
        results: dict[str, EnhancedRequest] = {}

        # Perform base enhancement once using a generic model ID so the base
        # prompt is model-neutral.  Per-model formatting is applied below via
        # create_model_specific_prompt, preventing double model-specific wrapping.
        # Use GENERAL compliance for the base call because "generic" is not on any
        # restricted allowlist.  Per-model compliance validation happens in the loop.
        compliance_handler = ComplianceHandler(self._default_compliance)
        base_result = await self.enhance(
            query=query,
            model_id="generic",
            security_level=security_level,
            compliance_mode=ComplianceMode.GENERAL,
            force_offline=compliance_handler.force_offline,
        )

        # If the base enhancement was blocked (e.g. injection detected),
        # do not wrap the block message in model-specific formatting.
        if not base_result.was_enhanced:
            logger.warning(
                "Base enhancement blocked in enhance_for_models; returning empty results"
            )
            return results

        # Validate each model against compliance policy before formatting
        compliance_handler = ComplianceHandler(self._default_compliance)

        for model_id in model_ids:
            if not compliance_handler.validate_model(model_id):
                logger.warning("Skipping forbidden model in enhance_for_models: %s", model_id)
                continue

            # Get model-specific formatting
            model_family = get_model_family(model_id)

            # Create model-specific prompt
            model_prompt = await self._prompt_engine.create_model_specific_prompt(
                base_prompt=base_result.enhanced_prompt,
                model_type=model_family,
                # base_result.enhanced_prompt already contains any gathered
                # search context from enhance(); avoid injecting it twice.
                search_context=None,
            )

            results[model_id] = EnhancedRequest(
                query=query,
                enhanced_prompt=model_prompt,
                model_id=model_id,
                security_level=security_level,
                compliance_mode=self._default_compliance,
                processing_tier=base_result.processing_tier,
                metadata={
                    "model_family": model_family,
                    "base_enhancement_time_ms": base_result.enhancement_time_ms,
                    "query_type": base_result.query_analysis.query_type.value,
                },
            )

        return results

    def _is_offline_required(
        self,
        security_level: SecurityLevel,
        compliance_mode: ComplianceMode,
        force_offline: bool,
    ) -> bool:
        """Determine if offline mode is required.

        Offline mode is required when:
        - Security level is SECRET or TOP_SECRET
        - force_offline flag is set
        - Compliance mode is TACTICAL

        Args:
            security_level: The security classification level
            compliance_mode: Compliance mode for the request
            force_offline: Whether offline mode is explicitly forced

        Returns:
            True if offline mode is required
        """
        if force_offline:
            return True

        if security_level.value >= SecurityLevel.SECRET.value:
            return True

        return compliance_mode == ComplianceMode.TACTICAL

    async def _gather_online_context(
        self,
        query: str,
        analysis: QueryAnalysis,
        security_context: SecurityContext,
    ) -> AIPEASearchContext | None:
        """Gather context from online search providers.

        Uses the SearchOrchestrator to gather relevant context
        based on the query analysis search strategy.

        Args:
            query: The user's query
            analysis: Query analysis with search strategy
            security_context: Security context for filtering

        Returns:
            SearchContext with search results, or None if unavailable
        """
        if analysis.search_strategy == SearchStrategy.NONE:
            logger.debug("Search strategy NONE, skipping online context")
            return None

        if self._search_orchestrator is None:
            logger.debug("Search orchestrator not available, skipping online context")
            return None

        # Map analysis search strategy to orchestrator strategy
        strategy_map = {
            SearchStrategy.QUICK_FACTS: "quick_facts",
            SearchStrategy.DEEP_RESEARCH: "deep_research",
            SearchStrategy.MULTI_SOURCE: "multi_source",
            SearchStrategy.NONE: "quick_facts",
        }

        strategy = strategy_map.get(analysis.search_strategy, "quick_facts")

        try:
            context = await self._search_orchestrator.search(
                query=query,
                strategy=strategy,
                num_results=5,
            )
            return context
        except Exception as e:
            logger.warning("Online search failed: %s", e)
            return None

    async def _gather_offline_context(
        self,
        query: str,
        analysis: QueryAnalysis,
    ) -> AIPEASearchContext | None:
        """Gather context from offline knowledge base.

        Uses the OfflineKnowledgeBase to retrieve relevant cached
        knowledge for air-gapped environments.

        Args:
            query: The user's query
            analysis: Query analysis for domain filtering

        Returns:
            SearchContext with offline results, or None if unavailable
        """
        if self._offline_kb is None:
            logger.debug("Offline knowledge base not available, skipping offline context")
            return None

        # Map query type to knowledge domain
        domain_map: dict[QueryType, KnowledgeDomain] = {
            QueryType.TECHNICAL: KnowledgeDomain.TECHNICAL,
            QueryType.RESEARCH: KnowledgeDomain.GENERAL,
            QueryType.CREATIVE: KnowledgeDomain.GENERAL,
            QueryType.ANALYTICAL: KnowledgeDomain.GENERAL,
            QueryType.OPERATIONAL: KnowledgeDomain.LOGISTICS,
            QueryType.STRATEGIC: KnowledgeDomain.MILITARY,
            QueryType.UNKNOWN: KnowledgeDomain.GENERAL,
        }

        domain = domain_map.get(analysis.query_type, KnowledgeDomain.GENERAL)

        try:
            nodes = await self._offline_kb.search(
                query=query,
                domain=domain,
                limit=5,
            )

            if not nodes:
                return create_empty_context(query, source="offline_kb")

            # Convert KnowledgeNodes to SearchResults
            results: list[SearchResult] = []
            for node in nodes:
                results.append(
                    SearchResult(
                        title=f"[{node.domain.value.upper()}] Knowledge ({node.id[:8]})",
                        url=f"offline://kb/{node.id}",
                        snippet=(
                            node.content[:500] + "..." if len(node.content) > 500 else node.content
                        ),
                        score=node.relevance_score,
                    )
                )

            return AIPEASearchContext(
                query=query,
                results=results,
                timestamp=datetime.now(UTC),
                source="offline_kb",
                confidence=sum(r.score for r in results) / len(results) if results else 0.0,
            )

        except Exception as e:
            logger.warning("Offline search failed: %s", e)
            return None

    def _create_passthrough_result(
        self,
        query: str,
        model_id: str,
        security_level: SecurityLevel,
        compliance_mode: ComplianceMode,
        start_time: float,
    ) -> EnhancementResult:
        """Create a passthrough result when enhancement is disabled.

        Args:
            query: The original query
            model_id: Target model ID
            security_level: Security level
            compliance_mode: Compliance mode
            start_time: Start time for timing calculation

        Returns:
            EnhancementResult with unmodified query
        """
        security_context = SecurityContext(
            compliance_mode=compliance_mode,
            security_level=security_level,
        )

        # Create minimal analysis
        analysis = QueryAnalysis(
            query=query,
            query_type=QueryType.UNKNOWN,
            complexity=0.0,
            confidence=0.0,
            needs_current_info=False,
        )

        enhancement_time_ms = (time.perf_counter() - start_time) * 1000

        return EnhancementResult(
            original_query=query,
            enhanced_prompt=query,  # Passthrough - no enhancement
            processing_tier=ProcessingTier.OFFLINE,
            security_context=security_context,
            query_analysis=analysis,
            search_context=None,
            enhancement_time_ms=enhancement_time_ms,
            was_enhanced=False,
            enhancement_notes=["Enhancement disabled - query passed through unmodified"],
        )

    def _create_blocked_result(
        self,
        query: str,
        model_id: str,
        security_context: SecurityContext,
        scan_result: ScanResult,
        compliance_mode: ComplianceMode,
        start_time: float,
        enhancement_notes: list[str],
    ) -> EnhancementResult:
        """Create a blocked result when security scan blocks the query.

        Args:
            query: The original query
            model_id: Target model ID
            security_context: Security context
            scan_result: Security scan result
            compliance_mode: Compliance mode
            start_time: Start time for timing calculation
            enhancement_notes: Notes to include

        Returns:
            EnhancementResult indicating blocked query
        """
        # Create minimal analysis
        analysis = QueryAnalysis(
            query=query,
            query_type=QueryType.UNKNOWN,
            complexity=0.0,
            confidence=0.0,
            needs_current_info=False,
        )

        enhancement_time_ms = (time.perf_counter() - start_time) * 1000

        # Create blocked message
        blocked_prompt = (
            "This query has been blocked by security screening. "
            "Please reformulate your query without sensitive content."
        )

        return EnhancementResult(
            original_query=query,
            enhanced_prompt=blocked_prompt,
            processing_tier=ProcessingTier.OFFLINE,
            security_context=security_context,
            query_analysis=analysis,
            search_context=None,
            enhancement_time_ms=enhancement_time_ms,
            was_enhanced=False,
            enhancement_notes=enhancement_notes,
        )

    def _update_avg_time(self, new_time_ms: float) -> None:
        """Update the rolling average enhancement time.

        Args:
            new_time_ms: New enhancement time in milliseconds
        """
        count = self._stats["queries_enhanced"]
        if count == 1:
            self._stats["avg_enhancement_time_ms"] = new_time_ms
        else:
            # Rolling average
            current_avg = self._stats["avg_enhancement_time_ms"]
            self._stats["avg_enhancement_time_ms"] = (
                current_avg + (new_time_ms - current_avg) / count
            )

    def get_status(self) -> dict[str, Any]:
        """Get current enhancement system status.

        Returns:
            Dictionary with status information including:
            - enhancement_enabled: Whether enhancement is active
            - storage_tier: Current storage tier
            - default_compliance: Default compliance mode
            - offline_knowledge_ready: Whether offline KB is available
            - search_orchestrator_ready: Whether search is available
            - queries_enhanced: Total queries enhanced
            - queries_blocked: Total queries blocked
        """
        return {
            "enhancement_enabled": self._enable_enhancement,
            "storage_tier": self._storage_tier.tier_name,
            "default_compliance": self._default_compliance.value,
            "offline_knowledge_ready": self._offline_kb is not None,
            "search_orchestrator_ready": self._search_orchestrator is not None,
            "queries_enhanced": self._stats["queries_enhanced"],
            "queries_blocked": self._stats["queries_blocked"],
            "queries_passthrough": self._stats["queries_passthrough"],
            "avg_enhancement_time_ms": round(self._stats["avg_enhancement_time_ms"], 2),
            "tier_distribution": self._stats["tier_distribution"],
            "compliance_distribution": self._stats["compliance_distribution"],
        }

    def reset_stats(self) -> None:
        """Reset all statistics counters."""
        self._stats = {
            "queries_enhanced": 0,
            "queries_blocked": 0,
            "queries_passthrough": 0,
            "avg_enhancement_time_ms": 0.0,
            "tier_distribution": {tier.value: 0 for tier in ProcessingTier},
            "compliance_distribution": {mode.value: 0 for mode in ComplianceMode},
        }
        logger.info("Enhancement statistics reset")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


# Module-level singleton for easy access
_default_enhancer: AIPEAEnhancer | None = None
_default_enhancer_lock = threading.Lock()


def get_enhancer() -> AIPEAEnhancer:
    """Get or create the default prompt enhancer.

    Returns a singleton instance of AIPEAEnhancer with default settings.
    Thread-safe via double-checked locking pattern.

    Returns:
        The default AIPEAEnhancer instance

    Example:
        >>> enhancer = get_enhancer()
        >>> result = await enhancer.enhance("Hello", "gpt-4")
    """
    global _default_enhancer
    if _default_enhancer is None:
        with _default_enhancer_lock:
            if _default_enhancer is None:
                _default_enhancer = AIPEAEnhancer()
    return _default_enhancer


def reset_enhancer() -> None:
    """Reset the default enhancer singleton.

    Thread-safe via the same lock used in get_enhancer().
    Useful for testing or when configuration needs to change.
    """
    global _default_enhancer
    with _default_enhancer_lock:
        _default_enhancer = None
    logger.info("Default enhancer reset")


async def enhance_prompt(
    query: str,
    model_id: str,
    security_level: SecurityLevel = SecurityLevel.UNCLASSIFIED,
) -> EnhancementResult:
    """Convenience function for quick prompt enhancement.

    Uses the default singleton enhancer to enhance a query.

    Args:
        query: The user's query to enhance
        model_id: Target model identifier
        security_level: Security classification level

    Returns:
        EnhancementResult with enhanced prompt and metadata

    Example:
        >>> result = await enhance_prompt(
        ...     "What are the latest AI developments?",
        ...     model_id="gpt-4"
        ... )
        >>> print(result.enhanced_prompt)
    """
    return await get_enhancer().enhance(query, model_id, security_level)


# =============================================================================
# EXPORTS
# =============================================================================


__all__ = [
    "AIPEAEnhancer",
    "ComplianceMode",
    "EnhancedRequest",
    "EnhancementResult",
    "ProcessingTier",
    "QueryType",
    "SecurityLevel",
    "StorageTier",
    "enhance_prompt",
    "get_enhancer",
    "get_model_family",
    "is_offline_model",
    "reset_enhancer",
]
