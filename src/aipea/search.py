"""AIPEA Search Providers Module - Web search and research for AI query processing.

This module provides search provider implementations for the AI Prompt Engineer
Agent (AIPEA) integration with Agora IV. It enables real-time information retrieval
from multiple sources to augment AI responses with current data.

Key features:
- Multiple search provider backends (Exa, Firecrawl, Context7)
- Model-specific output formatting (OpenAI, Claude, Gemini)
- Search strategy orchestration (quick_facts, deep_research, multi_source)
- Graceful failure handling with fallback to empty results
- Confidence scoring for result quality assessment

Design principles:
- Online mode only: This module requires network connectivity
- Placeholder implementations: Actual MCP integration added later
- Graceful degradation: Failures return empty results, not exceptions
- Type-safe: Full type hints throughout

Note: For offline/air-gapped environments, use OfflineKnowledgeBase instead.
"""

from __future__ import annotations

import asyncio
import html
import logging
import math
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

import httpx

logger = logging.getLogger(__name__)

# API Configuration
EXA_API_URL = os.environ.get("AIPEA_EXA_API_URL", "https://api.exa.ai/search")
FIRECRAWL_API_URL = os.environ.get("AIPEA_FIRECRAWL_API_URL", "https://api.firecrawl.dev/v1/search")


def _resolve_http_timeout() -> float:
    """Resolve HTTP timeout from env var, config files, or default (30.0).

    Checks ``AIPEA_HTTP_TIMEOUT`` environment variable first, then falls
    back to :func:`aipea.config.load_config` for .env / TOML sources.
    """
    env_val = os.environ.get("AIPEA_HTTP_TIMEOUT")
    if env_val is not None:
        try:
            val = float(env_val)
            return val if 0 < val < float("inf") else 30.0
        except (ValueError, TypeError):
            return 30.0
    # Lazy import to avoid circular deps and import-time cost
    from aipea.config import load_config

    cfg = load_config()
    return cfg.http_timeout


def _get_api_key(env_var: str, constructor_value: str | None) -> str:
    """Resolve an API key: constructor arg > env var > config files.

    Args:
        env_var: Environment variable name (e.g. ``"EXA_API_KEY"``).
        constructor_value: Value passed by the caller (``None`` means not set).

    Returns:
        Resolved API key string (empty string if not found anywhere).
    """
    if constructor_value is not None:
        return constructor_value
    env_val = os.environ.get(env_var)
    if env_val is not None:
        return env_val
    # Lazy import to avoid circular deps and import-time cost
    from aipea.config import load_config

    cfg = load_config()
    # Map env var name to config field
    field_map: dict[str, str] = {
        "EXA_API_KEY": "exa_api_key",
        "FIRECRAWL_API_KEY": "firecrawl_api_key",
    }
    field_name = field_map.get(env_var, "")
    return str(getattr(cfg, field_name, "")) if field_name else ""


# Resolved once at import time; config file changes require process restart.
HTTP_TIMEOUT = _resolve_http_timeout()


# =============================================================================
# ESCAPING HELPERS
# =============================================================================


def _escape_markdown(text: str) -> str:
    """Escape markdown-significant characters in user-supplied text.

    Prevents injected titles/snippets from breaking markdown structure
    (e.g., accidental headers, links, or table syntax).
    """
    for ch in ("|", "[", "]", "`", "*", "_", "~"):
        text = text.replace(ch, f"\\{ch}")
    # Escape leading # that would create headers (per line)
    lines = text.split("\n")
    lines = [("\\#" + line[1:] if line.startswith("#") else line) for line in lines]
    return "\n".join(lines)


def _escape_plaintext(text: str) -> str:
    """Escape plaintext-significant patterns in user-supplied text.

    Prevents injected content from creating spurious numbered-list items
    in the generic (plaintext) formatter — checks every line, not just the first.
    """
    lines = text.split("\n")
    escaped = []
    for line in lines:
        is_list_item = (
            line
            and len(line) >= 2
            and line[0].isdigit()
            and line.lstrip("0123456789").startswith(".")
        )
        if is_list_item:
            line = "\\" + line
        escaped.append(line)
    return "\n".join(escaped)


# =============================================================================
# ENUMS
# =============================================================================


