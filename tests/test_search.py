#!/usr/bin/env python3
"""Tests for aipea.search.py - Web Search Providers.

Tests cover:
- SearchStrategy and ModelType enums
- SearchResult and SearchContext dataclasses
- SearchProvider implementations (Exa, Firecrawl, Context7)
- SearchOrchestrator with different strategies
- Convenience functions
- Exception handling in all providers
- Multi-source merge edge cases
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from aipea.search import (
    Context7Provider,
    ExaSearchProvider,
    FirecrawlProvider,
    ModelType,
    SearchContext,
    SearchOrchestrator,
    SearchResult,
    SearchStrategy,
    create_empty_context,
    parse_model_type,
)

# =============================================================================
# ENUM TESTS
# =============================================================================


class TestSearchStrategy:
    """Tests for SearchStrategy enum."""

    def test_strategies_exist(self) -> None:
        """Test that all strategies are defined."""
        assert SearchStrategy.QUICK_FACTS.value == "quick_facts"
        assert SearchStrategy.DEEP_RESEARCH.value == "deep_research"
        assert SearchStrategy.MULTI_SOURCE.value == "multi_source"

    def test_strategy_count(self) -> None:
        """Test expected number of strategies."""
        assert len(SearchStrategy) == 3


class TestModelType:
    """Tests for ModelType enum."""

    def test_model_types_exist(self) -> None:
        """Test that all model types are defined."""
        assert ModelType.OPENAI.value == "openai"
        assert ModelType.ANTHROPIC.value == "anthropic"
        assert ModelType.GEMINI.value == "gemini"
        assert ModelType.GENERIC.value == "generic"

    def test_model_type_count(self) -> None:
        """Test expected number of model types."""
        assert len(ModelType) == 4


# =============================================================================
# SEARCH RESULT TESTS
# =============================================================================


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_creation_with_defaults(self) -> None:
        """Test creating a SearchResult with default score."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet text",
        )
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet text"
        assert result.score == 0.0

    def test_creation_with_score(self) -> None:
        """Test creating a SearchResult with explicit score."""
        result = SearchResult(
            title="Test",
            url="https://test.com",
            snippet="Snippet",
            score=0.85,
        )
        assert result.score == 0.85

    def test_score_clamping_high(self) -> None:
        """Test that scores > 1.0 are clamped."""
        result = SearchResult(
            title="Test",
            url="https://test.com",
            snippet="Snippet",
            score=1.5,
        )
        assert result.score == 1.0

    def test_score_clamping_low(self) -> None:
        """Test that scores < 0.0 are clamped."""
        result = SearchResult(
            title="Test",
            url="https://test.com",
            snippet="Snippet",
            score=-0.5,
        )
        assert result.score == 0.0


# =============================================================================
# SEARCH CONTEXT TESTS
# =============================================================================


