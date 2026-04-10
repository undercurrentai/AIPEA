"""AIPEA Prompt Engine - AI Query Enhancement.

This module provides the core prompt engineering capabilities:

- Query classification via pattern matching (OfflineTierProcessor)
- Model-aware query formatting (XML for Claude, markdown for GPT, etc.)
- Search context integration from multiple providers
- Offline/air-gapped support via Ollama
- Current year injection for temporal awareness

Design principles:
- Model-aware: Different AI models receive structurally optimized prompts
- Content-only: Enriches query content without prescribing response style
- Graceful degradation: Falls back to templates when LLM unavailable
- Type-safe: Full type hints throughout

Based on AIPEA design patterns.
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, ClassVar

from aipea._types import (
    QUERY_TYPE_PATTERNS,
    QUERY_TYPE_PRIORITY,
    ProcessingTier,
    QueryType,
    SearchStrategy,
)
from aipea.search import (
    ModelType,
    SearchOrchestrator,
    SearchResult,
    create_empty_context,
)
from aipea.search import SearchContext as SearchContext  # re-exported for backward compat

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================


class OfflineModel(Enum):
    """Offline model options for air-gapped environments via Ollama.

    These models can run locally without external API calls,
    suitable for classified or disconnected operations.

    IMPORTANT: Models must be pre-downloaded before going offline.
    Use `ollama pull <model>` during online setup phase.

    Tier 1 (Available - Tested):
        GEMMA3_270M: Google Gemma 3 270M - Ultra-lightweight (291MB)
        PHI3_MINI: Microsoft Phi-3 Mini - Small but capable (2.2GB)

    Tier 2/3 (Future - Require More Resources):
        GPT_OSS_20B: OpenAI OSS 20B - ~11GB, 16GB VRAM
        LLAMA_3_3_70B: Meta Llama 3.3 70B - ~40GB, 48GB+ VRAM
    """

    # Tier 1: Currently available and tested
    GEMMA3_1B = "gemma3:1b"  # Google 1B params, 815MB, good quality/size balance
    GEMMA3_270M = "gemma3:270m"  # Google 270M params, 291MB, edge-friendly
    PHI3_MINI = "phi3:mini"  # Microsoft 3.8B params, 2.2GB, good quality

    # Tier 2/3: Future enhancement (require download + more resources)
    GPT_OSS_20B = "gpt-oss-20b"  # OpenAI 20B, ~11GB - NOT YET AVAILABLE
    LLAMA_3_3_70B = "llama-3.3-70b"  # Meta 70B, ~40GB - NOT YET AVAILABLE

    @classmethod
    def tier1_models(cls) -> list[OfflineModel]:
        """Return Tier 1 models (tested and available)."""
        return [cls.GEMMA3_1B, cls.GEMMA3_270M, cls.PHI3_MINI]

    @classmethod
    def tier2_models(cls) -> list[OfflineModel]:
        """Return Tier 2/3 models (future enhancement)."""
        return [cls.GPT_OSS_20B, cls.LLAMA_3_3_70B]


# =============================================================================
# OLLAMA CLIENT FOR OFFLINE INFERENCE
# =============================================================================


@dataclass
class OllamaModelInfo:
    """Information about an available Ollama model.

    Attributes:
        name: Model name (e.g., "gemma3:270m")
        size_bytes: Size in bytes
        modified: Last modified timestamp
    """

    name: str
    size_bytes: int
    modified: str


class OllamaOfflineClient:
    """Client for running offline inference via Ollama.

    IMPORTANT: This client checks for pre-downloaded models.
    Models must be downloaded BEFORE going offline using `ollama pull <model>`.

    Example:
        >>> client = OllamaOfflineClient()
        >>> available = await client.get_available_models()
        >>> if OfflineModel.GEMMA3_270M.value in [m.name for m in available]:
        ...     response = await client.generate("Hello", OfflineModel.GEMMA3_270M)
    """

    DEFAULT_HOST = "http://localhost:11434"

    def __init__(self, host: str | None = None) -> None:
        """Initialize Ollama client.

        Args:
            host: Ollama server URL (default: AIPEA_OLLAMA_HOST env var or http://localhost:11434)
        """
        import os

        self.host = host or os.environ.get("AIPEA_OLLAMA_HOST", self.DEFAULT_HOST)
        self._available_models: list[OllamaModelInfo] | None = None
        logger.debug("OllamaOfflineClient initialized with host: %s", self.host)

    async def get_available_models(self) -> list[OllamaModelInfo]:
        """Get list of pre-downloaded Ollama models.

        Returns:
            List of available model info objects.
            Empty list if Ollama is not running or no models are downloaded.
        """
        import subprocess

        try:
            # Run blocking subprocess in thread to avoid blocking event loop
            result = await asyncio.to_thread(
                subprocess.run,
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.warning("Ollama list failed: %s", result.stderr)
                self._available_models = []
                return []

            models: list[OllamaModelInfo] = []
            lines = result.stdout.strip().split("\n")

            # Skip header line
            for line in lines[1:]:
                try:
                    parts = line.split()
                    if len(parts) >= 3:
                        name = parts[0]
                        # Parse size (e.g., "291 MB" -> bytes)
                        size_str = parts[2] if len(parts) > 2 else "0"
                        size_unit = parts[3] if len(parts) > 3 else "B"
                        try:
                            size_val = float(size_str)
                            if "GB" in size_unit:
                                size_bytes = int(size_val * 1_000_000_000)
                            elif "MB" in size_unit:
                                size_bytes = int(size_val * 1_000_000)
                            elif "KB" in size_unit:
                                size_bytes = int(size_val * 1_000)
                            else:
                                size_bytes = int(size_val)
                        except ValueError:
                            size_bytes = 0

                        models.append(
                            OllamaModelInfo(
                                name=name,
                                size_bytes=size_bytes,
                                modified=" ".join(parts[4:]) if len(parts) > 4 else "",
                            )
                        )
                except (IndexError, ValueError) as parse_err:
                    logger.debug(
                        "Skipping unparseable Ollama output line: %r (%s)", line, parse_err
                    )

            self._available_models = models
            logger.info("Found %d Ollama models: %s", len(models), [m.name for m in models])
            return models

        except subprocess.TimeoutExpired:
            logger.warning("Ollama list timed out")
            self._available_models = []
            return []
        except FileNotFoundError:
            logger.warning("Ollama not found in PATH")
            self._available_models = []
            return []
        except OSError as e:
            # Catch remaining OS-level errors (permissions, broken pipe, etc.)
            logger.warning(
                "Error listing Ollama models: %s: %s",
                type(e).__name__,
                e,
                exc_info=True,
            )
            self._available_models = []
            return []

    async def is_model_available(self, model: OfflineModel) -> bool:
        """Check if a specific model is downloaded and available.

        Args:
            model: OfflineModel to check

        Returns:
            True if model is available for offline use
        """
        if self._available_models is None:
            await self.get_available_models()

        if self._available_models:
            available_names = [m.name for m in self._available_models]
            return model.value in available_names
        return False

    async def get_best_available_model(self) -> OfflineModel | None:
        """Get the best available Tier 1 model.

        Preference order: phi3:mini (best quality) > gemma3:1b > gemma3:270m (fastest).

        Returns:
            Best available OfflineModel, or None if none available
        """
        if self._available_models is None:
            await self.get_available_models()

        if not self._available_models:
            return None

        available_names = [m.name for m in self._available_models]

        # Prefer phi3:mini for quality, then gemma3:1b, fallback to gemma3:270m
        preference_order = [
            OfflineModel.PHI3_MINI,
            OfflineModel.GEMMA3_1B,
            OfflineModel.GEMMA3_270M,
        ]
        for model in preference_order:
            if model.value in available_names:
                logger.info("Selected best available offline model: %s", model.value)
                return model

        logger.warning("No Tier 1 offline models available")
        return None

    # Maximum prompt length in bytes (128KB - generous limit for local models)
    _MAX_PROMPT_BYTES = 128 * 1024

    async def generate(
        self,
        prompt: str,
        model: OfflineModel,
        max_tokens: int = 512,  # reserved for future REST API migration
        temperature: float = 0.7,  # reserved for future REST API migration
    ) -> str:
        """Generate a response using an offline Ollama model.

        Args:
            prompt: Input prompt
            model: OfflineModel to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text response

        Raises:
            RuntimeError: If model is not available or generation fails
            ValueError: If prompt exceeds maximum length
        """
        import subprocess

        # Warn when callers pass non-default values for parameters that
        # the ollama CLI does not support (will be used after REST API migration).
        if max_tokens != 512:
            logger.warning(
                "max_tokens=%d ignored (ollama CLI does not support it; "
                "will be used when REST API migration completes)",
                max_tokens,
            )
        if temperature != 0.7:
            logger.warning(
                "temperature=%.2f ignored (ollama CLI does not support it; "
                "will be used when REST API migration completes)",
                temperature,
            )

        # Validate prompt length to prevent resource exhaustion
        prompt_bytes = len(prompt.encode("utf-8"))
        if prompt_bytes > self._MAX_PROMPT_BYTES:
            raise ValueError(
                f"Prompt too long ({prompt_bytes} bytes > {self._MAX_PROMPT_BYTES} max). "
                "Please reduce prompt size."
            )

        if not await self.is_model_available(model):
            raise RuntimeError(
                f"Model {model.value} not available. Download with: ollama pull {model.value}"
            )

        try:
            # Use ollama run for simple generation
            # Pass prompt via stdin to prevent command injection (security fix)
            # Note: ollama run does not support --num-predict/--temperature flags;
            # those are REST API options. We rely on Ollama defaults here.
            # Run blocking subprocess in thread to avoid blocking event loop
            result = await asyncio.to_thread(
                subprocess.run,
                ["ollama", "run", model.value],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=60,  # 60 second timeout for generation
            )

            if result.returncode != 0:
                logger.error("Ollama generation failed: %s", result.stderr)
                raise RuntimeError(f"Ollama generation failed: {result.stderr}")

            response = result.stdout.strip()
            logger.debug("Ollama generated %d chars with %s", len(response), model.value)
            return response

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Ollama generation timed out for {model.value}") from None
        except FileNotFoundError:
            raise RuntimeError("Ollama not found. Install from https://ollama.ai") from None
        except RuntimeError:
            raise
        except OSError as e:
            raise RuntimeError(f"Ollama generation error: {e}") from e


# Singleton accessor for Ollama client
_ollama_client: OllamaOfflineClient | None = None
_ollama_client_lock = threading.Lock()


def get_ollama_client() -> OllamaOfflineClient:
    """Get the singleton OllamaOfflineClient instance.

    Thread-safe via double-checked locking pattern.

    Returns:
        The global OllamaOfflineClient instance
    """
    global _ollama_client
    if _ollama_client is None:
        with _ollama_client_lock:
            if _ollama_client is None:
                _ollama_client = OllamaOfflineClient()
    return _ollama_client


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class EnhancedQuery:
    """Result of query enhancement through the prompt engine.

    Contains the original and enhanced query along with metadata
    about the processing that was performed.

    Attributes:
        original_query: The original user query
        enhanced_query: The enhanced/augmented query
        tier_used: Processing tier that was applied
        confidence: Confidence score of the enhancement (0.0-1.0)
        query_type: Classified type of the query
        search_context: Optional search context used in enhancement
        enhancement_metadata: Additional metadata about the enhancement
    """

    original_query: str
    enhanced_query: str
    tier_used: ProcessingTier
    confidence: float
    query_type: QueryType
    search_context: SearchContext | None = None
    enhancement_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate confidence score and search_context type."""
        # Coerce to float first (same pattern as SearchResult in search.py)
        try:
            self.confidence = float(self.confidence)
        except (TypeError, ValueError):
            logger.warning(
                "EnhancedQuery confidence has invalid type %s, defaulting to 0.0",
                type(self.confidence).__name__,
            )
            self.confidence = 0.0
        if math.isnan(self.confidence):
            logger.warning("EnhancedQuery confidence is NaN, defaulting to 0.0")
            self.confidence = 0.0
        if not 0.0 <= self.confidence <= 1.0:
            logger.warning(
                "EnhancedQuery confidence %s outside [0, 1] range, clamping",
                self.confidence,
            )
            self.confidence = max(0.0, min(1.0, self.confidence))
        # Runtime type guard: search_context may be assigned a wrong type at runtime
        # despite the type annotation (e.g., from untyped consumer code)
        ctx: object = self.search_context
        if ctx is not None and not isinstance(ctx, SearchContext):
            logger.warning(
                "EnhancedQuery search_context has unexpected type %s, setting to None",
                type(ctx).__name__,
            )
            self.search_context = None


# =============================================================================
# TIER PROCESSORS (ABSTRACT BASE)
# =============================================================================


class TierProcessor(ABC):
    """Abstract base class for tier processors.

    Each tier processor implements a specific level of query enhancement
    with different complexity, latency, and capability characteristics.

    Currently only OfflineTierProcessor exists. TacticalTierProcessor and
    StrategicTierProcessor are planned (see docs/ROADMAP.md P2/P3) and will
    extend this ABC.
    """

    @abstractmethod
    async def process(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> EnhancedQuery:
        """Process a query and return an enhanced version.

        Args:
            query: The original query to enhance
            context: Optional context dictionary for processing

        Returns:
            EnhancedQuery with enhancement results
        """
        pass

    @property
    @abstractmethod
    def tier(self) -> ProcessingTier:
        """Return the tier this processor handles.

        Returns:
            ProcessingTier enum value
        """
        pass


# =============================================================================
# TIER 0: OFFLINE PROCESSOR
# =============================================================================


class OfflineTierProcessor(TierProcessor):
    """Tier 0 (Offline) processor - Fast pattern-based enhancement.

    Uses pattern matching and template-based enhancement without
    external API calls. Suitable for air-gapped environments.

    Characteristics:
    - No external API calls
    - Pattern-based query classification
    - Template-driven enhancement
    - Latency: <2 seconds
    - Confidence range: 0.70-0.80
    """

    # Query type patterns sourced from canonical QUERY_TYPE_PATTERNS in _types.py

    # Enhancement templates by query type
    ENHANCEMENT_TEMPLATES: ClassVar[dict[QueryType, str]] = {
        QueryType.TECHNICAL: (
            "Technical Query: {query}\n\n"
            "Please provide a detailed technical response including:\n"
            "- Code examples where applicable\n"
            "- Best practices and conventions\n"
            "- Common pitfalls to avoid\n"
            "- References to documentation"
        ),
        QueryType.RESEARCH: (
            "Research Query: {query}\n\n"
            "Please provide a comprehensive research-oriented response including:\n"
            "- Key concepts and definitions\n"
            "- Current state of knowledge\n"
            "- Relevant studies or evidence\n"
            "- Areas of ongoing investigation"
        ),
        QueryType.CREATIVE: (
            "Creative Query: {query}\n\n"
            "Please provide a creative response that:\n"
            "- Explores multiple perspectives\n"
            "- Offers original ideas\n"
            "- Balances creativity with practicality\n"
            "- Inspires further exploration"
        ),
        QueryType.ANALYTICAL: (
            "Analytical Query: {query}\n\n"
            "Please provide a systematic analysis including:\n"
            "- Clear problem decomposition\n"
            "- Evaluation criteria\n"
            "- Data-driven insights where applicable\n"
            "- Actionable recommendations"
        ),
        QueryType.OPERATIONAL: (
            "Operational Query: {query}\n\n"
            "Please provide step-by-step guidance including:\n"
            "- Prerequisites and requirements\n"
            "- Detailed procedures\n"
            "- Verification steps\n"
            "- Troubleshooting tips"
        ),
        QueryType.STRATEGIC: (
            "Strategic Query: {query}\n\n"
            "Please provide strategic guidance including:\n"
            "- Context and background\n"
            "- Options and trade-offs\n"
            "- Recommended approach\n"
            "- Risk considerations"
        ),
        QueryType.UNKNOWN: (
            "Query: {query}\n\n"
            "Please provide a comprehensive response addressing all aspects of this query."
        ),
    }

    def __init__(self, use_ollama: bool = True) -> None:
        """Initialize the offline tier processor.

        Args:
            use_ollama: If True, attempt to use Ollama for real LLM processing
                       when models are available. Falls back to templates if not.
        """
        # Compile canonical patterns from _types.py
        self._compiled_patterns: dict[QueryType, list[re.Pattern[str]]] = {}
        for qtype, patterns in QUERY_TYPE_PATTERNS.items():
            self._compiled_patterns[qtype] = [re.compile(p, re.IGNORECASE) for p in patterns]

        self._use_ollama = use_ollama
        self._ollama_client: OllamaOfflineClient | None = None
        self._ollama_model: OfflineModel | None = None
        self._ollama_checked = False
        self._ollama_lock = asyncio.Lock()

        logger.debug(
            "OfflineTierProcessor initialized with %d query types, ollama=%s",
            len(QUERY_TYPE_PATTERNS),
            use_ollama,
        )

    @property
    def tier(self) -> ProcessingTier:
        """Return the tier this processor handles.

        Returns:
            ProcessingTier.OFFLINE
        """
        return ProcessingTier.OFFLINE

    def classify_query(self, query: str) -> QueryType:
        """Classify a query into a query type using pattern matching.

        Args:
            query: The query to classify

        Returns:
            Detected QueryType, or UNKNOWN if no patterns match
        """
        scores: dict[QueryType, int] = {}

        for qtype, patterns in self._compiled_patterns.items():
            score = sum(1 for p in patterns if p.search(query))
            if score > 0:
                scores[qtype] = score

        if not scores:
            return QueryType.UNKNOWN

        # Return the query type with the highest pattern match count
        # Tie-break by explicit priority (lower = higher priority)
        return max(
            scores.keys(),
            key=lambda k: (scores[k], -QUERY_TYPE_PRIORITY.get(k, 99)),
        )

    async def _check_ollama_availability(self) -> None:
        """Check if Ollama is available and select best model.

        This is called once on first process() call to avoid
        repeated checks. The result is cached. Uses asyncio.Lock
        for double-checked locking to prevent concurrent first-call races.
        """
        if self._ollama_checked:
            return

        async with self._ollama_lock:
            # Double-check after acquiring lock (concurrent callers may have finished)
            if self._ollama_checked:  # pragma: no branch
                return  # type: ignore[unreachable]

            if not self._use_ollama:
                logger.debug("Ollama disabled, using templates only")
                self._ollama_checked = True
                return

            try:
                self._ollama_client = get_ollama_client()
                self._ollama_model = await self._ollama_client.get_best_available_model()

                if self._ollama_model:
                    logger.info("Offline mode using Ollama model: %s", self._ollama_model.value)
                else:
                    logger.info("No Ollama models available, using templates only")
            except (RuntimeError, OSError) as e:
                logger.warning("Ollama check failed: %s, using templates only", e)
                self._ollama_client = None
                self._ollama_model = None

            self._ollama_checked = True

    async def process(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> EnhancedQuery:
        """Process a query using offline enhancement.

        Uses Ollama for real LLM processing if available and pre-downloaded,
        otherwise falls back to pattern-based template enhancement.

        Args:
            query: The original query to enhance
            context: Optional context (may contain knowledge_base, use_llm)

        Returns:
            EnhancedQuery with enhancement results
        """
        logger.debug("OfflineTierProcessor processing query: %s...", query[:50])

        # Check Ollama availability (once)
        await self._check_ollama_availability()

        # Classify the query
        query_type = self.classify_query(query)

        # Check if context requests LLM processing
        use_llm = context.get("use_llm", True) if context else True

        # Try Ollama if available and requested
        if use_llm and self._ollama_client and self._ollama_model:
            try:
                return await self._process_with_ollama(query, query_type)
            except (RuntimeError, OSError, ValueError) as e:
                logger.warning("Ollama processing failed: %s, falling back to templates", e)

        # Fall back to template-based enhancement
        strategy_name = context.get("strategy") if context else None
        return await self._process_with_templates(query, query_type, strategy_name)

    async def _process_with_ollama(
        self,
        query: str,
        query_type: QueryType,
    ) -> EnhancedQuery:
        """Process query using Ollama LLM.

        Args:
            query: The original query
            query_type: Classified query type

        Returns:
            EnhancedQuery with LLM-enhanced content
        """
        if self._ollama_client is None:
            raise RuntimeError("Ollama client not initialized")
        if self._ollama_model is None:
            raise RuntimeError("Ollama model not configured")

        # Build system prompt based on query type
        system_prompts = {
            QueryType.TECHNICAL: (
                "You are a technical expert. Provide detailed, accurate technical responses."
            ),
            QueryType.RESEARCH: (
                "You are a research analyst. Provide evidence-based, comprehensive responses."
            ),
            QueryType.CREATIVE: (
                "You are a creative advisor. Provide innovative, inspiring responses."
            ),
            QueryType.ANALYTICAL: (
                "You are a data analyst. Provide systematic, analytical responses."
            ),
            QueryType.OPERATIONAL: (
                "You are an operations expert. Provide clear, step-by-step guidance."
            ),
            QueryType.STRATEGIC: (
                "You are a strategic advisor. Provide thoughtful, high-level guidance."
            ),
            QueryType.UNKNOWN: "You are a helpful assistant. Provide comprehensive responses.",
        }

        system = system_prompts.get(query_type, system_prompts[QueryType.UNKNOWN])
        full_prompt = f"{system}\n\nQuery: {query}\n\nResponse:"

        response = await self._ollama_client.generate(full_prompt, self._ollama_model)

        return EnhancedQuery(
            original_query=query,
            enhanced_query=response,
            tier_used=ProcessingTier.OFFLINE,
            confidence=0.82,  # Higher confidence with real LLM
            query_type=query_type,
            search_context=None,
            enhancement_metadata={
                "processor": "offline",
                "ollama_model": self._ollama_model.value,
                "pattern_match": query_type != QueryType.UNKNOWN,
                "llm_enhanced": True,
            },
        )

    async def _process_with_templates(
        self,
        query: str,
        query_type: QueryType,
        strategy_name: str | None = None,
    ) -> EnhancedQuery:
        """Process query using template-based enhancement (fallback).

        Args:
            query: The original query
            query_type: Classified query type
            strategy_name: Optional override for the enhancement strategy

        Returns:
            EnhancedQuery with template-based enhancement
        """
        from aipea.strategies import apply_strategy, select_strategy_for_query_type

        # Get the appropriate template
        template = self.ENHANCEMENT_TEMPLATES.get(
            query_type, self.ENHANCEMENT_TEMPLATES[QueryType.UNKNOWN]
        )

        # Apply the template without format-string injection risks
        enhanced = template.replace("{query}", query)

        # Apply named strategy techniques for additional structure
        effective_strategy = strategy_name or select_strategy_for_query_type(query_type)
        strategy_output = apply_strategy(query, effective_strategy)
        if strategy_output:
            enhanced = f"{enhanced}\n\n[Enhancement Context]\n{strategy_output}"

        # Determine confidence based on classification
        confidence = 0.70 if query_type == QueryType.UNKNOWN else 0.75

        return EnhancedQuery(
            original_query=query,
            enhanced_query=enhanced,
            tier_used=ProcessingTier.OFFLINE,
            confidence=confidence,
            query_type=query_type,
            search_context=None,
            enhancement_metadata={
                "processor": "offline",
                "pattern_match": query_type != QueryType.UNKNOWN,
                "llm_enhanced": False,
            },
        )


# =============================================================================
# MAIN PROMPT ENGINE
# =============================================================================


class PromptEngine:
    """AIPEA Prompt Engine - Core query enhancement system.

    Provides model-specific prompt optimization for different AI providers.

    Features:
    - Query classification via OfflineTierProcessor
    - Model-aware query formatting (XML for Claude, markdown for GPT, etc.)
    - Search context integration
    - Current year injection for temporal awareness

    Example:
        >>> engine = PromptEngine()
        >>> prompt = await engine.formulate_search_aware_prompt(
        ...     query="Explain quantum computing",
        ...     complexity="medium",
        ...     search_context=None,
        ...     model_type="claude"
        ... )
    """

    def __init__(self) -> None:
        """Initialize the prompt engine."""
        self._offline_processor = OfflineTierProcessor()
        logger.info("PromptEngine initialized")

    # Query-type-specific instructions injected into prompts
    _QUERY_TYPE_INSTRUCTIONS: ClassVar[dict[str, str]] = {
        "technical": (
            "Focus on implementation details, code patterns, and technical accuracy. "
            "Include concrete examples where appropriate."
        ),
        "research": (
            "Prioritize evidence-based analysis with citations and data. "
            "Distinguish established findings from emerging hypotheses."
        ),
        "creative": (
            "Emphasize originality, varied perspectives, and creative expression. "
            "Explore unconventional angles and novel approaches."
        ),
        "analytical": (
            "Use structured comparison, data-driven reasoning, and clear criteria. "
            "Present trade-offs and quantify differences where possible."
        ),
        "operational": (
            "Provide step-by-step procedures with concrete actionable guidance. "
            "Include prerequisites, potential pitfalls, and verification steps."
        ),
        "strategic": (
            "Consider long-term implications, trade-offs, and decision frameworks. "
            "Evaluate risks and present alternatives with their consequences."
        ),
    }

    def _get_prompt_template(self, complexity: str, query_type: str = "unknown") -> str:
        """Get a prompt template based on complexity and query type.

        Args:
            complexity: Query complexity level (simple, medium, complex)
            query_type: Classified query type (technical, research, etc.)

        Returns:
            Prompt template string with placeholders
        """
        now = datetime.now(UTC)
        current_date = now.strftime("%Y-%m-%d")

        # Base template parts
        base_intro = f"Today's date is {current_date} (year {now.year})."

        # Complexity-specific instructions
        complexity_lower = complexity.lower()
        if complexity_lower == "simple":
            complexity_instructions = (
                "This is a straightforward query requiring a direct, accurate response. "
                "Please provide a clear, concise answer."
            )
        elif complexity_lower == "complex":
            complexity_instructions = (
                "This is a complex query requiring deep, systematic analysis. "
                "Please provide comprehensive reasoning with detailed explanations."
            )
        else:  # medium
            complexity_instructions = (
                "This is a moderate query requiring balanced analysis. "
                "Please provide a thorough but focused response."
            )

        # Query-type-specific instructions
        type_instructions = self._QUERY_TYPE_INSTRUCTIONS.get(query_type.lower(), "")

        parts = [base_intro, "", complexity_instructions]
        if type_instructions:
            parts.extend(["", type_instructions])

        return "\n".join(parts)

    def classify_query(self, query: str) -> QueryType:
        """Classify a query into a query type.

        Args:
            query: The query to classify

        Returns:
            Detected QueryType
        """
        return self._offline_processor.classify_query(query)

    async def formulate_search_aware_prompt(
        self,
        query: str,
        complexity: str,
        search_context: SearchContext | None,
        model_type: str = "general",
        query_type: str = "unknown",
        strategy: str | None = None,
        embed_search_context: bool = True,
    ) -> str:
        """Formulate a search-aware enhanced prompt.

        Creates an enhanced prompt that includes:
        - Current year for temporal awareness
        - Complexity-appropriate instructions
        - Model-specific optimization
        - Query-type-specific guidance
        - Model-aware query formatting
        - Search context when available

        Args:
            query: The user's query
            complexity: Query complexity (simple, medium, complex)
            search_context: Optional search context to include
            model_type: Target model type for optimization
            query_type: Classified query type (technical, research, etc.)

        Returns:
            Enhanced prompt string ready for model consumption
        """
        logger.debug(
            "Formulating search-aware prompt: query='%s...', complexity=%s, model=%s, type=%s",
            query[:30],
            complexity,
            model_type,
            query_type,
        )

        # Get base template (includes query-type instructions)
        template = self._get_prompt_template(complexity, query_type)

        # Model-aware query formatting (Defect 3)
        model_lower = model_type.lower()
        if "openai" in model_lower or "gpt" in model_lower:
            query_section = f"## Query\n{query}"
        elif "claude" in model_lower or "anthropic" in model_lower:
            query_section = f"<query>\n{query}\n</query>"
        elif "gemini" in model_lower or "google" in model_lower:
            query_section = f"Query:\n1. {query}"
        else:
            query_section = f"Query ({complexity} complexity): {query}"

        # Build prompt parts
        parts = [
            template,
            "",
            query_section,
        ]

        # Add search context if available (clearly framed as supplementary)
        if embed_search_context and search_context is not None and not search_context.is_empty():
            formatted = search_context.formatted_for_model(model_type)
            if formatted:
                parts.extend(
                    [
                        "",
                        "[Supplementary Context from Web Search — not part of the user's"
                        " original query. Use to inform your response but verify claims.]",
                        formatted,
                    ]
                )
                if search_context.search_timestamp:
                    # Include date from timestamp
                    timestamp_date = search_context.search_timestamp[:10]
                    parts.append(f"(Context retrieved: {timestamp_date})")

        # Apply named strategy techniques for structured enhancement context
        from aipea.strategies import apply_strategy, select_strategy_for_query_type

        try:
            effective_strategy = strategy or select_strategy_for_query_type(QueryType(query_type))
        except ValueError:
            effective_strategy = strategy or "general"
        strategy_output = apply_strategy(query, effective_strategy)
        if strategy_output:
            parts.extend(["", f"[Enhancement Context]\n{strategy_output}"])

        # Add response instructions
        parts.extend(
            [
                "",
                "Please provide your response:",
            ]
        )

        return "\n".join(parts)

    async def create_model_specific_prompt(
        self,
        base_prompt: str,
        model_type: str,
        search_context: SearchContext | None = None,
    ) -> str:
        """Create a model-specific optimized prompt.

        Optimizes the base prompt for the target model's preferences
        and capabilities.

        Args:
            base_prompt: The base prompt to optimize
            model_type: Target model type (gpt-4, claude-4, gemini-pro, etc.)
            search_context: Optional search context to include

        Returns:
            Model-optimized prompt string
        """
        parts = [base_prompt]

        # Add search context if available.
        # Includes prompt-injection-mitigation framing header matching
        # formulate_search_aware_prompt() for defense-in-depth. (#86)
        if search_context is not None and not search_context.is_empty():
            formatted = search_context.formatted_for_model(model_type)
            if formatted:
                parts.extend(
                    [
                        "",
                        "[Supplementary Context from Web Search — not part of the user's"
                        " original query. Use to inform your response but verify claims.]",
                        formatted,
                    ]
                )

        return "\n".join(parts)


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_prompt_engine_instance: PromptEngine | None = None
_prompt_engine_lock = threading.Lock()


def get_prompt_engine() -> PromptEngine:
    """Get the singleton PromptEngine instance.

    Thread-safe via double-checked locking pattern.

    Returns:
        The global PromptEngine instance
    """
    global _prompt_engine_instance
    if _prompt_engine_instance is None:
        with _prompt_engine_lock:
            if _prompt_engine_instance is None:
                _prompt_engine_instance = PromptEngine()
    return _prompt_engine_instance


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "EnhancedQuery",
    "ModelType",
    "OfflineModel",
    "OfflineTierProcessor",
    "OllamaModelInfo",
    "OllamaOfflineClient",
    "ProcessingTier",
    "PromptEngine",
    "QueryType",
    "SearchContext",
    "SearchOrchestrator",
    "SearchResult",
    "SearchStrategy",
    "TierProcessor",
    "create_empty_context",
    "get_ollama_client",
    "get_prompt_engine",
]