class ModelType(Enum):
    """Model types for result formatting.

    Different AI models prefer different formatting styles for
    injected context. This enum maps to formatting strategies.
    """

    OPENAI = "openai"  # GPT models - prefer markdown headers
    ANTHROPIC = "anthropic"  # Claude models - prefer XML tags
    GEMINI = "gemini"  # Gemini models - prefer numbered lists
    GENERIC = "generic"  # Default formatting


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class SearchResult:
    """A single search result from any provider.

    Represents one result item from a web search or content extraction,
    with relevance scoring for ranking.

    Attributes:
        title: Title of the search result or page
        url: URL of the source page
        snippet: Text excerpt or summary from the page
        score: Relevance score (0.0-1.0, higher is more relevant)
    """

    title: str
    url: str
    snippet: str
    score: float = 0.0

    def __post_init__(self) -> None:
        """Validate score is within valid range."""
        try:
            score_val = float(self.score)
        except (TypeError, ValueError):
            logger.warning(
                "SearchResult score has invalid type %s, defaulting to 0.0",
                type(self.score).__name__,
            )
            score_val = 0.0
        self.score = score_val
        if math.isnan(self.score):
            logger.warning("SearchResult score is NaN, defaulting to 0.0")
            self.score = 0.0
        if not 0.0 <= self.score <= 1.0:
            logger.warning("SearchResult score %s outside [0, 1] range, clamping", self.score)
            self.score = max(0.0, min(1.0, self.score))