class TestSearchContext:
    """Tests for SearchContext dataclass."""

    def test_creation_with_defaults(self) -> None:
        """Test creating a SearchContext with default values."""
        ctx = SearchContext(query="test query")
        assert ctx.query == "test query"
        assert ctx.results == []
        assert ctx.source == "unknown"
        assert ctx.confidence == 0.0
        assert isinstance(ctx.timestamp, datetime)

    def test_creation_with_all_fields(self) -> None:
        """Test creating a SearchContext with all fields."""
        results = [
            SearchResult(title="Result 1", url="https://1.com", snippet="First"),
            SearchResult(title="Result 2", url="https://2.com", snippet="Second"),
        ]
        now = datetime.now(UTC)
        ctx = SearchContext(
            query="full query",
            results=results,
            timestamp=now,
            source="test_source",
            confidence=0.9,
        )
        assert len(ctx.results) == 2
        assert ctx.source == "test_source"
        assert ctx.confidence == 0.9

    def test_confidence_clamping_high(self) -> None:
        """Test that confidence > 1.0 is clamped."""
        ctx = SearchContext(query="test", confidence=1.5)
        assert ctx.confidence == 1.0

    def test_confidence_clamping_low(self) -> None:
        """Test that confidence < 0.0 is clamped."""
        ctx = SearchContext(query="test", confidence=-0.5)
        assert ctx.confidence == 0.0

    def test_is_empty_true(self) -> None:
        """Test is_empty returns True when no results."""
        ctx = SearchContext(query="test", results=[])
        assert ctx.is_empty() is True

    def test_is_empty_false(self) -> None:
        """Test is_empty returns False when results exist."""
        ctx = SearchContext(
            query="test",
            results=[SearchResult(title="T", url="U", snippet="S")],
        )
        assert ctx.is_empty() is False

    def test_formatted_for_model_empty(self) -> None:
        """Test formatting returns empty string when no results."""
        ctx = SearchContext(query="test")
        assert ctx.formatted_for_model("openai") == ""

    def test_formatted_for_model_openai(self) -> None:
        """Test OpenAI/GPT formatting with markdown."""
        ctx = SearchContext(
            query="test",
            results=[SearchResult(title="Title", url="https://url.com", snippet="Snippet")],
            source="exa",
            confidence=0.8,
        )
        formatted = ctx.formatted_for_model("openai")
        assert "# Current Information Context" in formatted
        assert "Source 1: Title" in formatted
        assert "https://url.com" in formatted

    def test_formatted_for_model_gpt(self) -> None:
        """Test GPT models use OpenAI formatting."""
        ctx = SearchContext(
            query="test",
            results=[SearchResult(title="T", url="U", snippet="S")],
        )
        formatted = ctx.formatted_for_model("gpt-4")
        assert "# Current Information Context" in formatted

    def test_formatted_for_model_anthropic(self) -> None:
        """Test Anthropic/Claude formatting with XML tags."""
        ctx = SearchContext(
            query="test",
            results=[SearchResult(title="Title", url="https://url.com", snippet="Snippet")],
            source="exa",
            confidence=0.75,
        )
        formatted = ctx.formatted_for_model("claude")
        assert "<search_context>" in formatted
        assert "</search_context>" in formatted
        assert "<title>Title</title>" in formatted

    def test_formatted_for_model_anthropic_escapes_xml(self) -> None:
        """Ensure XML formatting escapes special characters."""
        ctx = SearchContext(
            query='cats & "dogs"',
            results=[
                SearchResult(
                    title="Title <b>bold</b>",
                    url="https://example.com/?q=1&x=2",
                    snippet='Use <tag> & "quotes"',
                )
            ],
            source="exa & co",
            confidence=0.75,
        )
        formatted = ctx.formatted_for_model("claude")
        assert 'query="cats &amp; &quot;dogs&quot;"' in formatted
        assert 'source="exa &amp; co"' in formatted
        assert "<title>Title &lt;b&gt;bold&lt;/b&gt;</title>" in formatted
        assert "<url>https://example.com/?q=1&amp;x=2</url>" in formatted
        assert '<snippet>Use &lt;tag&gt; &amp; "quotes"</snippet>' in formatted

    def test_formatted_for_model_claude(self) -> None:
        """Test Claude models use Anthropic formatting."""
        ctx = SearchContext(
            query="test",
            results=[SearchResult(title="T", url="U", snippet="S")],
        )
        formatted = ctx.formatted_for_model("anthropic")
        assert "<search_context>" in formatted

    def test_formatted_for_model_generic(self) -> None:
        """Test generic formatting with numbered lists."""
        ctx = SearchContext(
            query="test",
            results=[SearchResult(title="Title", url="https://url.com", snippet="Snippet")],
            source="test",
        )
        formatted = ctx.formatted_for_model("gemini")
        assert "Supporting Information:" in formatted
        assert "1. Title" in formatted

    def test_formatted_for_model_unknown(self) -> None:
        """Test unknown models use generic formatting."""
        ctx = SearchContext(
            query="test",
            results=[SearchResult(title="T", url="U", snippet="S")],
        )
        formatted = ctx.formatted_for_model("unknown-model")
        assert "Supporting Information:" in formatted

    def test_merge_with(self) -> None:
        """Test merging two SearchContexts."""
        ctx1 = SearchContext(
            query="test",
            results=[SearchResult(title="A", url="1", snippet="a")],
            source="exa",
            confidence=0.8,
        )
        ctx2 = SearchContext(
            query="test",
            results=[SearchResult(title="B", url="2", snippet="b")],
            source="firecrawl",
            confidence=0.6,
        )
        merged = ctx1.merge_with(ctx2)
        assert len(merged.results) == 2
        assert merged.confidence == 0.7  # Average
        assert merged.source == "exa+firecrawl"


