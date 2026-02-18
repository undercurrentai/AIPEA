"""AIPEA Prompt Engine - AI Query Enhancement with Tiered Processing.

This module provides the core prompt engineering capabilities,
implementing a three-tier processing architecture for query enhancement:

- Tier 0 (Offline): Pattern-based, template-driven enhancement (<2 seconds)
- Tier 1 (Tactical): LLM-assisted disambiguation with search context (2-5 seconds)
- Tier 2 (Strategic): Multi-agent reasoning chains for complex queries (5-15 seconds)

Key features:
- Tiered query processing with configurable confidence thresholds
- Search context integration from multiple providers
- Model-specific prompt optimization (OpenAI, Claude, Gemini)
- Offline/air-gapped support via OfflineKnowledgeBase
- Current year injection for temporal awareness

Design principles:
- Progressive complexity: Start simple, escalate only when needed
- Model-aware: Different AI models receive optimized prompt structures
- Graceful degradation: Falls back to simpler tiers on failure
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

from aipea._types import QUERY_TYPE_PRIORITY, ProcessingTier, QueryType, SearchStrategy
from aipea.search import (
    ModelType,
    SearchOrchestrator,
    SearchResult,
    _escape_markdown,
    _escape_plaintext,
    create_empty_context,
)
from aipea.search import SearchContext as AIPEASearchContext

logger = logging.getLogger(__name__)

# Availability flag for Claude Code SDK integration
# Set to False as placeholder - actual SDK detection would go here
CLAUDE_CODE_AVAILABLE = False


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
    GEMMA3_270M = "gemma3:270m"  # Google 270M params, 291MB, edge-friendly
    PHI3_MINI = "phi3:mini"  # Microsoft 3.8B params, 2.2GB, good quality

    # Tier 2/3: Future enhancement (require download + more resources)
    GPT_OSS_20B = "gpt-oss-20b"  # OpenAI 20B, ~11GB - NOT YET AVAILABLE
    LLAMA_3_3_70B = "llama-3.3-70b"  # Meta 70B, ~40GB - NOT YET AVAILABLE

    @classmethod
    def tier1_models(cls) -> list[OfflineModel]:
        """Return Tier 1 models (tested and available)."""
        return [cls.GEMMA3_270M, cls.PHI3_MINI]

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
            host: Ollama server URL (default: http://localhost:11434)
        """
        self.host = host or self.DEFAULT_HOST
        self._available_models: list[OllamaModelInfo] | None = None
        logger.debug(f"OllamaOfflineClient initialized with host: {self.host}")

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
                logger.warning(f"Ollama list failed: {result.stderr}")
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
                    logger.debug(f"Skipping unparseable Ollama output line: {line!r} ({parse_err})")

            self._available_models = models
            logger.info(f"Found {len(models)} Ollama models: {[m.name for m in models]}")
            return models

        except subprocess.TimeoutExpired:
            logger.warning("Ollama list timed out")
            self._available_models = []
            return []
        except FileNotFoundError:
            logger.warning("Ollama not found in PATH")
            self._available_models = []
            return []
        except Exception as e:
            # Log full exception info including type for better debugging
            logger.warning(
                "Error listing Ollama models: %s: %s",
                type(e).__name__,
                e,
                exc_info=True,  # Include traceback in debug mode
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

        Prefers phi3:mini (better quality) over gemma3:270m (faster).

        Returns:
            Best available OfflineModel, or None if none available
        """
        if self._available_models is None:
            await self.get_available_models()

        if not self._available_models:
            return None

        available_names = [m.name for m in self._available_models]

        # Prefer phi3:mini for quality, fallback to gemma3:270m for speed
        preference_order = [OfflineModel.PHI3_MINI, OfflineModel.GEMMA3_270M]
        for model in preference_order:
            if model.value in available_names:
                logger.info(f"Selected best available offline model: {model.value}")
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
                logger.error(f"Ollama generation failed: {result.stderr}")
                raise RuntimeError(f"Ollama generation failed: {result.stderr}")

            response = result.stdout.strip()
            logger.debug(f"Ollama generated {len(response)} chars with {model.value}")
            return response

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Ollama generation timed out for {model.value}") from None
        except FileNotFoundError:
            raise RuntimeError("Ollama not found. Install from https://ollama.ai") from None
        except RuntimeError:
            raise
        except Exception as e:
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
class SearchContext:
    """Container for search results with metadata - Legacy compatible version.

    This class provides backward compatibility with the Prompt Engine
    test suite while also supporting integration with the AIPEA search providers.

    Attributes:
        results: List of search result dictionaries
        sources: List of source identifiers
        confidence_score: Overall confidence in result quality (0.0-1.0)
        search_timestamp: ISO timestamp of when search was performed
        query_type: Type of search performed (e.g., "web", "library")
    """

    results: list[dict[str, Any]] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    search_timestamp: str = ""
    query_type: str = "web"

    def __post_init__(self) -> None:
        """Initialize defaults and validate fields."""
        if not self.search_timestamp:
            self.search_timestamp = datetime.now(UTC).isoformat()

        # Coerce to float first (same pattern as SearchResult in search.py)
        try:
            self.confidence_score = float(self.confidence_score)
        except (TypeError, ValueError):
            logger.warning(
                "SearchContext confidence_score has invalid type %s, defaulting to 0.0",
                type(self.confidence_score).__name__,
            )
            self.confidence_score = 0.0

        # Guard against NaN (comparisons with NaN are always False,
        # so the clamping below would leave NaN unchanged)
        if math.isnan(self.confidence_score):
            logger.warning("SearchContext confidence_score is NaN, defaulting to 0.0")
            self.confidence_score = 0.0

        # Clamp confidence score to valid range
        if not 0.0 <= self.confidence_score <= 1.0:
            logger.warning(
                f"SearchContext confidence_score {self.confidence_score} "
                "outside [0, 1] range, clamping"
            )
            self.confidence_score = max(0.0, min(1.0, self.confidence_score))

    def is_empty(self) -> bool:
        """Check if context contains any results.

        Returns:
            True if no results are present
        """
        return len(self.results) == 0

    def formatted_for_model(self, model_type: str) -> str:
        """Format search results for injection into a specific model's prompt.

        Different AI models have different preferences for how context
        is structured:

        - OpenAI/GPT: Markdown with numbered bold headers
        - Claude: Markdown with detailed source sections
        - Gemini/Generic: Simple list format

        Args:
            model_type: Model identifier (e.g., "openai", "claude", "gemini")

        Returns:
            Formatted string ready for prompt injection
        """
        if self.is_empty():
            return ""

        model_lower = model_type.lower()

        if "openai" in model_lower or "gpt" in model_lower:
            return self._format_openai()
        elif "claude" in model_lower or "anthropic" in model_lower:
            return self._format_claude()
        else:
            return self._format_generic()

    def _format_openai(self) -> str:
        """Format results for OpenAI/GPT models.

        Returns:
            Markdown-formatted context with numbered bold headers
        """
        lines = [
            "# Current Information Context",
            "",
            f"*Sources: {', '.join(self.sources) if self.sources else 'various'}*",
            "",
        ]

        for i, result in enumerate(self.results, 1):
            title = _escape_markdown(result.get("title", "Untitled") or "Untitled")
            snippet = _escape_markdown(result.get("snippet", "") or "")
            url = result.get("url", "") or ""

            lines.extend(
                [
                    f"{i}. **{title}**",
                    f"   URL: {url}",
                    f"   {snippet}",
                    "",
                ]
            )

        return "\n".join(lines)

    def _format_claude(self) -> str:
        """Format results for Claude models.

        Returns:
            Markdown with detailed source sections
        """
        lines = [
            "# Current Information Context",
            "",
            f"*Sources: {', '.join(self.sources) if self.sources else 'various'}*",
            "",
        ]

        for i, result in enumerate(self.results, 1):
            title = _escape_markdown(result.get("title", "Untitled") or "Untitled")
            snippet = _escape_markdown(result.get("snippet", "") or "")
            url = result.get("url", "") or ""

            lines.extend(
                [
                    f"## Source {i}: {title}",
                    f"**URL:** {url}",
                    f"**Content:** {snippet}",
                    "",
                ]
            )

        return "\n".join(lines)

    def _format_generic(self) -> str:
        """Format results for Gemini and other models.

        Returns:
            Simple list format
        """
        if self.is_empty():
            return ""

        lines = [
            "Supporting Information:",
            f"(Sources: {', '.join(self.sources) if self.sources else 'various'})",
            "",
        ]

        for i, result in enumerate(self.results, 1):
            title = _escape_plaintext(result.get("title", "Untitled") or "Untitled")
            snippet = _escape_plaintext(result.get("snippet", "") or "")
            url = result.get("url", "") or ""

            lines.extend(
                [
                    f"{i}. {title}",
                    f"   URL: {url}",
                    f"   {snippet}",
                    "",
                ]
            )

        return "\n".join(lines)

    @classmethod
    def from_aipea_context(cls, aipea_ctx: AIPEASearchContext) -> SearchContext:
        """Convert an AIPEA SearchContext to a legacy SearchContext.

        Args:
            aipea_ctx: SearchContext from aipea.search

        Returns:
            Legacy SearchContext for prompt engine compatibility
        """
        results = []
        for sr in aipea_ctx.results:
            results.append(
                {
                    "title": sr.title,
                    "snippet": sr.snippet,
                    "url": sr.url,
                }
            )

        return cls(
            results=results,
            sources=[aipea_ctx.source],
            confidence_score=aipea_ctx.confidence,
            search_timestamp=aipea_ctx.timestamp.isoformat(),
            query_type="web",
        )


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
                f"EnhancedQuery confidence {self.confidence} outside [0, 1] range, clamping"
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

    # Query type patterns for classification
    QUERY_PATTERNS: ClassVar[dict[QueryType, list[str]]] = {
        QueryType.TECHNICAL: [
            r"\b(code|program|api|function|class|method|debug|error|exception)\b",
            r"\b(python|javascript|java|c\+\+|rust|golang|typescript)\b",
            r"\b(database|sql|query|schema|table|index)\b",
        ],
        QueryType.RESEARCH: [
            r"\b(research|study|paper|journal|academic|scientific)\b",
            r"\b(analysis|investigate|examine|explore|hypothesis)\b",
            r"\b(data|statistics|findings|results|evidence)\b",
        ],
        QueryType.CREATIVE: [
            r"\b(create|design|write|compose|brainstorm|ideate)\b",
            r"\b(story|article|content|copy|creative|artistic)\b",
            r"\b(imagine|innovate|original|unique|novel)\b",
        ],
        QueryType.ANALYTICAL: [
            r"\b(analyze|evaluate|compare|assess|measure)\b",
            r"\b(problem|solve|solution|strategy|approach)\b",
            r"\b(data|metrics|kpi|performance|benchmark)\b",
        ],
        QueryType.OPERATIONAL: [
            r"\b(how\s+to|steps|procedure|process|workflow)\b",
            r"\b(install|configure|setup|deploy|implement)\b",
            r"\b(guide|tutorial|instructions|manual)\b",
        ],
        QueryType.STRATEGIC: [
            r"\b(plan|strategy|roadmap|vision|goals)\b",
            r"\b(decision|choose|option|alternative|trade-off)\b",
            r"\b(long-term|future|forecast|predict|scenario)\b",
        ],
    }

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
        # Compile patterns for efficiency
        self._compiled_patterns: dict[QueryType, list[re.Pattern[str]]] = {}
        for qtype, patterns in self.QUERY_PATTERNS.items():
            self._compiled_patterns[qtype] = [re.compile(p, re.IGNORECASE) for p in patterns]

        self._use_ollama = use_ollama
        self._ollama_client: OllamaOfflineClient | None = None
        self._ollama_model: OfflineModel | None = None
        self._ollama_checked = False
        self._ollama_lock = asyncio.Lock()

        logger.debug(
            "OfflineTierProcessor initialized with %d query types, ollama=%s",
            len(self.QUERY_PATTERNS),
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
                    logger.info(f"Offline mode using Ollama model: {self._ollama_model.value}")
                else:
                    logger.info("No Ollama models available, using templates only")
            except Exception as e:
                logger.warning(f"Ollama check failed: {e}, using templates only")
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
            except Exception as e:
                logger.warning(f"Ollama processing failed: {e}, falling back to templates")

        # Fall back to template-based enhancement
        return await self._process_with_templates(query, query_type)

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
    ) -> EnhancedQuery:
        """Process query using template-based enhancement (fallback).

        Args:
            query: The original query
            query_type: Classified query type

        Returns:
            EnhancedQuery with template-based enhancement
        """
        # Get the appropriate template
        template = self.ENHANCEMENT_TEMPLATES.get(
            query_type, self.ENHANCEMENT_TEMPLATES[QueryType.UNKNOWN]
        )

        # Apply the template without format-string injection risks
        enhanced = template.replace("{query}", query)

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
# TIER 1: TACTICAL PROCESSOR
# =============================================================================


class TacticalTierProcessor(TierProcessor):
    """Tier 1 (Tactical) processor - LLM-assisted enhancement with search.

    Uses LLM analysis for query disambiguation and integrates
    search context for improved responses. When an orchestrator is
    provided, makes a single LLM call to improve query understanding;
    otherwise falls back to template-based enhancement.

    Characteristics:
    - LLM-assisted analysis (when orchestrator provided)
    - Search context integration
    - Structured prompt templates (fallback)
    - Latency: 2-5 seconds
    - Confidence range: 0.80-0.90
    """

    def __init__(self, orchestrator: Any | None = None) -> None:
        """Initialize the tactical tier processor.

        Args:
            orchestrator: Optional ConsultationOrchestrator for LLM calls.
                         If None, falls back to template-only enhancement.
        """
        self._offline_processor = OfflineTierProcessor()
        self._orchestrator = orchestrator
        logger.debug("TacticalTierProcessor initialized (llm=%s)", orchestrator is not None)

    @property
    def tier(self) -> ProcessingTier:
        """Return the tier this processor handles.

        Returns:
            ProcessingTier.TACTICAL
        """
        return ProcessingTier.TACTICAL

    async def process(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> EnhancedQuery:
        """Process a query with LLM assistance and search context.

        Args:
            query: The original query to enhance
            context: Optional context (may contain search_context)

        Returns:
            EnhancedQuery with LLM-enhanced content
        """
        logger.debug("TacticalTierProcessor processing query: %s...", query[:50])

        # Get base classification from offline processor
        query_type = self._offline_processor.classify_query(query)

        # Extract search context if provided
        search_context = None
        if context and "search_context" in context:
            search_context = context["search_context"]

        # Build enhanced prompt template
        enhanced_parts = [
            f"Query (requiring tactical analysis): {query}",
            "",
            "Please provide a thorough response with:",
            "- Clear structure and organization",
            "- Evidence-based reasoning",
            "- Practical recommendations",
        ]

        # Add search context if available
        if search_context and isinstance(search_context, SearchContext):
            formatted = search_context.formatted_for_model("general")
            if formatted:
                enhanced_parts.extend(
                    [
                        "",
                        "Relevant Context:",
                        formatted,
                    ]
                )

        enhanced = "\n".join(enhanced_parts)
        llm_assisted = False
        confidence = 0.85

        # Attempt LLM-assisted disambiguation if orchestrator available
        if self._orchestrator is not None and hasattr(self._orchestrator, "consult"):
            try:
                disambiguation_prompt = (
                    f"Disambiguate and clarify the following query. "
                    f"Return a single improved version of the query that is more "
                    f"specific and actionable:\n\n{query}"
                )
                responses = await self._orchestrator.consult(
                    prompt=disambiguation_prompt,
                    models=self._get_available_models(),
                    parallel=False,
                )
                # Use the first successful response
                for resp in responses:
                    if hasattr(resp, "content") and resp.content:
                        enhanced = resp.content
                        llm_assisted = True
                        confidence = 0.88
                        break
            except Exception:
                logger.debug("LLM disambiguation failed, using template fallback")

        return EnhancedQuery(
            original_query=query,
            enhanced_query=enhanced,
            tier_used=ProcessingTier.TACTICAL,
            confidence=confidence,
            query_type=query_type,
            search_context=search_context,
            enhancement_metadata={
                "processor": "tactical",
                "has_search_context": search_context is not None,
                "llm_assisted": llm_assisted,
            },
        )

    def _get_available_models(self) -> list[tuple[Any, str]]:
        """Get list of available model tuples from orchestrator providers."""
        if not self._orchestrator or not hasattr(self._orchestrator, "providers"):
            return []
        models: list[tuple[Any, str]] = []
        for provider_key in self._orchestrator.providers:
            models.append((provider_key, "default"))
        return models[:1]  # Use single model for tactical tier


# =============================================================================
# TIER 2: STRATEGIC PROCESSOR
# =============================================================================


class StrategicTierProcessor(TierProcessor):
    """Tier 2 (Strategic) processor - Multi-agent reasoning chains.

    Uses multi-step reasoning with critique loops for complex
    queries requiring deep analysis. When an orchestrator is provided,
    performs decomposition, parallel sub-question analysis, iterative
    critique, and final synthesis via LLM calls.

    Characteristics:
    - Multi-step reasoning chain (when orchestrator provided)
    - Cross-domain synthesis
    - Critique loop (up to 3 rounds)
    - Latency: 5-15 seconds
    - Confidence range: 0.90-0.98
    """

    def __init__(self, orchestrator: Any | None = None) -> None:
        """Initialize the strategic tier processor.

        Args:
            orchestrator: Optional ConsultationOrchestrator for LLM calls.
                         If None, falls back to template-only enhancement.
        """
        self._tactical_processor = TacticalTierProcessor(orchestrator=orchestrator)
        self._orchestrator = orchestrator
        self._max_critique_rounds = 3
        logger.debug(
            "StrategicTierProcessor initialized (llm=%s, max_critique=%d)",
            orchestrator is not None,
            self._max_critique_rounds,
        )

    @property
    def tier(self) -> ProcessingTier:
        """Return the tier this processor handles.

        Returns:
            ProcessingTier.STRATEGIC
        """
        return ProcessingTier.STRATEGIC

    async def process(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> EnhancedQuery:
        """Process a query with multi-agent reasoning chains.

        Args:
            query: The original query to enhance
            context: Optional context for processing

        Returns:
            EnhancedQuery with strategic multi-step enhancement
        """
        logger.debug("StrategicTierProcessor processing query: %s...", query[:50])

        # Get base result from tactical processor
        tactical_result = await self._tactical_processor.process(query, context)

        # Build strategic template enhancement
        strategic_parts = [
            "Strategic Analysis Required",
            "=" * 40,
            "",
            f"Original Query: {query}",
            "",
            "Multi-Step Reasoning Framework:",
            "1. Problem Decomposition: Break down the query into component parts",
            "2. Cross-Domain Analysis: Consider implications across related domains",
            "3. Synthesis: Integrate findings into a cohesive response",
            "4. Validation: Verify reasoning chain for logical consistency",
            "",
            "Tactical Context:",
            tactical_result.enhanced_query,
            "",
            "Please provide a comprehensive strategic response that:",
            "- Addresses all aspects of the original query",
            "- Considers multiple perspectives and trade-offs",
            "- Provides actionable recommendations",
            "- Acknowledges uncertainties and limitations",
        ]

        enhanced = "\n".join(strategic_parts)
        multi_agent = False
        critique_rounds = 0
        confidence = 0.92

        # Attempt multi-step LLM reasoning if orchestrator available
        if self._orchestrator is not None and hasattr(self._orchestrator, "consult"):
            try:
                models = self._get_available_models()
                if models:
                    enhanced, critique_rounds = await self._run_strategic_reasoning(
                        query, tactical_result.enhanced_query, models
                    )
                    multi_agent = True
                    confidence = min(0.92 + critique_rounds * 0.02, 0.98)
            except Exception:
                logger.debug("Strategic LLM reasoning failed, using template fallback")

        return EnhancedQuery(
            original_query=query,
            enhanced_query=enhanced,
            tier_used=ProcessingTier.STRATEGIC,
            confidence=confidence,
            query_type=tactical_result.query_type,
            search_context=tactical_result.search_context,
            enhancement_metadata={
                "processor": "strategic",
                "critique_rounds": critique_rounds,
                "multi_agent": multi_agent,
                "tactical_confidence": tactical_result.confidence,
            },
        )

    async def _decompose_query(
        self,
        query: str,
        models: list[tuple[Any, str]],
    ) -> list[str]:
        """Decompose a complex query into sub-questions via LLM.

        Args:
            query: The original query to decompose
            models: Available model tuples for LLM calls

        Returns:
            List of sub-questions (falls back to [query] on failure)
        """
        if self._orchestrator is None:
            raise RuntimeError("Orchestrator not initialized")

        decompose_prompt = (
            f"Break the following complex query into 2-4 independent sub-questions "
            f"that together cover all aspects. Return one sub-question per line.\n\n"
            f"Query: {query}"
        )
        decompose_responses = await self._orchestrator.consult(
            prompt=decompose_prompt, models=models, parallel=False
        )
        for resp in decompose_responses:
            if hasattr(resp, "content") and resp.content:
                lines = [ln.strip() for ln in resp.content.strip().split("\n") if ln.strip()]
                if lines:
                    return lines[:4]
        return [query]

    async def _synthesize_analyses(
        self,
        query: str,
        analyses: list[str],
        models: list[tuple[Any, str]],
    ) -> str:
        """Synthesize sub-question analyses into a comprehensive response.

        Args:
            query: The original query
            analyses: List of analysis strings from sub-questions
            models: Available model tuples for LLM calls

        Returns:
            Synthesized response text
        """
        if self._orchestrator is None:
            raise RuntimeError("Orchestrator not initialized")

        synthesis_prompt = (
            f"Synthesize the following analyses into a comprehensive response to: {query}\n\n"
            + "\n\n---\n\n".join(analyses)
        )
        synthesis_responses = await self._orchestrator.consult(
            prompt=synthesis_prompt, models=models, parallel=False
        )
        for resp in synthesis_responses:
            if hasattr(resp, "content") and resp.content:
                return str(resp.content)
        return "\n\n".join(analyses)

    async def _critique_and_refine(
        self,
        query: str,
        synthesis: str,
        models: list[tuple[Any, str]],
    ) -> tuple[str, int]:
        """Run critique loop to refine synthesis.

        Args:
            query: The original query
            synthesis: Current synthesized response
            models: Available model tuples for LLM calls

        Returns:
            Tuple of (refined_text, critique_rounds_completed)
        """
        if self._orchestrator is None:
            raise RuntimeError("Orchestrator not initialized")

        critique_rounds = 0
        for _ in range(self._max_critique_rounds):
            critique_prompt = (
                f"Critically evaluate this response for gaps, errors, or missed perspectives. "
                f"If it is complete and accurate, respond with exactly 'APPROVED'. "
                f"Otherwise describe what needs improvement.\n\n"
                f"Original query: {query}\n\nResponse:\n{synthesis}"
            )
            critique_responses = await self._orchestrator.consult(
                prompt=critique_prompt, models=models, parallel=False
            )
            critique_text = ""
            for resp in critique_responses:
                if hasattr(resp, "content") and resp.content:
                    critique_text = resp.content
                    break

            critique_rounds += 1

            if "APPROVED" in critique_text.upper():
                break

            refine_prompt = (
                f"Improve this response based on the critique:\n\n"
                f"Critique: {critique_text}\n\nCurrent response:\n{synthesis}"
            )
            refine_responses = await self._orchestrator.consult(
                prompt=refine_prompt, models=models, parallel=False
            )
            for resp in refine_responses:
                if hasattr(resp, "content") and resp.content:
                    synthesis = resp.content
                    break

        return synthesis, critique_rounds

    async def _run_strategic_reasoning(
        self,
        query: str,
        tactical_context: str,
        models: list[tuple[Any, str]],
    ) -> tuple[str, int]:
        """Run multi-step strategic reasoning via LLM.

        Pipeline: decompose -> parallel analyze -> synthesize -> critique.

        Returns:
            Tuple of (enhanced_response, critique_rounds_completed)
        """
        if self._orchestrator is None:
            raise RuntimeError("Orchestrator not initialized")
        orchestrator = self._orchestrator

        # Step 1: Decompose query into sub-questions
        sub_questions = await self._decompose_query(query, models)

        # Step 2: Parallel sub-question analysis
        async def analyze_sub(sq: str) -> str:
            responses = await orchestrator.consult(
                prompt=f"Provide a concise analysis:\n\n{sq}\n\nContext:\n{tactical_context}",
                models=models,
                parallel=False,
            )
            for r in responses:
                if hasattr(r, "content") and r.content:
                    return str(r.content)
            return sq

        analyses = await asyncio.gather(*[analyze_sub(sq) for sq in sub_questions])

        # Step 3: Synthesize analyses
        synthesis = await self._synthesize_analyses(query, list(analyses), models)

        # Step 4: Critique and refine
        return await self._critique_and_refine(query, synthesis, models)

    def _get_available_models(self) -> list[tuple[Any, str]]:
        """Get list of available model tuples from orchestrator providers."""
        if not self._orchestrator or not hasattr(self._orchestrator, "providers"):
            return []
        models: list[tuple[Any, str]] = []
        for provider_key in self._orchestrator.providers:
            models.append((provider_key, "default"))
        return models[:2]  # Use up to 2 models for strategic tier


# =============================================================================
# MAIN PROMPT ENGINE
# =============================================================================


class PromptEngine:
    """AIPEA Prompt Engine - Core query enhancement system.

    Orchestrates tiered query processing and provides model-specific
    prompt optimization for different AI providers.

    Features:
    - Three-tier processing (Offline, Tactical, Strategic)
    - Model-specific prompt templates
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
        """Initialize the prompt engine with all tier processors."""
        self._offline_processor = OfflineTierProcessor()
        self._tactical_processor = TacticalTierProcessor()
        self._strategic_processor = StrategicTierProcessor()
        logger.info("PromptEngine initialized with all tier processors")

    def _get_prompt_template(self, complexity: str, model_type: str) -> str:
        """Get a prompt template based on complexity and model type.

        Args:
            complexity: Query complexity level (simple, medium, complex)
            model_type: Target model type (openai, claude, gemini, general)

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

        # Model-specific instructions
        model_lower = model_type.lower()
        if "openai" in model_lower or "gpt" in model_lower:
            model_instructions = (
                "You excel at structured, logical responses with step-by-step reasoning. "
                "Use clear headings and numbered lists where appropriate."
            )
        elif "claude" in model_lower or "anthropic" in model_lower:
            model_instructions = (
                "You excel at detailed, nuanced analysis with sophisticated reasoning. "
                "Provide thoughtful exploration of the topic."
            )
        elif "gemini" in model_lower or "google" in model_lower:
            model_instructions = (
                "You excel at comprehensive, well-structured responses with "
                "practical applications. Balance depth with clarity."
            )
        else:  # general
            model_instructions = (
                "Please provide a well-organized response appropriate to the query complexity."
            )

        return f"{base_intro}\n\n{complexity_instructions}\n\n{model_instructions}"

    def classify_query(self, query: str) -> QueryType:
        """Classify a query into a query type.

        Args:
            query: The query to classify

        Returns:
            Detected QueryType
        """
        return self._offline_processor.classify_query(query)

    async def enhance_query(
        self,
        query: str,
        tier: ProcessingTier,
        context: dict[str, Any] | None = None,
    ) -> EnhancedQuery:
        """Enhance a query using the specified processing tier.

        Args:
            query: The query to enhance
            tier: Processing tier to use
            context: Optional context for processing

        Returns:
            EnhancedQuery with enhancement results
        """
        match tier:
            case ProcessingTier.OFFLINE:
                return await self._offline_processor.process(query, context)
            case ProcessingTier.TACTICAL:
                return await self._tactical_processor.process(query, context)
            case ProcessingTier.STRATEGIC:
                return await self._strategic_processor.process(query, context)
            case _:
                raise ValueError(f"Unsupported processing tier: {tier}")

    async def formulate_search_aware_prompt(
        self,
        query: str,
        complexity: str,
        search_context: SearchContext | None,
        model_type: str = "general",
    ) -> str:
        """Formulate a search-aware enhanced prompt.

        Creates an enhanced prompt that includes:
        - Current year for temporal awareness
        - Complexity-appropriate instructions
        - Model-specific optimization
        - Search context when available

        Args:
            query: The user's query
            complexity: Query complexity (simple, medium, complex)
            search_context: Optional search context to include
            model_type: Target model type for optimization

        Returns:
            Enhanced prompt string ready for model consumption
        """
        logger.debug(
            "Formulating search-aware prompt: query='%s...', complexity=%s, model=%s",
            query[:30],
            complexity,
            model_type,
        )

        # Get base template
        template = self._get_prompt_template(complexity, model_type)

        # Build prompt parts
        parts = [
            template,
            "",
            f"Query ({complexity} complexity): {query}",
        ]

        # Add search context if available
        if search_context is not None and not search_context.is_empty():
            formatted = search_context.formatted_for_model(model_type)
            if formatted:
                parts.extend(
                    [
                        "",
                        "Relevant Search Context:",
                        formatted,
                    ]
                )
                if search_context.search_timestamp:
                    # Include date from timestamp
                    timestamp_date = search_context.search_timestamp[:10]
                    parts.append(f"(Context retrieved: {timestamp_date})")

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
        model_lower = model_type.lower()

        parts = []

        if "gpt" in model_lower or "openai" in model_lower:
            parts.extend(
                [
                    "System: You are an expert assistant. You excel at providing "
                    "structured, logical responses with step-by-step reasoning. "
                    "Use Clear headings and structure for complex answers.",
                    "",
                    base_prompt,
                ]
            )
        elif "claude" in model_lower:
            parts.extend(
                [
                    "You are an expert assistant capable of sophisticated analysis. "
                    "Please provide a response demonstrating nuanced understanding "
                    "and detailed reasoning.",
                    "",
                    base_prompt,
                ]
            )
        elif "gemini" in model_lower:
            parts.extend(
                [
                    "Please provide a comprehensive response that demonstrates "
                    "deep understanding with practical application of concepts.",
                    "",
                    base_prompt,
                ]
            )
        else:
            parts.append(base_prompt)

        # Add search context if available
        if search_context is not None and not search_context.is_empty():
            formatted = search_context.formatted_for_model(model_type)
            if formatted:
                parts.extend(
                    [
                        "",
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
    "CLAUDE_CODE_AVAILABLE",
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
    "StrategicTierProcessor",
    "TacticalTierProcessor",
    "TierProcessor",
    "create_empty_context",
    "get_ollama_client",
    "get_prompt_engine",
]
