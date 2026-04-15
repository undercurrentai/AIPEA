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
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import httpx

from aipea._types import ProcessingTier, QueryType, SearchStrategy, get_model_family
from aipea.analyzer import QueryAnalyzer
from aipea.engine import PromptEngine
from aipea.knowledge import KnowledgeDomain, OfflineKnowledgeBase, StorageTier
from aipea.models import QueryAnalysis
from aipea.quality import QualityAssessor, QualityScore
from aipea.search import SearchContext, SearchOrchestrator, SearchResult, create_empty_context
from aipea.security import (
    ComplianceHandler,
    ComplianceMode,
    ScanResult,
    SecurityContext,
    SecurityLevel,
    SecurityScanner,
)

if TYPE_CHECKING:
    from aipea.engine import OfflineTierProcessor  # used as type hint for _ollama_processor
    from aipea.learning import LearningPolicy  # used as type hint for __init__ param

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
        clarifications: Advisory clarifying questions for ambiguous queries (max 3)
        quality_score: Optional quality assessment of the enhancement (None if not computed)
    """

    original_query: str
    enhanced_prompt: str
    processing_tier: ProcessingTier
    security_context: SecurityContext
    query_analysis: QueryAnalysis
    search_context: SearchContext | None = None
    enhancement_time_ms: float = 0.0
    was_enhanced: bool = True
    enhancement_notes: list[str] = field(default_factory=list)
    clarifications: list[str] = field(default_factory=list)
    quality_score: QualityScore | None = None
    strategy_used: str = ""

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
            "clarifications": self.clarifications,
            "quality_score": self.quality_score.to_dict() if self.quality_score else None,
            "strategy_used": self.strategy_used,
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


# Re-export canonical definitions for backward compatibility
from aipea._types import MODEL_FAMILY_MAP as MODEL_FAMILY_MAP  # noqa: E402

# Offline-capable models
OFFLINE_MODELS: set[str] = {
    "gpt-oss-20b",
    "llama-3.3-70b",
    "llama-3.2-3b",
    "gemma-3n",
    "gemma3:1b",
    "gemma3:270m",
    "phi3:mini",
}


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
        enable_learning: bool = False,
        learning_policy: LearningPolicy | None = None,
    ) -> None:
        """Initialize the prompt enhancement facade.

        Args:
            enable_enhancement: Whether to enable enhancement (default True)
            storage_tier: Storage tier for offline knowledge base
            default_compliance: Default compliance mode for requests
            exa_api_key: Optional API key for Exa search provider
            firecrawl_api_key: Optional API key for Firecrawl provider
            enable_learning: Whether to enable adaptive strategy learning
            learning_policy: Compliance-aware policy for the learning engine.
                Controls which compliance modes may persist feedback and
                configures retention limits.  See :class:`LearningPolicy`.
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
                    tier=storage_tier,
                )
            except (sqlite3.Error, OSError, RuntimeError) as e:
                logger.warning("Failed to initialize offline knowledge base: %s", e)
                self._offline_kb = None

        # Ollama processor (lazily initialized, reused across calls)
        self._ollama_processor: OfflineTierProcessor | None = None

        # Adaptive learning engine (opt-in)
        self._learning_engine: AdaptiveLearningEngine | None = None
        if enable_learning:
            try:
                from aipea.learning import AdaptiveLearningEngine, LearningPolicy

                policy = learning_policy or LearningPolicy()
                self._learning_engine = AdaptiveLearningEngine(policy=policy)
            except (sqlite3.Error, OSError, RuntimeError) as e:
                logger.warning("Failed to initialize learning engine: %s", e)
                self._learning_engine = None

        # Thread-safe statistics tracking
        self._stats_lock = threading.Lock()
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

    def close(self) -> None:
        """Close resources held by this enhancer (e.g. SQLite connections)."""
        if self._offline_kb is not None:
            self._offline_kb.close()
            self._offline_kb = None
        if self._learning_engine is not None:
            self._learning_engine.close()
            self._learning_engine = None

    def __enter__(self) -> AIPEAEnhancer:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _generate_clarifications(self, query: str, analysis: QueryAnalysis) -> list[str]:
        """Generate advisory clarifying questions for ambiguous queries.

        Produces up to 3 clarifying questions based on query analysis signals.
        These are advisory only — the enhancement still proceeds best-effort.

        Args:
            query: The original user query.
            analysis: The query analysis result.

        Returns:
            List of clarifying question strings (max 3).
        """
        clarifications: list[str] = []

        # High ambiguity → ask for specificity
        if analysis.ambiguity_score > 0.6:
            clarifications.append(
                "Could you be more specific about what aspect you're interested in?"
            )

        # No detected entities → ask for domain/topic
        if not analysis.detected_entities:
            query_type_label = analysis.query_type.value.replace("_", " ")
            clarifications.append(f"What specific {query_type_label} topic are you asking about?")

        # High complexity without clear search strategy → ask about depth
        if analysis.complexity >= 0.7 and analysis.search_strategy.value == "none":
            clarifications.append(
                "Are you looking for a high-level summary or a deep technical dive?"
            )

        # Short query (fewer than 4 words) → suggest more context
        if len(query.split()) < 4 and not clarifications:
            clarifications.append("Could you provide more context to help refine the response?")

        # Low confidence → suggest rephrasing
        if analysis.confidence < 0.4 and len(clarifications) < 3:
            clarifications.append(
                "The intent isn't fully clear — could you rephrase or add more detail?"
            )

        # Incorporate enhancement suggestions from analyzer (reformulated as questions)
        if len(clarifications) < 3:
            suggestions = self._query_analyzer.suggest_enhancements(query, analysis)
            for suggestion in suggestions:
                if len(clarifications) >= 3:
                    break
                # Skip suggestions that substantially overlap with existing clarifications
                suggestion_lower = suggestion.lower()
                if any(
                    suggestion_lower in c.lower() or c.lower() in suggestion_lower
                    for c in clarifications
                ):
                    continue
                # Reformulate suggestion as a question if not already one
                if not suggestion.endswith("?"):
                    suggestion = f"Would it help to {suggestion[0].lower()}{suggestion[1:]}"
                    if not suggestion.endswith("?"):
                        suggestion = suggestion.rstrip(".") + "?"
                clarifications.append(suggestion)
                if len(clarifications) >= 3:
                    break

        return clarifications[:3]

    async def enhance(
        self,
        query: str,
        model_id: str,
        security_level: SecurityLevel = SecurityLevel.UNCLASSIFIED,
        compliance_mode: ComplianceMode | None = None,
        force_offline: bool = False,
        include_search: bool = True,
        format_for_model: bool = True,
        strategy: str | None = None,
        embed_search_context: bool = True,
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
            include_search: Include search context in enhancement (default True).
                           Set False to skip search/KB context gathering.
            format_for_model: Apply model-specific formatting (default True).
                             Set False for generic prompt structure.

        Returns:
            EnhancementResult with enhanced prompt and metadata

        Example:
            >>> result = await enhancer.enhance(
            ...     "Explain quantum computing",
            ...     model_id="claude-3-opus"
            ... )
            >>> print(result.enhanced_prompt)
        """
        if not query or not query.strip():
            logger.debug("Empty query provided to enhance()")
            return EnhancementResult(
                original_query=query or "",
                enhanced_prompt=query or "",
                processing_tier=ProcessingTier.OFFLINE,
                security_context=SecurityContext(),
                query_analysis=QueryAnalysis(
                    query=query or "",
                    query_type=QueryType.UNKNOWN,
                    complexity=0.0,
                    confidence=0.0,
                    needs_current_info=False,
                ),
                was_enhanced=False,
                enhancement_notes=["Empty query provided"],
            )

        start_time = time.perf_counter()
        enhancement_notes: list[str] = []

        # Use default compliance if not specified
        if compliance_mode is None:
            compliance_mode = self._default_compliance

        # If enhancement is disabled, pass through
        if not self._enable_enhancement:
            with self._stats_lock:
                self._stats["queries_passthrough"] += 1
                self._stats["compliance_distribution"][compliance_mode.value] += 1
            return self._create_passthrough_result(
                query, model_id, security_level, compliance_mode, start_time
            )

        # FEDRAMP is deprecated as of v1.3.4; the ComplianceHandler constructor
        # (below) emits the canonical DeprecationWarning. We log a compact
        # pointer here for operators reading enhancer.py logs. Scheduled for
        # removal in v2.0.0. See docs/adr/ADR-002-fedramp-removal.md.
        if compliance_mode == ComplianceMode.FEDRAMP:
            logger.warning("FEDRAMP mode is deprecated and provides no enforcement — see ADR-002")

        # Step 1: Create security context
        compliance_handler = ComplianceHandler(compliance_mode)
        security_context = compliance_handler.create_security_context(
            has_connectivity=not force_offline,
        )
        security_context.security_level = security_level

        # Enforce compliance-mode model restrictions and global forbidden list
        if not compliance_handler.validate_model(model_id):
            with self._stats_lock:
                self._stats["queries_blocked"] += 1
                self._stats["compliance_distribution"][compliance_mode.value] += 1
            enhancement_notes.append(
                f"Model '{model_id}' is not allowed in compliance mode '{compliance_mode.value}'"
            )
            return self._create_blocked_result(
                query,
                model_id,
                security_context,
                ScanResult(
                    flags=[f"model_not_allowed:{model_id}"],
                    is_blocked=True,
                ),
                compliance_mode,
                start_time,
                enhancement_notes,
            )

        # Step 2: Security scan
        scan_result = self._security_scanner.scan(query, security_context)

        if scan_result.is_blocked:
            with self._stats_lock:
                self._stats["queries_blocked"] += 1
                self._stats["compliance_distribution"][compliance_mode.value] += 1
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

        # Step 3b: Generate dialogical clarifications (advisory only)
        clarifications = self._generate_clarifications(query, analysis)

        # Step 4: Determine if offline mode is required
        offline_required = self._is_offline_required(
            security_level,
            compliance_mode,
            force_offline,
        )

        if offline_required:
            enhancement_notes.append("Processing in offline mode due to security/connectivity")

        # Step 5: Gather context (skipped when include_search=False)
        search_context = await self._gather_context_for_enhance(
            query,
            analysis,
            security_context,
            offline_required,
            include_search,
            enhancement_notes,
        )

        # Step 6: Determine processing tier
        processing_tier = analysis.suggested_tier or ProcessingTier.OFFLINE
        if offline_required:
            # Offline-required requests must report OFFLINE tier for consistency
            processing_tier = ProcessingTier.OFFLINE

        # Step 6b: Ollama LLM enhancement (offline mode only)
        # When Ollama models are available, use OfflineTierProcessor for
        # real LLM-assisted query analysis before final prompt formulation.
        ollama_analysis: str | None = None
        if offline_required:
            ollama_analysis = await self._try_ollama_enhancement(query, enhancement_notes)

        # Step 7: Formulate enhanced prompt
        model_family = get_model_family(model_id) if format_for_model else "general"

        # Determine complexity string from actual analysis score
        if analysis.complexity >= 0.7:
            complexity = "complex"
        elif analysis.complexity >= 0.4:
            complexity = "medium"
        else:
            complexity = "simple"

        # If Ollama provided LLM analysis, prepend it to the query for richer context
        effective_query = query
        if ollama_analysis:
            effective_query = f"{query}\n\n[Offline LLM Analysis]\n{ollama_analysis}"

        effective_strategy = self._resolve_strategy(
            strategy, analysis.query_type, enhancement_notes
        )

        # Formulate the enhanced prompt
        enhanced_prompt = await self._prompt_engine.formulate_search_aware_prompt(
            query=effective_query,
            complexity=complexity,
            search_context=search_context,
            model_type=model_family,
            query_type=analysis.query_type.value,
            strategy=effective_strategy,
            embed_search_context=embed_search_context,
        )

        # Calculate timing
        enhancement_time_ms = (time.perf_counter() - start_time) * 1000

        # Update statistics (thread-safe)
        with self._stats_lock:
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

        # Compute quality score
        quality_score = QualityAssessor().assess(query, enhanced_prompt)

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
            strategy_used=effective_strategy,
            clarifications=clarifications,
            quality_score=quality_score,
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

        # Empty-query short circuit. Mirrors enhance()'s early return at
        # the top of the method: downstream per-model prompt building would
        # produce templates with literally empty query sections, leaking
        # malformed prompts instead of signalling the empty input. (#103)
        if not query or not query.strip():
            logger.debug("Empty query provided to enhance_for_models()")
            return results

        # Filter model list to those allowed by current compliance policy.
        # If none are allowed, skip enhancement entirely.
        compliance_handler = ComplianceHandler(self._default_compliance)
        compliant_model_ids: list[str] = []
        for model_id in model_ids:
            if compliance_handler.validate_model(model_id):
                compliant_model_ids.append(model_id)
            else:
                logger.warning("Skipping forbidden model in enhance_for_models: %s", model_id)

        if not compliant_model_ids:
            logger.warning("No compliant models provided in enhance_for_models; returning empty")
            return results

        # Perform base enhancement once to run the security scan, query
        # analysis, and search-context fetch.  We set embed_search_context
        # to False here because per-model prompts are (re)built below via
        # formulate_search_aware_prompt using the CACHED search context —
        # that way every model gets its own query-section format
        # (GPT markdown / Claude XML / Gemini numbered) instead of the
        # first model's format baked in. (#90)
        base_model = compliant_model_ids[0]
        base_result = await self.enhance(
            query=query,
            model_id=base_model,
            security_level=security_level,
            compliance_mode=self._default_compliance,
            force_offline=compliance_handler.force_offline,
            embed_search_context=False,
        )

        # If the base enhancement was blocked (e.g. injection detected),
        # do not rebuild per-model prompts.
        is_blocked = (
            not base_result.was_enhanced
            and base_result.original_query != base_result.enhanced_prompt
        )
        if is_blocked:
            logger.warning(
                "Base enhancement blocked in enhance_for_models; returning empty results"
            )
            return results

        # Compute complexity string from the cached analysis — same
        # mapping as enhance() lines 588-593.
        complexity_score = base_result.query_analysis.complexity
        if complexity_score >= 0.7:
            complexity = "complex"
        elif complexity_score >= 0.4:
            complexity = "medium"
        else:
            complexity = "simple"

        query_type_value = base_result.query_analysis.query_type.value

        for model_id in compliant_model_ids:
            model_family = get_model_family(model_id)

            # Rebuild the full per-model prompt using the cached
            # search_context.  formulate_search_aware_prompt dispatches
            # on model_type to emit "## Query" for GPT, "<query>...</query>"
            # for Claude, and the numbered format for Gemini — the whole
            # point of the #90 fix.  Search context framing header
            # (wave 17 #86) is embedded inside formulate_search_aware_prompt
            # so nothing is lost.
            model_prompt = await self._prompt_engine.formulate_search_aware_prompt(
                query=query,
                complexity=complexity,
                search_context=base_result.search_context,
                model_type=model_family,
                query_type=query_type_value,
                strategy=base_result.strategy_used or None,  # (#109)
                embed_search_context=True,
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
                    "query_type": query_type_value,
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

    async def _gather_context_for_enhance(
        self,
        query: str,
        analysis: QueryAnalysis,
        security_context: SecurityContext,
        offline_required: bool,
        include_search: bool,
        enhancement_notes: list[str],
    ) -> SearchContext | None:
        """Gather search/KB context for the enhance pipeline.

        Handles offline vs online routing, search result security scanning,
        and enhancement notes. Returns None when search is disabled or no
        results are found.

        Args:
            query: The user's query
            analysis: Query analysis results
            security_context: Active security context
            offline_required: Whether offline mode is forced
            include_search: Whether to gather search context
            enhancement_notes: Mutable list for pipeline notes
        """
        if not include_search:
            enhancement_notes.append("Search context skipped (include_search=False)")
            return None

        if offline_required:
            search_context = await self._gather_offline_context(query, analysis)
            if search_context and not search_context.is_empty():
                enhancement_notes.append(
                    f"Offline context gathered: {len(search_context.results)} results"
                )
            else:
                if self._offline_kb is None:
                    enhancement_notes.append(
                        "Offline knowledge base not initialized — "
                        "run 'aipea seed-kb' to populate it"
                    )
            return search_context

        search_context = await self._gather_online_context(query, analysis, security_context)
        if search_context and not search_context.is_empty():
            source = search_context.source
            raw_count = len(search_context.results)
            # Scan search results for injection attacks AND compliance leaks
            # (PHI in HIPAA mode, classified markers in TACTICAL mode). The
            # caller's security_context is plumbed through so mode-gated
            # PHI/classified scans actually run on scraped web content. (#96)
            search_context = self._scan_search_results(search_context, security_context)
            filtered_count = raw_count - len(search_context.results)
            if filtered_count > 0:
                enhancement_notes.append(
                    f"Online context from {source}: {raw_count} results"
                    f" ({filtered_count} filtered for security)"
                )
            else:
                enhancement_notes.append(
                    f"Online context gathered from {source}: {len(search_context.results)} results"
                )
        elif analysis.search_strategy != SearchStrategy.NONE:
            enhancement_notes.append(
                "No search context available — configure API keys "
                "with 'aipea configure' to enable web search"
            )
        return search_context

    def _scan_search_results(
        self,
        search_context: SearchContext,
        caller_ctx: SecurityContext | None = None,
    ) -> SearchContext:
        """Scan search result snippets for injection attacks and compliance leaks.

        Filters out search results whose content triggers the security
        scanner — either a prompt injection attempt embedded in a scraped
        page, OR (when the caller is in HIPAA / TACTICAL mode) a snippet
        containing PHI / classified markers that must not be forwarded to
        downstream models in those modes. (#96)

        Args:
            search_context: Search context with results to scan
            caller_ctx: The active SecurityContext from the enhance() call.
                If None (back-compat), a default GENERAL context is used and
                only injection filtering runs — callers should plumb through
                the real context so PHI / classified filtering engages in
                HIPAA / TACTICAL mode.

        Returns:
            Filtered SearchContext with dangerous results removed
        """
        if search_context.is_empty():
            return search_context

        # Mirror the caller's compliance mode into the scan context so
        # PHI/classified checks actually run. Security level stays
        # UNCLASSIFIED because the snippet text originates from the web,
        # not the user's query. (#96)
        if caller_ctx is not None:
            scan_ctx = SecurityContext(
                compliance_mode=caller_ctx.compliance_mode,
                security_level=SecurityLevel.UNCLASSIFIED,
            )
        else:
            scan_ctx = SecurityContext(
                compliance_mode=ComplianceMode.GENERAL,
                security_level=SecurityLevel.UNCLASSIFIED,
            )
        hipaa_mode = scan_ctx.compliance_mode == ComplianceMode.HIPAA
        tactical_mode = scan_ctx.compliance_mode == ComplianceMode.TACTICAL

        safe_results: list[SearchResult] = []
        for result in search_context.results:
            snippet = result.snippet or ""
            if snippet:
                scan = self._security_scanner.scan(snippet, scan_ctx)
                if scan.is_blocked:
                    logger.warning(
                        "Search result filtered (injection detected): %s",
                        result.title or result.url,
                    )
                    continue
                # PHI / classified markers / PII are surfaced as flags
                # rather than is_blocked by SecurityScanner.scan. In HIPAA
                # mode we must not forward PHI-containing or PII-containing
                # web snippets to downstream models — HIPAA Safe Harbor
                # explicitly classifies SSN, account numbers, and similar
                # direct identifiers as PHI, so PII flags also warrant
                # filtering in HIPAA mode (ultrathink audit, wave 19).
                # In TACTICAL mode ditto for classified markers and PII
                # (direct identifiers should not leak to an external LLM
                # in an air-gapped workflow). (#96)
                has_phi = any(f.startswith("phi_detected:") for f in scan.flags)
                has_pii = any(f.startswith("pii_detected:") for f in scan.flags)
                has_classified = any(f.startswith("classified_marker:") for f in scan.flags)
                if hipaa_mode and (has_phi or has_pii):
                    logger.warning(
                        "Search result filtered (PHI/PII in HIPAA mode): %s",
                        result.title or result.url,
                    )
                    continue
                if tactical_mode and (has_classified or has_pii):
                    logger.warning(
                        "Search result filtered (classified/PII in TACTICAL mode): %s",
                        result.title or result.url,
                    )
                    continue
            safe_results.append(result)

        if len(safe_results) < len(search_context.results):
            filtered_count = len(search_context.results) - len(safe_results)
            logger.info("Filtered %d search results for security", filtered_count)

        return SearchContext(
            query=search_context.query,
            results=safe_results,
            timestamp=search_context.timestamp,
            source=search_context.source,
            confidence=search_context.confidence,
        )

    async def _gather_online_context(
        self,
        query: str,
        analysis: QueryAnalysis,
        security_context: SecurityContext,
    ) -> SearchContext | None:
        """Gather context from online search providers.

        Uses the SearchOrchestrator to gather relevant context
        based on the query analysis search strategy.

        Args:
            query: The user's query
            analysis: Query analysis with search strategy
            security_context: Security context for filtering (reserved for
                future security-level-aware search filtering)

        Returns:
            SearchContext with search results, or None if unavailable
        """
        # Log security context for audit trail; future: filter results by level
        logger.debug(
            "Online context gather: security_level=%s, compliance=%s",
            security_context.security_level.value,
            security_context.compliance_mode.value,
        )
        if analysis.search_strategy == SearchStrategy.NONE:
            logger.debug("Search strategy NONE, skipping online context")
            return None

        if self._search_orchestrator is None:
            logger.debug("Search orchestrator not available, skipping online context")
            return None

        # Map analysis search strategy to orchestrator strategy string
        strategy_name = analysis.search_strategy.value
        strategy = strategy_name if strategy_name != "none" else "quick_facts"

        try:
            context = await self._search_orchestrator.search(
                query=query,
                strategy=strategy,
                num_results=5,
            )
            return context
        except (httpx.HTTPError, KeyError, ValueError) as e:
            logger.warning("Online search failed: %s", e)
            return None

    async def _gather_offline_context(
        self,
        query: str,
        analysis: QueryAnalysis,
    ) -> SearchContext | None:
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

        # Map query type to knowledge domain (GENERAL for non-specialized types)
        domain_map: dict[QueryType, KnowledgeDomain] = {
            QueryType.TECHNICAL: KnowledgeDomain.TECHNICAL,
            QueryType.RESEARCH: KnowledgeDomain.GENERAL,
            QueryType.CREATIVE: KnowledgeDomain.GENERAL,
            QueryType.ANALYTICAL: KnowledgeDomain.GENERAL,
            QueryType.OPERATIONAL: KnowledgeDomain.GENERAL,
            QueryType.STRATEGIC: KnowledgeDomain.GENERAL,
            QueryType.UNKNOWN: KnowledgeDomain.GENERAL,
        }

        domain = domain_map.get(analysis.query_type, KnowledgeDomain.GENERAL)

        try:
            # Prefer semantic (BM25) search; fall back to domain-filtered search
            semantic_result = await self._offline_kb.search_semantic(query=query, top_k=5)
            if semantic_result.nodes:
                nodes = semantic_result.nodes
            else:
                domain_result = await self._offline_kb.search(
                    query=query,
                    domain=domain,
                    limit=5,
                )
                nodes = domain_result.nodes

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

            return SearchContext(
                query=query,
                results=results,
                timestamp=datetime.now(UTC),
                source="offline_kb",
                confidence=sum(r.score for r in results) / len(results) if results else 0.0,
            )

        except (sqlite3.Error, OSError, ValueError, TypeError) as e:
            logger.warning("Offline search failed: %s", e)
            return None

    async def _try_ollama_enhancement(
        self,
        query: str,
        enhancement_notes: list[str],
    ) -> str | None:
        """Attempt LLM-enhanced analysis via Ollama in offline mode.

        Uses the OfflineTierProcessor to run a local Ollama model for
        real LLM-assisted query analysis. Gracefully returns None if
        Ollama is unavailable or processing fails.

        Args:
            query: The user's query
            enhancement_notes: List to append status notes to

        Returns:
            LLM analysis text, or None if Ollama is not available
        """
        try:
            from aipea.engine import OfflineTierProcessor

            if self._ollama_processor is None:
                self._ollama_processor = OfflineTierProcessor(use_ollama=True)
            result = await self._ollama_processor.process(query)

            if result.enhancement_metadata.get("llm_enhanced"):
                model_name = result.enhancement_metadata.get("ollama_model", "unknown")
                enhancement_notes.append(f"Ollama LLM enhancement via {model_name}")
                logger.info("Ollama LLM enhancement succeeded with model %s", model_name)
                return result.enhanced_query

            logger.debug("Ollama not available, skipping LLM enhancement")
            enhancement_notes.append(
                "Offline LLM enhancement skipped (Ollama not available) — "
                "using template-based enhancement"
            )
            return None

        except (RuntimeError, OSError, ValueError) as e:
            logger.debug("Ollama enhancement skipped: %s", e)
            enhancement_notes.append(
                "Offline LLM enhancement skipped (Ollama not available) — "
                "using template-based enhancement"
            )
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
            enhancement_notes=[
                f"Enhancement disabled for model '{model_id}' - query passed through unmodified"
            ],
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
            scan_result: Security scan result with flags
            compliance_mode: Compliance mode
            start_time: Start time for timing calculation
            enhancement_notes: Notes to include

        Returns:
            EnhancementResult indicating blocked query
        """
        # Enrich notes with audit-trail metadata
        enhancement_notes.append(f"Blocked for model '{model_id}'")
        enhancement_notes.append(f"Compliance mode: {compliance_mode.value}")
        if scan_result.flags:
            enhancement_notes.append(f"Security flags: {', '.join(scan_result.flags)}")

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

    def _resolve_strategy(
        self,
        caller_strategy: str | None,
        query_type: QueryType,
        enhancement_notes: list[str],
    ) -> str:
        """Resolve the effective strategy: learned > caller override > default."""
        from aipea.strategies import select_strategy_for_query_type

        if self._learning_engine is not None and caller_strategy is None:
            learned = self._learning_engine.get_best_strategy(query_type)
            if learned is not None:
                enhancement_notes.append(f"Using learned strategy: {learned}")
                return learned
        return caller_strategy or select_strategy_for_query_type(query_type)

    async def record_feedback(self, result: EnhancementResult, score: float) -> None:
        """Record user feedback on an enhancement result for adaptive learning.

        Compliance gating is handled by the underlying
        :class:`~aipea.learning.AdaptiveLearningEngine` — TACTICAL mode always
        blocks, HIPAA blocks unless opted in via ``LearningPolicy``.

        Args:
            result: The enhancement result to provide feedback on
            score: Satisfaction score in [-1.0, 1.0] (positive = good)
        """
        if self._learning_engine is not None and result.strategy_used:
            await self._learning_engine.arecord_feedback(
                query_type=result.query_analysis.query_type,
                strategy=result.strategy_used,
                score=score,
                compliance_mode=result.security_context.compliance_mode,
            )

    def _update_avg_time(self, new_time_ms: float) -> None:
        """Update the rolling average enhancement time.

        Note: Caller must hold ``_stats_lock``.

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
        with self._stats_lock:
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
                "tier_distribution": dict(self._stats["tier_distribution"]),
                "compliance_distribution": dict(self._stats["compliance_distribution"]),
                "learning_enabled": self._learning_engine is not None,
                "learning_stats": (
                    self._learning_engine.get_stats() if self._learning_engine is not None else None
                ),
            }

    def reset_stats(self) -> None:
        """Reset all statistics counters."""
        with self._stats_lock:
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
    Closes the knowledge base connection before discarding.
    Useful for testing or when configuration needs to change.
    """
    global _default_enhancer
    with _default_enhancer_lock:
        if _default_enhancer is not None:
            _default_enhancer.close()
        _default_enhancer = None
    logger.info("Default enhancer reset")


async def enhance_prompt(
    query: str,
    model_id: str,
    security_level: SecurityLevel = SecurityLevel.UNCLASSIFIED,
    compliance_mode: ComplianceMode | None = None,
    force_offline: bool = False,
    include_search: bool = True,
    format_for_model: bool = True,
    strategy: str | None = None,
) -> EnhancementResult:
    """Convenience function for quick prompt enhancement.

    Uses the default singleton enhancer to enhance a query.

    Args:
        query: The user's query to enhance
        model_id: Target model identifier
        security_level: Security classification level
        compliance_mode: Compliance mode (HIPAA, TACTICAL, etc.) or None for default
        force_offline: Force air-gapped mode regardless of security level
        include_search: Include search context in enhancement (default True)
        format_for_model: Apply model-specific formatting (default True)
        strategy: Named enhancement strategy override (default: auto-select)

    Returns:
        EnhancementResult with enhanced prompt and metadata

    Example:
        >>> result = await enhance_prompt(
        ...     "What are the latest AI developments?",
        ...     model_id="gpt-4"
        ... )
        >>> print(result.enhanced_prompt)
    """
    if not query or not query.strip():
        logger.debug("Empty query provided to enhance_prompt()")
        return EnhancementResult(
            original_query=query or "",
            enhanced_prompt=query or "",
            processing_tier=ProcessingTier.OFFLINE,
            security_context=SecurityContext(),
            query_analysis=QueryAnalysis(
                query=query or "",
                query_type=QueryType.UNKNOWN,
                complexity=0.0,
                confidence=0.0,
                needs_current_info=False,
            ),
            was_enhanced=False,
            enhancement_notes=["Empty query provided"],
        )

    return await get_enhancer().enhance(
        query,
        model_id,
        security_level,
        compliance_mode,
        force_offline,
        include_search=include_search,
        format_for_model=format_for_model,
        strategy=strategy,
    )


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