# =============================================================================
# EXA SEARCH PROVIDER TESTS
# =============================================================================


class TestExaSearchProvider:
    """Tests for ExaSearchProvider."""

    def test_provider_name(self) -> None:
        """Test provider name is 'exa'."""
        provider = ExaSearchProvider()
        assert provider.provider_name == "exa"

    @patch.dict(os.environ, {"EXA_API_KEY": "test-api-key"})
    def test_initialization_enabled(self) -> None:
        """Test initialization with enabled=True when API key is present."""
        provider = ExaSearchProvider(enabled=True)
        assert provider.enabled is True

    def test_initialization_disabled(self) -> None:
        """Test initialization with enabled=False."""
        provider = ExaSearchProvider(enabled=False)
        assert provider.enabled is False

    @pytest.mark.asyncio
    async def test_search_enabled(self) -> None:
        """Test search when enabled returns empty placeholder context."""
        provider = ExaSearchProvider(enabled=True)
        result = await provider.search("test query", num_results=5)
        assert isinstance(result, SearchContext)
        assert result.query == "test query"
        assert result.source == "exa"

    @pytest.mark.asyncio
    async def test_search_disabled(self) -> None:
        """Test search when disabled returns empty context."""
        provider = ExaSearchProvider(enabled=False)
        result = await provider.search("test query")
        assert result.is_empty() is True
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"EXA_API_KEY": "test-api-key"})
    async def test_search_zero_results_request(self) -> None:
        """Test num_results=0 does not raise and confidence is safe."""
        provider = ExaSearchProvider(enabled=True)

        class DummyResponse:
            def __init__(self, payload: dict[str, object]) -> None:
                self._payload = payload

            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return self._payload

        dummy_response = DummyResponse(
            {
                "results": [
                    {
                        "title": "Test Result",
                        "url": "https://example.com",
                        "text": "Snippet",
                        "score": 0.9,
                    }
                ]
            }
        )
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = dummy_response

        with patch("aipea.search.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            result = await provider.search("test query", num_results=0)

        assert len(result.results) == 1
        assert result.confidence == 0.0


# =============================================================================
# FIRECRAWL PROVIDER TESTS
# =============================================================================


class TestFirecrawlProvider:
    """Tests for FirecrawlProvider."""

    def test_provider_name(self) -> None:
        """Test provider name is 'firecrawl'."""
        provider = FirecrawlProvider()
        assert provider.provider_name == "firecrawl"

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-api-key"})
    def test_initialization_enabled(self) -> None:
        """Test initialization with enabled=True when API key is present."""
        provider = FirecrawlProvider(enabled=True)
        assert provider.enabled is True

    def test_initialization_disabled(self) -> None:
        """Test initialization with enabled=False."""
        provider = FirecrawlProvider(enabled=False)
        assert provider.enabled is False

    @pytest.mark.asyncio
    async def test_search_enabled(self) -> None:
        """Test search when enabled returns placeholder context."""
        provider = FirecrawlProvider(enabled=True)
        result = await provider.search("test query", num_results=5)
        assert isinstance(result, SearchContext)
        assert result.source == "firecrawl"

    @pytest.mark.asyncio
    async def test_search_disabled(self) -> None:
        """Test search when disabled returns empty context."""
        provider = FirecrawlProvider(enabled=False)
        result = await provider.search("test query")
        assert result.is_empty() is True

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-api-key"})
    async def test_search_zero_results_request(self) -> None:
        """Test num_results=0 does not raise and confidence is safe."""
        provider = FirecrawlProvider(enabled=True)

        class DummyResponse:
            def __init__(self, payload: dict[str, object]) -> None:
                self._payload = payload

            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return self._payload

        dummy_response = DummyResponse(
            {
                "data": [
                    {
                        "title": "Firecrawl Result",
                        "url": "https://example.com",
                        "markdown": "Snippet",
                    }
                ]
            }
        )
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = dummy_response

        with patch("aipea.search.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            result = await provider.search("test query", num_results=0)

        assert len(result.results) == 1
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_deep_research_enabled(self) -> None:
        """Test deep research when enabled."""
        provider = FirecrawlProvider(enabled=True)
        result = await provider.deep_research("research topic", max_depth=3, time_limit=120)
        assert isinstance(result, SearchContext)
        assert result.source == "firecrawl_deep"

    @pytest.mark.asyncio
    async def test_deep_research_disabled(self) -> None:
        """Test deep research when disabled."""
        provider = FirecrawlProvider(enabled=False)
        result = await provider.deep_research("topic")
        assert result.is_empty() is True
        assert result.source == "firecrawl_deep"

    @pytest.mark.asyncio
    async def test_deep_research_parameter_clamping(self) -> None:
        """Test that deep research clamps parameters."""
        provider = FirecrawlProvider(enabled=True)
        # Should clamp max_depth to [1, 10] and time_limit to [30, 300]
        result = await provider.deep_research("topic", max_depth=20, time_limit=500)
        assert isinstance(result, SearchContext)


# =============================================================================
# CONTEXT7 PROVIDER TESTS
# =============================================================================


class TestContext7Provider:
    """Tests for Context7Provider."""

    def test_provider_name(self) -> None:
        """Test provider name is 'context7'."""
        provider = Context7Provider()
        assert provider.provider_name == "context7"

    def test_initialization_enabled(self) -> None:
        """Test initialization with enabled=True."""
        provider = Context7Provider(enabled=True)
        assert provider.enabled is True

    def test_initialization_disabled(self) -> None:
        """Test initialization with enabled=False."""
        provider = Context7Provider(enabled=False)
        assert provider.enabled is False

    @pytest.mark.asyncio
    async def test_search_enabled(self) -> None:
        """Test search when enabled returns placeholder context."""
        provider = Context7Provider(enabled=True)
        result = await provider.search("React hooks", num_results=5)
        assert isinstance(result, SearchContext)
        assert result.source == "context7"

    @pytest.mark.asyncio
    async def test_search_disabled(self) -> None:
        """Test search when disabled returns empty context."""
        provider = Context7Provider(enabled=False)
        result = await provider.search("test query")
        assert result.is_empty() is True

    @pytest.mark.asyncio
    async def test_get_library_docs_enabled(self) -> None:
        """Test get_library_docs when enabled."""
        provider = Context7Provider(enabled=True)
        result = await provider.get_library_docs("/vercel/next.js", topic="routing")
        assert isinstance(result, SearchContext)
        assert result.query == "/vercel/next.js:routing"

    @pytest.mark.asyncio
    async def test_get_library_docs_disabled(self) -> None:
        """Test get_library_docs when disabled."""
        provider = Context7Provider(enabled=False)
        result = await provider.get_library_docs("/vercel/next.js")
        assert result.is_empty() is True
        assert result.query == "/vercel/next.js"

    @pytest.mark.asyncio
    async def test_get_library_docs_no_topic(self) -> None:
        """Test get_library_docs without topic."""
        provider = Context7Provider(enabled=False)
        result = await provider.get_library_docs("/react/docs")
        assert result.query == "/react/docs"


# =============================================================================
# SEARCH ORCHESTRATOR TESTS
# =============================================================================


class TestSearchOrchestrator:
    """Tests for SearchOrchestrator."""

    @patch.dict(
        os.environ,
        {
            "EXA_API_KEY": "test-key",
            "FIRECRAWL_API_KEY": "test-key",
            "CONTEXT7_API_KEY": "test-key",
        },
    )
    def test_initialization_all_enabled(self) -> None:
        """Test initialization with all providers enabled when API keys are present."""
        orchestrator = SearchOrchestrator(
            exa_enabled=True,
            firecrawl_enabled=True,
            context7_enabled=True,
        )
        status = orchestrator.get_provider_status()
        assert status["exa"] is True
        assert status["firecrawl"] is True
        assert status["context7"] is True

    def test_initialization_all_disabled(self) -> None:
        """Test initialization with all providers disabled."""
        orchestrator = SearchOrchestrator(
            exa_enabled=False,
            firecrawl_enabled=False,
            context7_enabled=False,
        )
        status = orchestrator.get_provider_status()
        assert status["exa"] is False
        assert status["firecrawl"] is False
        assert status["context7"] is False

    @pytest.mark.asyncio
    async def test_search_quick_facts(self) -> None:
        """Test quick_facts strategy uses Exa."""
        orchestrator = SearchOrchestrator()
        result = await orchestrator.search("test query", strategy="quick_facts")
        assert isinstance(result, SearchContext)
        assert result.source == "exa"

    @pytest.mark.asyncio
    async def test_search_deep_research(self) -> None:
        """Test deep_research strategy uses Firecrawl."""
        orchestrator = SearchOrchestrator()
        result = await orchestrator.search("test query", strategy="deep_research")
        assert isinstance(result, SearchContext)
        assert result.source == "firecrawl_deep"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"EXA_API_KEY": "", "FIRECRAWL_API_KEY": ""}, clear=False)
    async def test_search_multi_source(self) -> None:
        """Test multi_source strategy combines providers (disabled providers)."""
        orchestrator = SearchOrchestrator()
        result = await orchestrator.search("test query", strategy="multi_source")
        assert isinstance(result, SearchContext)
        # Both providers disabled (no API keys), so we get the multi_source fallback
        assert result.source == "multi_source"

    @pytest.mark.asyncio
    async def test_search_unknown_strategy(self) -> None:
        """Test unknown strategy falls back to quick_facts."""
        orchestrator = SearchOrchestrator()
        result = await orchestrator.search("test query", strategy="unknown_strategy")
        assert isinstance(result, SearchContext)
        assert result.source == "exa"  # Falls back to quick_facts

    @pytest.mark.asyncio
    async def test_search_strategy_normalization(self) -> None:
        """Test strategy names are normalized."""
        orchestrator = SearchOrchestrator()
        # Test with dashes instead of underscores
        result = await orchestrator.search("test", strategy="quick-facts")
        assert result.source == "exa"
        # Test with spaces
        result2 = await orchestrator.search("test", strategy="deep research")
        assert result2.source == "firecrawl_deep"

    @pytest.mark.asyncio
    async def test_search_technical(self) -> None:
        """Test technical search uses Context7."""
        orchestrator = SearchOrchestrator()
        result = await orchestrator.search_technical("React hooks")
        assert isinstance(result, SearchContext)
        assert result.source == "context7"

    @patch.dict(os.environ, {"EXA_API_KEY": "test-key", "CONTEXT7_API_KEY": "test-key"})
    def test_get_provider_status(self) -> None:
        """Test get_provider_status returns correct dict."""
        orchestrator = SearchOrchestrator(
            exa_enabled=True,
            firecrawl_enabled=False,
            context7_enabled=True,
        )
        status = orchestrator.get_provider_status()
        assert status == {
            "exa": True,
            "firecrawl": False,
            "context7": True,
        }