@dataclass
class SearchContext:
    """Container for search results with metadata.

    Holds the complete context from a search operation, including
    all results, source information, and quality metrics.

    Attributes:
        query: Original search query
        results: List of search results from the provider
        timestamp: When the search was performed
        source: Provider identifier (e.g., "exa", "firecrawl", "context7")
        confidence: Overall confidence in result quality (0.0-1.0)
    """

    query: str
    results: list[SearchResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    source: str = "unknown"
    confidence: float = 0.0

    def __post_init__(self) -> None:
        """Validate confidence is within valid range."""
        # Coerce to float first (same pattern as SearchResult above)
        try:
            self.confidence = float(self.confidence)
        except (TypeError, ValueError):
            logger.warning(
                "SearchContext confidence has invalid type %s, defaulting to 0.0",
                type(self.confidence).__name__,
            )
            self.confidence = 0.0
        if math.isnan(self.confidence):
            logger.warning("SearchContext confidence is NaN, defaulting to 0.0")
            self.confidence = 0.0
        if not 0.0 <= self.confidence <= 1.0:
            logger.warning(
                f"SearchContext confidence {self.confidence} outside [0, 1] range, clamping"
            )
            self.confidence = max(0.0, min(1.0, self.confidence))

    def is_empty(self) -> bool:
        """Check if context contains any results.

        Returns:
            True if no results are present
        """
        return len(self.results) == 0

    # -- Backward-compatibility properties for PromptEngine (legacy field names) --

    @property
    def search_timestamp(self) -> str:
        """ISO timestamp string (legacy compat for PromptEngine)."""
        return self.timestamp.isoformat()

    @property
    def sources(self) -> list[str]:
        """Source list (legacy compat — wraps single ``source`` field)."""
        return [self.source]

    @property
    def confidence_score(self) -> float:
        """Confidence score (legacy compat — alias for ``confidence``)."""
        return self.confidence

    @property
    def query_type(self) -> str:
        """Query type string (legacy compat — always ``'web'``)."""
        return "web"

    def formatted_for_model(self, model_type: str) -> str:
        """Format search results for injection into a specific model's prompt.

        Different AI models have different preferences for how context
        is structured. This method formats results appropriately:

        - OpenAI/GPT: Markdown with headers and sections
        - Anthropic/Claude: XML-style tags for clear delineation
        - Gemini/Generic: Simple numbered list format

        Args:
            model_type: Model identifier (e.g., "openai", "claude", "gemini")
                       or model name containing these strings

        Returns:
            Formatted string ready for prompt injection
        """
        if self.is_empty():
            return ""

        # Use canonical model family detector from _types.py
        from aipea._types import get_model_family as _get_family

        family = _get_family(model_type)
        if family == "openai":
            return self._format_openai()
        elif family == "claude":
            return self._format_anthropic()
        else:
            # Gemini, llama, and generic models use numbered list format
            return self._format_generic()

    def _format_openai(self) -> str:
        """Format results for OpenAI/GPT models using markdown.

        Returns:
            Markdown-formatted context string
        """
        lines = [
            "# Current Information Context",
            "",
            f"*Retrieved: {self.timestamp.strftime('%Y-%m-%d %H:%M UTC')}*",
            f"*Source: {self.source} | Confidence: {self.confidence:.0%}*",
            "",
        ]

        for i, result in enumerate(self.results, 1):
            safe_title = _escape_markdown(result.title or "Untitled")
            safe_snippet = _escape_markdown(result.snippet or "")
            lines.extend(
                [
                    f"## Source {i}: {safe_title}",
                    f"**URL:** {result.url or ''}",
                    "",
                    safe_snippet,
                    "",
                ]
            )

        return "\n".join(lines)

    def _format_anthropic(self) -> str:
        """Format results for Anthropic/Claude models using XML tags.

        Returns:
            XML-style formatted context string
        """
        safe_query = html.escape(self.query, quote=True)
        safe_source = html.escape(self.source, quote=True)
        safe_timestamp = html.escape(self.timestamp.isoformat(), quote=True)
        lines = [
            "<search_context>",
            f'  <metadata query="{safe_query}" source="{safe_source}" '
            f'confidence="{self.confidence:.2f}" '
            f'timestamp="{safe_timestamp}" />',
        ]

        for result in self.results:
            safe_title = html.escape(result.title or "Untitled", quote=False)
            safe_url = html.escape(result.url or "", quote=False)
            safe_snippet = html.escape(result.snippet or "", quote=False)
            lines.extend(
                [
                    "  <source>",
                    f"    <title>{safe_title}</title>",
                    f"    <url>{safe_url}</url>",
                    f"    <snippet>{safe_snippet}</snippet>",
                    f"    <relevance>{result.score:.2f}</relevance>",
                    "  </source>",
                ]
            )

        lines.append("</search_context>")
        return "\n".join(lines)

    def _format_generic(self) -> str:
        """Format results for Gemini and other models using numbered lists.

        Returns:
            Simple numbered list format
        """
        lines = [
            "Supporting Information:",
            f"(Source: {self.source}, Retrieved: {self.timestamp.strftime('%Y-%m-%d %H:%M')})",
            "",
        ]

        for i, result in enumerate(self.results, 1):
            safe_title = _escape_plaintext(result.title or "Untitled")
            safe_snippet = _escape_plaintext(result.snippet or "")
            lines.extend(
                [
                    f"{i}. {safe_title}",
                    f"   URL: {result.url or ''}",
                    f"   {safe_snippet}",
                    "",
                ]
            )

        return "\n".join(lines)

    def merge_with(self, other: SearchContext) -> SearchContext:
        """Merge another SearchContext into a new combined context.

        Combines results from both contexts, averaging confidence scores
        and concatenating source identifiers.

        Args:
            other: Another SearchContext to merge

        Returns:
            New SearchContext with combined results
        """
        combined_results = self.results + other.results
        # Weight confidence by result count for more accurate merged scores
        total_results = len(self.results) + len(other.results)
        if total_results > 0:
            combined_confidence = (
                self.confidence * len(self.results) + other.confidence * len(other.results)
            ) / total_results
        else:
            combined_confidence = (self.confidence + other.confidence) / 2
        combined_source = f"{self.source}+{other.source}"

        return SearchContext(
            query=self.query,
            results=combined_results,
            timestamp=datetime.now(UTC),
            source=combined_source,
            confidence=combined_confidence,
        )


# =============================================================================
# ABSTRACT BASE CLASS
# =============================================================================


class SearchProvider(ABC):
    """Abstract base class for search providers.

    All search providers must implement the search method to return
    a SearchContext with results. Implementations should handle their
    own error cases gracefully, returning empty contexts on failure.
    """

    @abstractmethod
    async def search(self, query: str, num_results: int = 5) -> SearchContext:
        """Perform a search and return results.

        Args:
            query: Search query string
            num_results: Maximum number of results to return

        Returns:
            SearchContext with results (empty if search fails)
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier.

        Returns:
            String identifier for this provider (e.g., "exa", "firecrawl")
        """
        pass


# =============================================================================
# PROVIDER IMPLEMENTATIONS
# =============================================================================


class ExaSearchProvider(SearchProvider):
    """Search provider using Exa AI for web search.

    Exa provides high-quality web search with semantic understanding,
    making it ideal for quick factual queries and current information.

    Attributes:
        enabled: Whether this provider is active
        api_key: Exa API key from environment
    """

    def __init__(self, enabled: bool = True, api_key: str | None = None) -> None:
        """Initialize the Exa search provider.

        Args:
            enabled: Whether to enable this provider (disabled returns empty results)
            api_key: Optional API key override (falls back to EXA_API_KEY env var)
        """
        self.api_key = _get_api_key("EXA_API_KEY", api_key)
        self.enabled = enabled and bool(self.api_key)

        if not self.api_key:
            logger.warning("ExaSearchProvider: EXA_API_KEY not set, provider disabled")
            self.enabled = False
        elif enabled:
            logger.info("ExaSearchProvider initialized (enabled)")
        else:
            logger.info("ExaSearchProvider initialized (disabled)")

    @property
    def provider_name(self) -> str:
        """Return provider identifier.

        Returns:
            "exa" identifier string
        """
        return "exa"

    async def search(self, query: str, num_results: int = 5) -> SearchContext:
        """Search using Exa AI REST API.

        Makes HTTP requests to Exa's search API for web search results.

        Args:
            query: Search query string
            num_results: Maximum number of results to return

        Returns:
            SearchContext with results from Exa
        """
        if not query or not query.strip():
            logger.debug("Empty query provided to ExaSearchProvider.search()")
            return SearchContext(
                query=query or "",
                results=[],
                source=self.provider_name,
                confidence=0.0,
            )

        if not self.enabled:
            logger.debug("ExaSearchProvider disabled, returning empty context")
            return SearchContext(
                query=query,
                results=[],
                source=self.provider_name,
                confidence=0.0,
            )

        # Clamp num_results to at least 1 to avoid division-by-zero in confidence calc
        num_results = max(1, num_results)
        logger.info("Exa search: query_len=%d, num_results=%d", len(query), num_results)

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.post(
                    EXA_API_URL,
                    headers={
                        "x-api-key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": query,
                        "numResults": num_results,
                        "type": "neural",
                        "useAutoprompt": True,
                        "contents": {
                            "text": {"maxCharacters": 2000},
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("results", []):
                # Exa may return `text: null`; fall back to summary safely.
                raw_snippet = item.get("text")
                if raw_snippet is None:
                    raw_snippet = item.get("summary", "")
                snippet = str(raw_snippet)[:1000] if raw_snippet else ""
                score_raw = item.get("score")
                results.append(
                    SearchResult(
                        title=item.get("title") or "Untitled",
                        url=item.get("url") or "",
                        snippet=snippet,
                        score=score_raw if score_raw is not None else 0.5,
                    )
                )

            confidence = (
                min(1.0, len(results) / num_results) if results and num_results > 0 else 0.0
            )
            logger.info("Exa search returned %d results", len(results))

            return SearchContext(
                query=query,
                results=results,
                source=self.provider_name,
                confidence=confidence,
            )

        except httpx.HTTPStatusError as e:
            logger.warning("Exa search HTTP error: %s - %s", e.response.status_code, e)
            return SearchContext(
                query=query,
                results=[],
                source=self.provider_name,
                confidence=0.0,
            )
        except (httpx.HTTPError, KeyError, ValueError) as e:
            logger.warning("Exa search failed: %s", e)
            return SearchContext(
                query=query,
                results=[],
                source=self.provider_name,
                confidence=0.0,
            )


class FirecrawlProvider(SearchProvider):
    """Search provider using Firecrawl for web scraping and research.

    Firecrawl provides advanced web scraping capabilities and deep
    research features for comprehensive information gathering.

    Attributes:
        enabled: Whether this provider is active
        api_key: Firecrawl API key from environment
    """

    def __init__(self, enabled: bool = True, api_key: str | None = None) -> None:
        """Initialize the Firecrawl provider.

        Args:
            enabled: Whether to enable this provider (disabled returns empty results)
            api_key: Optional API key override (falls back to FIRECRAWL_API_KEY env var)
        """
        self.api_key = _get_api_key("FIRECRAWL_API_KEY", api_key)
        self.enabled = enabled and bool(self.api_key)

        if not self.api_key:
            logger.warning("FirecrawlProvider: FIRECRAWL_API_KEY not set, provider disabled")
            self.enabled = False
        elif enabled:
            logger.info("FirecrawlProvider initialized (enabled)")
        else:
            logger.info("FirecrawlProvider initialized (disabled)")

    @property
    def provider_name(self) -> str:
        """Return provider identifier.

        Returns:
            "firecrawl" identifier string
        """
        return "firecrawl"

    async def search(self, query: str, num_results: int = 5) -> SearchContext:
        """Search using Firecrawl REST API.

        Makes HTTP requests to Firecrawl's search API for web search results.

        Args:
            query: Search query string
            num_results: Maximum number of results to return

        Returns:
            SearchContext with results from Firecrawl
        """
        if not query or not query.strip():
            logger.debug("Empty query provided to FirecrawlProvider.search()")
            return SearchContext(
                query=query or "",
                results=[],
                source=self.provider_name,
                confidence=0.0,
            )

        if not self.enabled:
            logger.debug("FirecrawlProvider disabled, returning empty context")
            return SearchContext(
                query=query,
                results=[],
                source=self.provider_name,
                confidence=0.0,
            )

        # Clamp num_results to at least 1 to avoid division-by-zero in confidence calc
        num_results = max(1, num_results)
        logger.info("Firecrawl search: query_len=%d, num_results=%d", len(query), num_results)

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.post(
                    FIRECRAWL_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": query,
                        "limit": num_results,
                        "lang": "en",
                        "scrapeOptions": {
                            "formats": ["markdown"],
                            "onlyMainContent": True,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("data", []):
                markdown_content = item.get("markdown") or ""
                snippet = str(markdown_content)[:1000] if markdown_content else ""
                metadata = item.get("metadata")
                metadata_title = metadata.get("title") if isinstance(metadata, dict) else None
                raw_title = item.get("title") or metadata_title
                title = str(raw_title) if raw_title else "Untitled"
                results.append(
                    SearchResult(
                        title=title,
                        url=item.get("url") or "",
                        snippet=snippet,
                        score=0.7,  # Firecrawl doesn't return relevance scores
                    )
                )

            confidence = (
                min(1.0, len(results) / num_results) if results and num_results > 0 else 0.0
            )
            logger.info("Firecrawl search returned %d results", len(results))

            return SearchContext(
                query=query,
                results=results,
                source=self.provider_name,
                confidence=confidence,
            )

        except httpx.HTTPStatusError as e:
            logger.warning("Firecrawl search HTTP error: %s - %s", e.response.status_code, e)
            return SearchContext(
                query=query,
                results=[],
                source=self.provider_name,
                confidence=0.0,
            )
        except (httpx.HTTPError, KeyError, ValueError) as e:
            logger.warning("Firecrawl search failed: %s", e)
            return SearchContext(
                query=query,
                results=[],
                source=self.provider_name,
                confidence=0.0,
            )

    async def deep_research(
        self,
        query: str,
        max_depth: int = 3,
        time_limit: int = 120,
    ) -> SearchContext:
        """Perform comprehensive deep research on a topic.

        Uses Firecrawl's deep research capabilities for complex queries
        requiring analysis of multiple sources and synthesis of findings.

        Args:
            query: Research question or topic
            max_depth: Maximum depth for recursive research (1-10)
            time_limit: Maximum time in seconds for research (30-300)

        Returns:
            SearchContext with research findings
        """
        if not self.enabled:
            logger.debug("FirecrawlProvider disabled, returning empty deep research context")
            return SearchContext(
                query=query,
                results=[],
                source=f"{self.provider_name}_deep",
                confidence=0.0,
            )

        # Validate parameters
        max_depth = max(1, min(10, max_depth))
        time_limit = max(30, min(300, time_limit))

        logger.info(
            f"Firecrawl deep research: query='{query}', "
            f"max_depth={max_depth}, time_limit={time_limit}s"
        )

        try:
            async with httpx.AsyncClient(timeout=float(time_limit + 30)) as client:
                response = await client.post(
                    "https://api.firecrawl.dev/v1/deep-research",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": query,
                        "maxDepth": max_depth,
                        "timeLimit": time_limit,
                    },
                )
                response.raise_for_status()
                data = response.json()

            # Deep research returns a synthesized analysis
            inner = data.get("data")
            inner = inner if isinstance(inner, dict) else {}
            final_analysis = inner.get("finalAnalysis") or ""
            sources = inner.get("sources") or []

            results = []
            if final_analysis:
                results.append(
                    SearchResult(
                        title="Deep Research Analysis",
                        url="",
                        snippet=final_analysis[:2000],
                        score=0.9,
                    )
                )

            for source in sources[:5]:  # Limit to 5 sources
                results.append(
                    SearchResult(
                        title=source.get("title") or "Source",
                        url=source.get("url") or "",
                        snippet=str(source.get("content") or "")[:500],
                        score=0.7,
                    )
                )

            confidence = 0.85 if results else 0.0
            logger.info("Firecrawl deep research returned %d results", len(results))

            return SearchContext(
                query=query,
                results=results,
                source=f"{self.provider_name}_deep",
                confidence=confidence,
            )

        except httpx.HTTPStatusError as e:
            logger.warning("Firecrawl deep research HTTP error: %s - %s", e.response.status_code, e)
            return SearchContext(
                query=query,
                results=[],
                source=f"{self.provider_name}_deep",
                confidence=0.0,
            )
        except (httpx.HTTPError, KeyError, ValueError) as e:
            logger.warning("Firecrawl deep research failed: %s", e)
            return SearchContext(
                query=query,
                results=[],
                source=f"{self.provider_name}_deep",
                confidence=0.0,
            )


class Context7Provider(SearchProvider):
    """Search provider interface for Context7 library documentation.

    Context7 is a Model Context Protocol (MCP) server that provides up-to-date
    documentation for programming libraries and frameworks. MCP is a tool-calling
    protocol used by Claude Code and similar AI development environments — it is
    NOT callable from Python application code at runtime.

    This provider implements the SearchProvider interface so it can be referenced
    uniformly by the search orchestrator, but it intentionally returns empty results.
    Context7 documentation lookups happen at the agent layer (Claude Code MCP tools)
    before code is written, not at application runtime.

    Attributes:
        enabled: Whether this provider is active (returns empty results either way)
    """

    def __init__(self, enabled: bool = True) -> None:
        """Initialize the Context7 provider.

        Args:
            enabled: Whether to enable this provider (disabled returns empty results)
        """
        self.enabled = enabled
        if enabled:
            logger.info("Context7Provider initialized (enabled)")
        else:
            logger.info("Context7Provider initialized (disabled)")

    @property
    def provider_name(self) -> str:
        """Return provider identifier.

        Returns:
            "context7" identifier string
        """
        return "context7"

    async def search(self, query: str, num_results: int = 5) -> SearchContext:
        """Search library documentation using Context7.

        Returns empty results by design. Context7 operates as an MCP server
        that is invoked by Claude Code at development time, not by Python
        application code at runtime. This method exists to satisfy the
        SearchProvider interface contract.

        Args:
            query: Search query (typically library/framework name + topic)
            num_results: Maximum number of results to return

        Returns:
            SearchContext with empty results (MCP not callable from Python)
        """
        if not self.enabled:
            logger.debug("Context7Provider disabled, returning empty context")
            return SearchContext(
                query=query,
                results=[],
                source=self.provider_name,
                confidence=0.0,
            )

        logger.info("Context7 search: query_len=%d, num_results=%d", len(query), num_results)

        try:
            # Context7 is an MCP tool-calling server used by Claude Code at
            # development time (resolve-library-id → get-library-docs).
            # It cannot be invoked from Python runtime code.

            logger.debug("Context7 returns empty results (MCP not callable at runtime)")
            return SearchContext(
                query=query,
                results=[],
                source=self.provider_name,
                confidence=0.0,
            )

        except (httpx.HTTPError, KeyError, ValueError) as e:
            logger.warning("Context7 search failed: %s", e)
            return SearchContext(
                query=query,
                results=[],
                source=self.provider_name,
                confidence=0.0,
            )

    async def get_library_docs(
        self,
        library_id: str,
        topic: str | None = None,
    ) -> SearchContext:
        """Get documentation for a specific library.

        Returns empty results by design. In Claude Code, library docs are
        retrieved via the MCP tool ``mcp__context7__get-library-docs`` at
        development time, not from Python runtime code.

        Args:
            library_id: Context7-compatible library ID (e.g., "/vercel/next.js")
            topic: Optional topic to focus documentation on

        Returns:
            SearchContext with empty results (MCP not callable from Python)
        """
        if not self.enabled:
            logger.debug("Context7Provider disabled, returning empty library docs")
            return SearchContext(
                query=f"{library_id}:{topic}" if topic else library_id,
                results=[],
                source=self.provider_name,
                confidence=0.0,
            )

        logger.info("Context7 library docs: library_id='%s', topic='%s'", library_id, topic)

        try:
            # Context7 MCP tools are invoked by Claude Code at development
            # time, not callable from Python runtime.

            logger.debug("Context7 library docs returns empty (MCP not callable at runtime)")
            return SearchContext(
                query=f"{library_id}:{topic}" if topic else library_id,
                results=[],
                source=self.provider_name,
                confidence=0.0,
            )

        except (httpx.HTTPError, KeyError, ValueError) as e:
            logger.warning("Context7 library docs failed: %s", e)
            return SearchContext(
                query=f"{library_id}:{topic}" if topic else library_id,
                results=[],
                source=self.provider_name,
                confidence=0.0,
            )


# =============================================================================
# SEARCH ORCHESTRATOR
# =============================================================================


class SearchOrchestrator:
    """Orchestrates multiple search providers with different strategies.

    Combines ExaSearchProvider, FirecrawlProvider, and Context7Provider
    to provide flexible search capabilities based on query requirements.

    Strategies:
    - quick_facts: Fast search using Exa only
    - deep_research: Comprehensive search using Firecrawl deep research
    - multi_source: Combined search using Exa + Firecrawl for broader coverage

    Attributes:
        exa_provider: ExaSearchProvider instance
        firecrawl_provider: FirecrawlProvider instance
        context7_provider: Context7Provider instance
    """

    def __init__(
        self,
        exa_enabled: bool = True,
        firecrawl_enabled: bool = True,
        context7_enabled: bool = True,
        exa_api_key: str | None = None,
        firecrawl_api_key: str | None = None,
    ) -> None:
        """Initialize the search orchestrator with configured providers.

        Args:
            exa_enabled: Whether to enable Exa provider
            firecrawl_enabled: Whether to enable Firecrawl provider
            context7_enabled: Whether to enable Context7 provider
            exa_api_key: Optional Exa API key override
            firecrawl_api_key: Optional Firecrawl API key override
        """
        self.exa_provider = ExaSearchProvider(enabled=exa_enabled, api_key=exa_api_key)
        self.firecrawl_provider = FirecrawlProvider(
            enabled=firecrawl_enabled, api_key=firecrawl_api_key
        )
        self.context7_provider = Context7Provider(enabled=context7_enabled)

        enabled_count = sum(
            [
                self.exa_provider.enabled,
                self.firecrawl_provider.enabled,
                self.context7_provider.enabled,
            ]
        )
        logger.info("SearchOrchestrator initialized with %d/3 providers enabled", enabled_count)

    async def search(
        self,
        query: str,
        strategy: str = "quick_facts",
        num_results: int = 5,
    ) -> SearchContext:
        """Perform a search using the specified strategy.

        Args:
            query: Search query string
            strategy: Search strategy to use:
                - "quick_facts": Fast search using Exa only
                - "deep_research": Comprehensive Firecrawl deep research
                - "multi_source": Combined Exa + Firecrawl results
            num_results: Maximum number of results per provider

        Returns:
            SearchContext with combined or single-source results
        """
        # Normalize strategy
        strategy_lower = strategy.lower().replace("-", "_").replace(" ", "_")

        logger.info("Search orchestration: strategy='%s', query_len=%d", strategy_lower, len(query))

        try:
            if strategy_lower == "quick_facts":
                return await self._quick_facts_search(query, num_results)
            elif strategy_lower == "deep_research":
                return await self._deep_research_search(query, num_results)
            elif strategy_lower == "multi_source":
                return await self._multi_source_search(query, num_results)
            else:
                logger.warning("Unknown strategy '%s', falling back to quick_facts", strategy)
                return await self._quick_facts_search(query, num_results)

        except (httpx.HTTPError, KeyError, ValueError, OSError) as e:
            logger.error("Search orchestration failed: %s", e)
            return SearchContext(
                query=query,
                results=[],
                source="orchestrator_error",
                confidence=0.0,
            )

    async def _quick_facts_search(self, query: str, num_results: int) -> SearchContext:
        """Execute quick facts strategy using Exa.

        Args:
            query: Search query string
            num_results: Maximum number of results

        Returns:
            SearchContext from Exa provider
        """
        logger.debug("Executing quick_facts strategy with Exa")
        return await self.exa_provider.search(query, num_results)

    async def _deep_research_search(self, query: str, num_results: int) -> SearchContext:
        """Execute deep research strategy using Firecrawl.

        Args:
            query: Research query string
            num_results: Maximum number of results (used for depth estimation)

        Returns:
            SearchContext from Firecrawl deep research
        """
        logger.debug("Executing deep_research strategy with Firecrawl")
        # Map num_results to reasonable depth (1-5 results = depth 2, 6+ = depth 3)
        max_depth = 3 if num_results > 5 else 2
        return await self.firecrawl_provider.deep_research(
            query,
            max_depth=max_depth,
            time_limit=120,
        )

    async def _multi_source_search(self, query: str, num_results: int) -> SearchContext:
        """Execute multi-source strategy combining Exa and Firecrawl.

        Args:
            query: Search query string
            num_results: Maximum number of results per provider

        Returns:
            Merged SearchContext from both providers
        """
        logger.debug("Executing multi_source strategy with Exa + Firecrawl")

        # Get results from both providers concurrently
        exa_context, firecrawl_context = await asyncio.gather(
            self.exa_provider.search(query, num_results),
            self.firecrawl_provider.search(query, num_results),
        )

        # Merge results
        if exa_context.is_empty() and firecrawl_context.is_empty():
            return SearchContext(
                query=query,
                results=[],
                source="multi_source",
                confidence=0.0,
            )
        elif exa_context.is_empty():
            return firecrawl_context
        elif firecrawl_context.is_empty():
            return exa_context
        else:
            return exa_context.merge_with(firecrawl_context)

    async def search_technical(self, query: str, num_results: int = 5) -> SearchContext:
        """Search for technical/library documentation using Context7.

        Convenience method for technical queries about programming
        libraries, frameworks, and APIs.

        Args:
            query: Technical query (e.g., "React hooks tutorial")
            num_results: Maximum number of results

        Returns:
            SearchContext from Context7 provider
        """
        logger.info("Technical search via Context7: query_len=%d", len(query))
        return await self.context7_provider.search(query, num_results)

    def get_provider_status(self) -> dict[str, bool]:
        """Get enabled status of all providers.

        Returns:
            Dictionary mapping provider names to enabled status
        """
        return {
            "exa": self.exa_provider.enabled,
            "firecrawl": self.firecrawl_provider.enabled,
            "context7": self.context7_provider.enabled,
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def create_empty_context(query: str, source: str = "none") -> SearchContext:
    """Create an empty SearchContext for fallback scenarios.

    Convenience function for creating a properly initialized empty context
    when search is not available or not needed.

    Args:
        query: Original query string
        source: Source identifier for the empty context

    Returns:
        Empty SearchContext with zero confidence
    """
    return SearchContext(
        query=query,
        results=[],
        source=source,
        confidence=0.0,
    )


def parse_model_type(model_id: str) -> ModelType:
    """Parse a model identifier to determine its type.

    Used for selecting appropriate formatting when injecting
    search context into prompts.

    Args:
        model_id: Model identifier string (e.g., "gpt-4", "claude-3-opus")

    Returns:
        ModelType enum value for formatting selection
    """
    model_lower = model_id.lower()

    if "gpt" in model_lower or "openai" in model_lower:
        return ModelType.OPENAI
    elif "claude" in model_lower or "anthropic" in model_lower:
        return ModelType.ANTHROPIC
    elif "gemini" in model_lower or "google" in model_lower:
        return ModelType.GEMINI
    else:
        return ModelType.GENERIC


# =============================================================================
# EXPORTS
# =============================================================================


__all__ = [
    "Context7Provider",
    "ExaSearchProvider",
    "FirecrawlProvider",
    "ModelType",
    "SearchContext",
    "SearchOrchestrator",
    "SearchProvider",
    "SearchResult",
    "create_empty_context",
    "parse_model_type",
]