# =============================================================================
# CONVENIENCE FUNCTION TESTS
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_empty_context_default_source(self) -> None:
        """Test create_empty_context with default source."""
        ctx = create_empty_context("test query")
        assert ctx.query == "test query"
        assert ctx.source == "none"
        assert ctx.is_empty() is True
        assert ctx.confidence == 0.0

    def test_create_empty_context_custom_source(self) -> None:
        """Test create_empty_context with custom source."""
        ctx = create_empty_context("query", source="fallback")
        assert ctx.source == "fallback"

    def test_parse_model_type_openai(self) -> None:
        """Test parse_model_type for OpenAI models."""
        assert parse_model_type("gpt-4") == ModelType.OPENAI
        assert parse_model_type("GPT-3.5-turbo") == ModelType.OPENAI
        assert parse_model_type("openai-model") == ModelType.OPENAI

    def test_parse_model_type_anthropic(self) -> None:
        """Test parse_model_type for Anthropic models."""
        assert parse_model_type("claude-3-opus") == ModelType.ANTHROPIC
        assert parse_model_type("CLAUDE-instant") == ModelType.ANTHROPIC
        assert parse_model_type("anthropic-claude") == ModelType.ANTHROPIC

    def test_parse_model_type_gemini(self) -> None:
        """Test parse_model_type for Gemini models."""
        assert parse_model_type("gemini-pro") == ModelType.GEMINI
        assert parse_model_type("google-gemini") == ModelType.GEMINI
        assert parse_model_type("GEMINI-1.5") == ModelType.GEMINI

    def test_parse_model_type_generic(self) -> None:
        """Test parse_model_type for unknown models."""
        assert parse_model_type("llama-2") == ModelType.GENERIC
        assert parse_model_type("mistral-7b") == ModelType.GENERIC
        assert parse_model_type("unknown") == ModelType.GENERIC


# =============================================================================
# EXCEPTION HANDLING TESTS
# =============================================================================


class TestExceptionHandling:
    """Tests for exception handling in providers."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"EXA_API_KEY": "test-key"})
    async def test_exa_search_exception_handling(self) -> None:
        """Test Exa search handles exceptions gracefully."""
        provider = ExaSearchProvider(enabled=True)
        # Mock logger.debug (inside try block) to raise an exception
        with patch(
            "aipea.search.logger.debug",
            side_effect=Exception("Test exception"),
        ):
            result = await provider.search("test query")
            # Should return empty context from exception handler, not raise
            assert isinstance(result, SearchContext)
            assert result.source == "exa"
            assert result.confidence == 0.0

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-key"})
    async def test_firecrawl_search_exception_handling(self) -> None:
        """Test Firecrawl search handles exceptions gracefully."""
        provider = FirecrawlProvider(enabled=True)
        with patch(
            "aipea.search.logger.debug",
            side_effect=Exception("Test exception"),
        ):
            result = await provider.search("test query")
            assert isinstance(result, SearchContext)
            assert result.source == "firecrawl"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-key"})
    async def test_firecrawl_deep_research_exception_handling(self) -> None:
        """Test Firecrawl deep research handles exceptions gracefully."""
        provider = FirecrawlProvider(enabled=True)
        with patch(
            "aipea.search.logger.debug",
            side_effect=Exception("Test exception"),
        ):
            result = await provider.deep_research("test topic")
            assert isinstance(result, SearchContext)
            assert result.source == "firecrawl_deep"

    @pytest.mark.asyncio
    async def test_context7_search_exception_handling(self) -> None:
        """Test Context7 search handles exceptions gracefully."""
        provider = Context7Provider(enabled=True)
        with patch(
            "aipea.search.logger.debug",
            side_effect=Exception("Test exception"),
        ):
            result = await provider.search("test query")
            assert isinstance(result, SearchContext)
            assert result.source == "context7"

    @pytest.mark.asyncio
    async def test_context7_library_docs_exception_handling(self) -> None:
        """Test Context7 get_library_docs handles exceptions gracefully."""
        provider = Context7Provider(enabled=True)
        with patch(
            "aipea.search.logger.debug",
            side_effect=Exception("Test exception"),
        ):
            result = await provider.get_library_docs("/test/lib", topic="routing")
            assert isinstance(result, SearchContext)
            assert result.source == "context7"

    @pytest.mark.asyncio
    async def test_orchestrator_search_exception_handling(self) -> None:
        """Test SearchOrchestrator handles exceptions gracefully."""
        orchestrator = SearchOrchestrator()
        # Mock the strategy method to raise an exception
        with patch.object(
            orchestrator,
            "_quick_facts_search",
            side_effect=Exception("Orchestrator error"),
        ):
            result = await orchestrator.search("test", strategy="quick_facts")
            assert isinstance(result, SearchContext)
            assert result.source == "orchestrator_error"
            assert result.confidence == 0.0


# =============================================================================
# MULTI-SOURCE EDGE CASE TESTS
# =============================================================================


class TestMultiSourceEdgeCases:
    """Tests for multi-source merge edge cases."""

    @pytest.mark.asyncio
    async def test_multi_source_exa_empty_firecrawl_has_results(self) -> None:
        """Test multi_source when only Firecrawl returns results."""
        orchestrator = SearchOrchestrator()

        # Mock Exa to return empty, Firecrawl to return results
        firecrawl_context = SearchContext(
            query="test",
            results=[SearchResult(title="FC Result", url="https://fc.com", snippet="FC")],
            source="firecrawl",
            confidence=0.8,
        )

        with (
            patch.object(
                orchestrator.exa_provider,
                "search",
                new_callable=AsyncMock,
                return_value=SearchContext(query="test", results=[], source="exa"),
            ),
            patch.object(
                orchestrator.firecrawl_provider,
                "search",
                new_callable=AsyncMock,
                return_value=firecrawl_context,
            ),
        ):
            result = await orchestrator.search("test", strategy="multi_source")
            # Should return firecrawl context when exa is empty
            assert result.source == "firecrawl"
            assert len(result.results) == 1

    @pytest.mark.asyncio
    async def test_multi_source_firecrawl_empty_exa_has_results(self) -> None:
        """Test multi_source when only Exa returns results."""
        orchestrator = SearchOrchestrator()

        # Mock Firecrawl to return empty, Exa to return results
        exa_context = SearchContext(
            query="test",
            results=[SearchResult(title="Exa Result", url="https://exa.com", snippet="EX")],
            source="exa",
            confidence=0.9,
        )

        with (
            patch.object(
                orchestrator.exa_provider,
                "search",
                new_callable=AsyncMock,
                return_value=exa_context,
            ),
            patch.object(
                orchestrator.firecrawl_provider,
                "search",
                new_callable=AsyncMock,
                return_value=SearchContext(query="test", results=[], source="firecrawl"),
            ),
        ):
            result = await orchestrator.search("test", strategy="multi_source")
            # Should return exa context when firecrawl is empty
            assert result.source == "exa"
            assert len(result.results) == 1

    @pytest.mark.asyncio
    async def test_multi_source_both_have_results_merge(self) -> None:
        """Test multi_source merges when both providers return results."""
        orchestrator = SearchOrchestrator()

        exa_context = SearchContext(
            query="test",
            results=[SearchResult(title="Exa", url="https://exa.com", snippet="E")],
            source="exa",
            confidence=0.9,
        )
        firecrawl_context = SearchContext(
            query="test",
            results=[SearchResult(title="FC", url="https://fc.com", snippet="F")],
            source="firecrawl",
            confidence=0.7,
        )

        with (
            patch.object(
                orchestrator.exa_provider,
                "search",
                new_callable=AsyncMock,
                return_value=exa_context,
            ),
            patch.object(
                orchestrator.firecrawl_provider,
                "search",
                new_callable=AsyncMock,
                return_value=firecrawl_context,
            ),
        ):
            result = await orchestrator.search("test", strategy="multi_source")
            # Should merge both contexts
            assert result.source == "exa+firecrawl"
            assert len(result.results) == 2
            assert result.confidence == 0.8  # Average of 0.9 and 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
