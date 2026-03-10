#!/usr/bin/env python3
"""
Unit Tests for Prompt Engine - Claude Code SDK Integration
Tests the enhanced prompt engineering capabilities with search context
"""

import asyncio
import subprocess
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aipea._types import ProcessingTier, QueryType

# Import the module under test
from aipea.engine import (
    EnhancedQuery,
    OfflineModel,
    OfflineTierProcessor,
    OllamaModelInfo,
    OllamaOfflineClient,
    PromptEngine,
    SearchContext,
    get_ollama_client,
    get_prompt_engine,
)
from aipea.search import SearchResult


class TestSearchContext:
    """Test SearchContext data class functionality"""

    def test_search_context_creation(self):
        """Test creating SearchContext with valid data"""
        results = [
            SearchResult(
                title="Test Article",
                snippet="Test content snippet",
                url="https://example.com",
                score=0.9,
            )
        ]

        context = SearchContext(
            query="test query",
            results=results,
            source="example.com",
            confidence=0.85,
        )

        assert context.results == results
        assert context.sources == ["example.com"]
        assert context.confidence_score == 0.85
        assert context.query_type == "web"

    def test_formatted_for_model_openai(self):
        """Test OpenAI-specific formatting"""
        results = [
            SearchResult(
                title="AI Development 2025",
                snippet="Latest AI developments in machine learning",
                url="https://example.com/ai-2025",
                score=0.9,
            )
        ]

        context = SearchContext(
            query="AI development",
            results=results,
            source="example.com",
            confidence=0.9,
        )

        formatted = context.formatted_for_model("openai")

        assert "# Current Information Context" in formatted
        assert "AI Development 2025" in formatted
        assert "Latest AI developments" in formatted
        assert "example.com" in formatted
        assert "## Source 1:" in formatted  # OpenAI structured format

    def test_formatted_for_model_openai_numbers_each_result(self):
        """Ensure OpenAI formatting numbers results sequentially."""
        results = [
            SearchResult(
                title="Result One",
                snippet="First snippet",
                url="https://example.com/one",
                score=0.9,
            ),
            SearchResult(
                title="Result Two",
                snippet="Second snippet",
                url="https://example.com/two",
                score=0.85,
            ),
        ]

        context = SearchContext(
            query="test query",
            results=results,
            source="example.com",
            confidence=0.9,
        )

        formatted = context.formatted_for_model("openai")

        assert "## Source 1: Result One" in formatted
        assert "## Source 2: Result Two" in formatted

    def test_formatted_for_model_claude(self):
        """Test Claude-specific formatting"""
        results = [
            SearchResult(
                title="Python Best Practices",
                snippet="Modern Python development guidelines",
                url="https://python.org/guide",
                score=0.8,
            )
        ]

        context = SearchContext(
            query="Python best practices",
            results=results,
            source="python.org",
            confidence=0.8,
        )

        formatted = context.formatted_for_model("claude")

        assert "<search_context>" in formatted  # Claude XML tag format
        assert "<title>" in formatted
        assert "<snippet>" in formatted
        assert "python.org" in formatted

    def test_empty_results_formatting(self):
        """Test formatting with no search results"""
        context = SearchContext(
            query="empty test",
            results=[],
            source="",
            confidence=0.0,
        )

        formatted = context.formatted_for_model("general")
        assert formatted == ""


class TestPromptEngine:
    """Test Prompt Engine functionality"""

    @pytest.fixture
    def prompt_engine(self):
        """Create Prompt Engine instance for testing"""
        return PromptEngine()

    @pytest.fixture
    def mock_search_context(self):
        """Create mock search context for testing"""
        return SearchContext(
            query="AI safety research",
            results=[
                SearchResult(
                    title="AI Safety Research 2025",
                    url="https://ai-safety.org/2025-research",
                    snippet="Recent developments in AI alignment and safety protocols",
                    score=0.9,
                ),
                SearchResult(
                    title="Machine Learning Advances",
                    url="https://ml-research.com/advances",
                    snippet="Breakthrough in transformer architecture efficiency",
                    score=0.85,
                ),
            ],
            source="ai-safety.org",
            confidence=0.88,
        )

    @pytest.mark.asyncio
    async def test_basic_enhanced_prompt_without_search(self, prompt_engine):
        """Test basic enhanced prompt generation without search context"""
        query = "Explain machine learning fundamentals"
        complexity = "medium"

        prompt = await prompt_engine.formulate_search_aware_prompt(
            query=query,
            complexity=complexity,
            search_context=None,
            model_type="general",
        )

        assert query in prompt
        assert str(datetime.now(UTC).year) in prompt  # Current year should be included
        assert "medium" in prompt.lower()
        assert len(prompt) > len(query)  # Should be enhanced

    @pytest.mark.asyncio
    async def test_enhanced_prompt_with_search_context(self, prompt_engine, mock_search_context):
        """Test enhanced prompt generation with search context"""
        query = "Latest AI safety research developments"
        complexity = "complex"

        prompt = await prompt_engine.formulate_search_aware_prompt(
            query=query,
            complexity=complexity,
            search_context=mock_search_context,
            model_type="claude",
        )

        assert query in prompt
        assert "AI Safety Research 2025" in prompt
        assert "ai-safety.org" in prompt
        assert "complex" in prompt.lower()
        assert "[Supplementary Context from Web Search" in prompt
        assert mock_search_context.search_timestamp[:10] in prompt  # Date included

    @pytest.mark.asyncio
    async def test_claude_code_sdk_integration(self, prompt_engine):
        """Test Claude Code SDK integration behavior (fallback when unavailable)"""
        query = "Analyze quantum computing implications"
        complexity = "complex"

        prompt = await prompt_engine.formulate_search_aware_prompt(
            query=query, complexity=complexity, search_context=None, model_type="claude"
        )

        # Should fall back to basic enhanced prompt when SDK unavailable
        assert query in prompt
        assert "claude" in prompt.lower() or "detailed" in prompt.lower()
        assert "complex" in prompt.lower()
        assert len(prompt) > 100

    @pytest.mark.asyncio
    @patch("aipea.engine.CLAUDE_CODE_AVAILABLE", False)
    async def test_fallback_when_claude_code_unavailable(self, prompt_engine):
        """Test fallback to basic enhanced prompts when Claude Code SDK unavailable"""
        query = "Design a microservices architecture"
        complexity = "complex"

        prompt = await prompt_engine.formulate_search_aware_prompt(
            query=query,
            complexity=complexity,
            search_context=None,
            model_type="general",
        )

        # Should fall back to basic enhanced prompt
        assert query in prompt
        assert str(datetime.now(UTC).year) in prompt
        assert len(prompt) > 200  # Should be reasonably detailed

    @pytest.mark.asyncio
    async def test_model_specific_optimization_openai(self, prompt_engine, mock_search_context):
        """Test model-specific prompt returns base prompt with search context for OpenAI"""
        base_prompt = "Analyze the current state of artificial intelligence"

        optimized = await prompt_engine.create_model_specific_prompt(
            base_prompt=base_prompt,
            model_type="gpt-4",
            search_context=mock_search_context,
        )

        assert base_prompt in optimized
        assert "AI Safety Research 2025" in optimized  # Search context included

    @pytest.mark.asyncio
    async def test_model_specific_optimization_claude(self, prompt_engine, mock_search_context):
        """Test model-specific prompt returns base prompt with search context for Claude"""
        base_prompt = "Evaluate ethical implications of AI development"

        optimized = await prompt_engine.create_model_specific_prompt(
            base_prompt=base_prompt,
            model_type="claude-4",
            search_context=mock_search_context,
        )

        assert base_prompt in optimized
        assert "<search_context>" in optimized  # Claude XML-formatted search context

    @pytest.mark.asyncio
    async def test_model_specific_optimization_gemini(self, prompt_engine, mock_search_context):
        """Test model-specific prompt returns base prompt with search context for Gemini"""
        base_prompt = "Create a comprehensive technology roadmap"

        optimized = await prompt_engine.create_model_specific_prompt(
            base_prompt=base_prompt,
            model_type="gemini-pro",
            search_context=mock_search_context,
        )

        assert base_prompt in optimized
        assert "Supporting Information:" in optimized  # Gemini-formatted search context

    def test_prompt_template_complexity_simple(self, prompt_engine):
        """Test prompt template for simple complexity"""
        template = prompt_engine._get_prompt_template("simple")

        assert "straightforward query" in template
        assert "direct, accurate response" in template
        assert "clear, concise" in template

    def test_prompt_template_complexity_complex(self, prompt_engine):
        """Test prompt template for complex complexity"""
        template = prompt_engine._get_prompt_template("complex")

        assert "complex query" in template
        assert "deep, systematic analysis" in template
        assert "comprehensive reasoning" in template

    def test_prompt_template_query_type_instructions(self, prompt_engine):
        """Test query-type-specific instructions in templates"""
        technical_template = prompt_engine._get_prompt_template("medium", "technical")
        research_template = prompt_engine._get_prompt_template("medium", "research")

        # Different query types should produce different instructions
        assert technical_template != research_template

        # Technical type includes implementation-focused guidance
        assert "implementation details" in technical_template

        # Research type includes evidence-focused guidance
        assert "evidence-based" in research_template

    def test_current_date_integration(self, prompt_engine):
        """Test that current date is properly integrated"""
        template = prompt_engine._get_prompt_template("medium")

        assert str(datetime.now(UTC).year) in template  # Current year
        assert "Today's date is" in template

    @pytest.mark.asyncio
    async def test_claude_code_error_handling(self, prompt_engine):
        """Test error handling when Claude Code SDK is unavailable"""
        query = "Analyze distributed systems"
        complexity = "complex"

        prompt = await prompt_engine.formulate_search_aware_prompt(
            query=query,
            complexity=complexity,
            search_context=None,
            model_type="general",
        )

        # Should fall back to basic enhanced prompt when SDK unavailable
        assert query in prompt
        assert len(prompt) > 100  # Should still generate a reasonable prompt

    def test_singleton_instance(self):
        """Test that get_prompt_engine returns singleton instance"""
        engine1 = get_prompt_engine()
        engine2 = get_prompt_engine()

        assert engine1 is engine2
        assert isinstance(engine1, PromptEngine)


class TestPromptEngineEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.fixture
    def prompt_engine(self):
        return PromptEngine()

    @pytest.mark.asyncio
    async def test_empty_query_handling(self, prompt_engine):
        """Test handling of empty or minimal queries"""
        empty_query = ""
        minimal_query = "Hi"

        empty_prompt = await prompt_engine.formulate_search_aware_prompt(
            query=empty_query,
            complexity="simple",
            search_context=None,
            model_type="general",
        )

        minimal_prompt = await prompt_engine.formulate_search_aware_prompt(
            query=minimal_query,
            complexity="simple",
            search_context=None,
            model_type="general",
        )

        # Should still generate valid prompts
        assert len(empty_prompt) > 50
        assert len(minimal_prompt) > 50
        assert str(datetime.now(UTC).year) in empty_prompt
        assert minimal_query in minimal_prompt

    @pytest.mark.asyncio
    async def test_malformed_search_context(self, prompt_engine):
        """Test handling of malformed search context"""
        malformed_context = SearchContext(
            query="Test query",
            results=[
                SearchResult(
                    title="",  # Empty title
                    url="invalid-url",  # Invalid URL
                    snippet="",  # Empty snippet
                    score=-1.0,  # Invalid score (will be clamped to 0.0)
                )
            ],
            source="",
            confidence=-1.0,  # Invalid confidence (will be clamped to 0.0)
        )

        prompt = await prompt_engine.formulate_search_aware_prompt(
            query="Test query",
            complexity="medium",
            search_context=malformed_context,
            model_type="general",
        )

        # Should handle gracefully and still generate prompt
        assert "Test query" in prompt
        assert len(prompt) > 100

    @pytest.mark.asyncio
    async def test_very_large_search_context(self, prompt_engine):
        """Test handling of very large search contexts"""
        large_results = []
        for i in range(100):  # Create 100 search results
            large_results.append(
                SearchResult(
                    title=f"Large Result {i}" * 10,  # Long titles
                    snippet=f"Very long snippet content for result {i}. " * 50,  # Long snippets
                    url=f"https://example{i}.com/very/long/url/path",
                    score=0.5,
                )
            )

        large_context = SearchContext(
            query="Test with large context",
            results=large_results,
            source="example0.com",
            confidence=0.5,
        )

        prompt = await prompt_engine.formulate_search_aware_prompt(
            query="Test with large context",
            complexity="complex",
            search_context=large_context,
            model_type="claude",
        )

        # Should handle large context reasonably (may truncate)
        assert "Test with large context" in prompt
        # Should not be unreasonably large
        assert len(prompt) < 250000  # Reasonable upper bound

    @pytest.mark.asyncio
    async def test_template_formatting_allows_braces(self):
        """Template processing should not break on brace characters in queries."""
        processor = OfflineTierProcessor(use_ollama=False)
        query = 'Explain JSON schema {"type": "object"} and {examples}'

        result = await processor.process(query)

        assert query in result.enhanced_query

    @pytest.mark.asyncio
    async def test_unknown_model_type(self, prompt_engine):
        """Test handling of unknown model types"""
        prompt = await prompt_engine.create_model_specific_prompt(
            base_prompt="Test prompt", model_type="unknown-model-v1"
        )

        # Should default to base prompt
        assert "Test prompt" in prompt

    @pytest.mark.asyncio
    async def test_concurrent_prompt_generation(self, prompt_engine):
        """Test concurrent prompt generation"""
        tasks = []

        for i in range(10):
            task = prompt_engine.formulate_search_aware_prompt(
                query=f"Test query {i}",
                complexity="medium",
                search_context=None,
                model_type="general",
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # All should complete successfully
        assert len(results) == 10
        for i, result in enumerate(results):
            assert f"Test query {i}" in result
            assert len(result) > 100


## =============================================================================
## NEW COVERAGE TESTS (appended below existing 24 tests)
## =============================================================================

# ---------------------------------------------------------------------------
# 1. OfflineModel enum helpers (lines 89, 94)
# ---------------------------------------------------------------------------


class TestOfflineModelEnum:
    """Tests for OfflineModel.tier1_models() and tier2_models()."""

    def test_tier1_models_returns_tested_models(self):
        """tier1_models returns Gemma3 1B, Gemma3 270M, and Phi3."""
        tier1 = OfflineModel.tier1_models()
        assert OfflineModel.GEMMA3_1B in tier1
        assert OfflineModel.GEMMA3_270M in tier1
        assert OfflineModel.PHI3_MINI in tier1
        assert len(tier1) == 3

    def test_tier2_models_returns_future_models(self):
        """tier2_models returns GPT-OSS and Llama 3.3."""
        tier2 = OfflineModel.tier2_models()
        assert OfflineModel.GPT_OSS_20B in tier2
        assert OfflineModel.LLAMA_3_3_70B in tier2
        assert len(tier2) == 2


# ---------------------------------------------------------------------------
# 2. OllamaOfflineClient (lines 119-345)
# ---------------------------------------------------------------------------


class TestOllamaOfflineClient:
    """Tests for OllamaOfflineClient constructor and methods."""

    def test_constructor_default_host(self):
        """Default host is localhost:11434."""
        client = OllamaOfflineClient()
        assert client.host == "http://localhost:11434"
        assert client._available_models is None

    def test_constructor_custom_host(self):
        """Custom host is accepted."""
        client = OllamaOfflineClient(host="http://remote:1234")
        assert client.host == "http://remote:1234"

    # -- get_available_models --

    @pytest.mark.asyncio
    async def test_get_available_models_success(self):
        """Parse typical `ollama list` output."""
        mock_result = SimpleNamespace(
            returncode=0,
            stdout=(
                "NAME            ID          SIZE    MODIFIED\n"
                "gemma3:270m     abc123      291 MB  3 days ago\n"
                "phi3:mini       def456      2.2 GB  1 week ago\n"
            ),
            stderr="",
        )
        client = OllamaOfflineClient()
        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            models = await client.get_available_models()

        assert len(models) == 2
        assert models[0].name == "gemma3:270m"
        assert models[0].size_bytes == 291_000_000
        assert models[1].name == "phi3:mini"
        assert models[1].size_bytes == 2_200_000_000

    @pytest.mark.asyncio
    async def test_get_available_models_nonzero_returncode(self):
        """Non-zero returncode returns empty list."""
        mock_result = SimpleNamespace(returncode=1, stdout="", stderr="error")
        client = OllamaOfflineClient()
        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            models = await client.get_available_models()
        assert models == []

    @pytest.mark.asyncio
    async def test_get_available_models_file_not_found(self):
        """FileNotFoundError returns empty list."""
        client = OllamaOfflineClient()
        with patch("asyncio.to_thread", new_callable=AsyncMock, side_effect=FileNotFoundError):
            models = await client.get_available_models()
        assert models == []

    @pytest.mark.asyncio
    async def test_get_available_models_timeout(self):
        """Subprocess timeout returns empty list."""
        client = OllamaOfflineClient()
        with patch(
            "asyncio.to_thread",
            new_callable=AsyncMock,
            side_effect=subprocess.TimeoutExpired(cmd="ollama", timeout=10),
        ):
            models = await client.get_available_models()
        assert models == []

    @pytest.mark.asyncio
    async def test_get_available_models_generic_exception(self):
        """Generic exception returns empty list (line 209-217)."""
        client = OllamaOfflineClient()
        with patch(
            "asyncio.to_thread",
            new_callable=AsyncMock,
            side_effect=OSError("connection refused"),
        ):
            models = await client.get_available_models()
        assert models == []

    @pytest.mark.asyncio
    async def test_get_available_models_kb_size(self):
        """Parse KB size unit."""
        mock_result = SimpleNamespace(
            returncode=0,
            stdout="NAME     ID      SIZE   MODIFIED\ntiny     x       500 KB  now\n",
            stderr="",
        )
        client = OllamaOfflineClient()
        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            models = await client.get_available_models()
        assert len(models) == 1
        assert models[0].size_bytes == 500_000

    @pytest.mark.asyncio
    async def test_get_available_models_bare_bytes(self):
        """Parse bare bytes (no unit suffix)."""
        mock_result = SimpleNamespace(
            returncode=0,
            stdout="NAME     ID      SIZE   MODIFIED\ntiny     x       1024 B  now\n",
            stderr="",
        )
        client = OllamaOfflineClient()
        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            models = await client.get_available_models()
        assert len(models) == 1
        assert models[0].size_bytes == 1024

    @pytest.mark.asyncio
    async def test_get_available_models_unparseable_size(self):
        """Non-numeric size falls back to 0."""
        mock_result = SimpleNamespace(
            returncode=0,
            stdout="NAME     ID      SIZE   MODIFIED\ntiny     x       bad MB  now\n",
            stderr="",
        )
        client = OllamaOfflineClient()
        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            models = await client.get_available_models()
        assert len(models) == 1
        assert models[0].size_bytes == 0

    @pytest.mark.asyncio
    async def test_get_available_models_short_line_skipped(self):
        """Lines with <3 parts are skipped."""
        mock_result = SimpleNamespace(
            returncode=0,
            stdout="NAME   ID   SIZE   MODIFIED\nab\n",
            stderr="",
        )
        client = OllamaOfflineClient()
        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            models = await client.get_available_models()
        assert models == []

    # -- is_model_available --

    @pytest.mark.asyncio
    async def test_is_model_available_true(self):
        """Returns True when model is in available list."""
        client = OllamaOfflineClient()
        client._available_models = [
            OllamaModelInfo(name="gemma3:270m", size_bytes=291_000_000, modified="now"),
        ]
        result = await client.is_model_available(OfflineModel.GEMMA3_270M)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_model_available_false(self):
        """Returns False when model is not in available list."""
        client = OllamaOfflineClient()
        client._available_models = [
            OllamaModelInfo(name="gemma3:270m", size_bytes=291_000_000, modified="now"),
        ]
        result = await client.is_model_available(OfflineModel.PHI3_MINI)
        assert result is False

    @pytest.mark.asyncio
    async def test_is_model_available_empty_list(self):
        """Returns False when available list is empty."""
        client = OllamaOfflineClient()
        client._available_models = []
        result = await client.is_model_available(OfflineModel.GEMMA3_270M)
        assert result is False

    @pytest.mark.asyncio
    async def test_is_model_available_fetches_when_none(self):
        """Fetches models if _available_models is None."""
        client = OllamaOfflineClient()
        assert client._available_models is None
        mock_result = SimpleNamespace(
            returncode=0,
            stdout="NAME   ID   SIZE   MODIFIED\ngemma3:270m  x  291 MB  now\n",
            stderr="",
        )
        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            result = await client.is_model_available(OfflineModel.GEMMA3_270M)
        assert result is True

    # -- get_best_available_model --

    @pytest.mark.asyncio
    async def test_get_best_available_model_prefers_phi3(self):
        """Prefers phi3:mini over gemma3:270m."""
        client = OllamaOfflineClient()
        client._available_models = [
            OllamaModelInfo(name="gemma3:270m", size_bytes=291_000_000, modified=""),
            OllamaModelInfo(name="phi3:mini", size_bytes=2_200_000_000, modified=""),
        ]
        best = await client.get_best_available_model()
        assert best == OfflineModel.PHI3_MINI

    @pytest.mark.asyncio
    async def test_get_best_available_model_falls_back_to_gemma(self):
        """Falls back to gemma3 when phi3 is not available."""
        client = OllamaOfflineClient()
        client._available_models = [
            OllamaModelInfo(name="gemma3:270m", size_bytes=291_000_000, modified=""),
        ]
        best = await client.get_best_available_model()
        assert best == OfflineModel.GEMMA3_270M

    @pytest.mark.asyncio
    async def test_get_best_available_model_none_when_empty(self):
        """Returns None when no models available."""
        client = OllamaOfflineClient()
        client._available_models = []
        best = await client.get_best_available_model()
        assert best is None

    @pytest.mark.asyncio
    async def test_get_best_available_model_none_when_no_tier1(self):
        """Returns None when only non-tier1 models exist."""
        client = OllamaOfflineClient()
        client._available_models = [
            OllamaModelInfo(name="some-other-model", size_bytes=1000, modified=""),
        ]
        best = await client.get_best_available_model()
        assert best is None

    @pytest.mark.asyncio
    async def test_get_best_available_model_fetches_when_none(self):
        """Fetches models if _available_models is None."""
        client = OllamaOfflineClient()
        mock_result = SimpleNamespace(
            returncode=0,
            stdout="NAME   ID   SIZE   MODIFIED\nphi3:mini  x  2.2 GB  now\n",
            stderr="",
        )
        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            best = await client.get_best_available_model()
        assert best == OfflineModel.PHI3_MINI

    # -- generate --

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Successful generation returns stdout."""
        client = OllamaOfflineClient()
        client._available_models = [
            OllamaModelInfo(name="gemma3:270m", size_bytes=291_000_000, modified=""),
        ]
        gen_result = SimpleNamespace(returncode=0, stdout="Hello world", stderr="")
        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=gen_result):
            response = await client.generate("Say hello", OfflineModel.GEMMA3_270M)
        assert response == "Hello world"

    @pytest.mark.asyncio
    async def test_generate_model_not_available(self):
        """Raises RuntimeError when model not available."""
        client = OllamaOfflineClient()
        client._available_models = []
        with pytest.raises(RuntimeError, match="not available"):
            await client.generate("Hello", OfflineModel.GEMMA3_270M)

    @pytest.mark.asyncio
    async def test_generate_prompt_too_long(self):
        """Raises ValueError when prompt exceeds max bytes."""
        client = OllamaOfflineClient()
        client._available_models = [
            OllamaModelInfo(name="gemma3:270m", size_bytes=291_000_000, modified=""),
        ]
        long_prompt = "x" * (128 * 1024 + 1)
        with pytest.raises(ValueError, match="Prompt too long"):
            await client.generate(long_prompt, OfflineModel.GEMMA3_270M)

    @pytest.mark.asyncio
    async def test_generate_nonzero_returncode(self):
        """Raises RuntimeError on non-zero returncode."""
        client = OllamaOfflineClient()
        client._available_models = [
            OllamaModelInfo(name="gemma3:270m", size_bytes=291_000_000, modified=""),
        ]
        gen_result = SimpleNamespace(returncode=1, stdout="", stderr="model error")
        with (
            patch("asyncio.to_thread", new_callable=AsyncMock, return_value=gen_result),
            pytest.raises(RuntimeError, match="generation failed"),
        ):
            await client.generate("Hello", OfflineModel.GEMMA3_270M)

    @pytest.mark.asyncio
    async def test_generate_timeout(self):
        """Raises RuntimeError on timeout."""
        client = OllamaOfflineClient()
        client._available_models = [
            OllamaModelInfo(name="gemma3:270m", size_bytes=291_000_000, modified=""),
        ]
        with (
            patch(
                "asyncio.to_thread",
                new_callable=AsyncMock,
                side_effect=subprocess.TimeoutExpired(cmd="ollama", timeout=60),
            ),
            pytest.raises(RuntimeError, match="timed out"),
        ):
            await client.generate("Hello", OfflineModel.GEMMA3_270M)

    @pytest.mark.asyncio
    async def test_generate_file_not_found(self):
        """Raises RuntimeError when ollama binary not found."""
        client = OllamaOfflineClient()
        client._available_models = [
            OllamaModelInfo(name="gemma3:270m", size_bytes=291_000_000, modified=""),
        ]
        with (
            patch(
                "asyncio.to_thread",
                new_callable=AsyncMock,
                side_effect=FileNotFoundError,
            ),
            pytest.raises(RuntimeError, match="not found"),
        ):
            await client.generate("Hello", OfflineModel.GEMMA3_270M)

    @pytest.mark.asyncio
    async def test_generate_generic_exception(self):
        """Raises RuntimeError on generic exception (line 336-337)."""
        client = OllamaOfflineClient()
        client._available_models = [
            OllamaModelInfo(name="gemma3:270m", size_bytes=291_000_000, modified=""),
        ]
        with (
            patch(
                "asyncio.to_thread",
                new_callable=AsyncMock,
                side_effect=OSError("disk full"),
            ),
            pytest.raises(RuntimeError, match="generation error"),
        ):
            await client.generate("Hello", OfflineModel.GEMMA3_270M)


# ---------------------------------------------------------------------------
# 3. get_ollama_client() singleton (lines 346-365)
# ---------------------------------------------------------------------------


class TestGetOllamaClient:
    """Tests for the get_ollama_client singleton."""

    def test_get_ollama_client_returns_instance(self):
        """Returns an OllamaOfflineClient instance."""
        # Reset singleton for clean test
        import aipea.engine as mod

        original = mod._ollama_client
        try:
            mod._ollama_client = None
            client = get_ollama_client()
            assert isinstance(client, OllamaOfflineClient)
        finally:
            mod._ollama_client = original

    def test_get_ollama_client_is_singleton(self):
        """Returns the same instance on repeated calls."""
        import aipea.engine as mod

        original = mod._ollama_client
        try:
            mod._ollama_client = None
            c1 = get_ollama_client()
            c2 = get_ollama_client()
            assert c1 is c2
        finally:
            mod._ollama_client = original


# ---------------------------------------------------------------------------
# 4. SearchContext.__post_init__ confidence clamping (line 388)
# ---------------------------------------------------------------------------


class TestSearchContextPostInit:
    """Tests for SearchContext __post_init__ auto-timestamp and clamping."""

    def test_auto_timestamp_exists(self):
        """Default timestamp is always present (datetime default)."""
        ctx = SearchContext(query="t", results=[], confidence=0.5)
        assert ctx.timestamp is not None
        assert ctx.search_timestamp != ""
        # Should be a valid ISO format string
        assert "T" in ctx.search_timestamp

    def test_none_confidence_coerced(self):
        """Non-numeric confidence is coerced to 0.0 (bug #39)."""
        ctx = SearchContext(query="t", confidence=None)  # type: ignore[arg-type]
        assert ctx.confidence == 0.0
        assert ctx.confidence_score == 0.0

    def test_string_confidence_coerced(self):
        """String confidence is coerced via float() (bug #39)."""
        ctx = SearchContext(query="t", confidence="0.7")  # type: ignore[arg-type]
        assert ctx.confidence == 0.7
        assert ctx.confidence_score == 0.7


# ---------------------------------------------------------------------------
# 5. SearchContext._format_generic() with results (line 501)
# ---------------------------------------------------------------------------


class TestSearchContextFormatGeneric:
    """Tests for _format_generic with non-empty results."""

    def test_format_generic_with_results(self):
        """Generic format includes 'Supporting Information' header."""
        ctx = SearchContext(
            query="test",
            results=[
                SearchResult(title="Result A", url="https://a.com", snippet="Content A", score=0.7),
            ],
            source="a.com",
            confidence=0.7,
        )
        formatted = ctx.formatted_for_model("gemini")
        assert "Supporting Information:" in formatted
        assert "1. Result A" in formatted
        assert "https://a.com" in formatted


# ---------------------------------------------------------------------------
# 7. EnhancedQuery.__post_init__ confidence clamping (lines 562-610)
# ---------------------------------------------------------------------------


class TestEnhancedQueryPostInit:
    """Tests for EnhancedQuery confidence clamping."""

    def test_confidence_clamped_above_one(self):
        """Confidence > 1.0 is clamped to 1.0."""
        eq = EnhancedQuery(
            original_query="q",
            enhanced_query="eq",
            tier_used=ProcessingTier.OFFLINE,
            confidence=1.5,
            query_type=QueryType.UNKNOWN,
        )
        assert eq.confidence == 1.0

    def test_confidence_clamped_below_zero(self):
        """Confidence < 0.0 is clamped to 0.0."""
        eq = EnhancedQuery(
            original_query="q",
            enhanced_query="eq",
            tier_used=ProcessingTier.OFFLINE,
            confidence=-0.5,
            query_type=QueryType.UNKNOWN,
        )
        assert eq.confidence == 0.0

    def test_confidence_within_range_unchanged(self):
        """Confidence within [0,1] is kept as-is."""
        eq = EnhancedQuery(
            original_query="q",
            enhanced_query="eq",
            tier_used=ProcessingTier.OFFLINE,
            confidence=0.75,
            query_type=QueryType.UNKNOWN,
        )
        assert eq.confidence == 0.75

    def test_none_confidence_coerced(self):
        """Non-numeric confidence is coerced to 0.0 (bug #39)."""
        eq = EnhancedQuery(
            original_query="q",
            enhanced_query="eq",
            tier_used=ProcessingTier.OFFLINE,
            confidence=None,  # type: ignore[arg-type]
            query_type=QueryType.UNKNOWN,
        )
        assert eq.confidence == 0.0

    def test_string_confidence_coerced(self):
        """String confidence is coerced via float() (bug #39)."""
        eq = EnhancedQuery(
            original_query="q",
            enhanced_query="eq",
            tier_used=ProcessingTier.OFFLINE,
            confidence="0.6",  # type: ignore[arg-type]
            query_type=QueryType.UNKNOWN,
        )
        assert eq.confidence == 0.6

    def test_search_context_invalid_type_set_to_none(self):
        """search_context with wrong type is set to None (#20)."""
        eq = EnhancedQuery(
            original_query="q",
            enhanced_query="eq",
            tier_used=ProcessingTier.OFFLINE,
            confidence=0.8,
            query_type=QueryType.UNKNOWN,
            search_context="not a SearchContext",  # type: ignore[arg-type]
        )
        assert eq.search_context is None

    def test_search_context_valid_type_preserved(self):
        """search_context with correct type is preserved."""
        ctx = SearchContext(
            query="test",
            results=[SearchResult(title="t", url="", snippet="", score=0.5)],
            source="s",
        )
        eq = EnhancedQuery(
            original_query="q",
            enhanced_query="eq",
            tier_used=ProcessingTier.OFFLINE,
            confidence=0.8,
            query_type=QueryType.UNKNOWN,
            search_context=ctx,
        )
        assert eq.search_context is ctx

    def test_search_context_none_preserved(self):
        """search_context=None is preserved as-is."""
        eq = EnhancedQuery(
            original_query="q",
            enhanced_query="eq",
            tier_used=ProcessingTier.OFFLINE,
            confidence=0.8,
            query_type=QueryType.UNKNOWN,
            search_context=None,
        )
        assert eq.search_context is None


# ---------------------------------------------------------------------------
# 8. TierProcessor abstract (lines 615, 625) — tested via subclasses below
# 9. OfflineTierProcessor.tier property (line 652)
# ---------------------------------------------------------------------------


class TestOfflineTierProcessorProperties:
    """Tests for OfflineTierProcessor.tier and Ollama integration."""

    def test_tier_returns_offline(self):
        """tier property returns ProcessingTier.OFFLINE (line 767)."""
        proc = OfflineTierProcessor(use_ollama=False)
        assert proc.tier == ProcessingTier.OFFLINE

    # -- _check_ollama_availability (line 815) --

    @pytest.mark.asyncio
    async def test_check_ollama_availability_already_checked(self):
        """Short-circuits when already checked (line 798)."""
        proc = OfflineTierProcessor(use_ollama=True)
        proc._ollama_checked = True
        proc._ollama_client = None
        # Should do nothing
        await proc._check_ollama_availability()
        assert proc._ollama_client is None  # unchanged

    @pytest.mark.asyncio
    async def test_check_ollama_availability_disabled(self):
        """Does nothing when use_ollama is False (line 802-804)."""
        proc = OfflineTierProcessor(use_ollama=False)
        await proc._check_ollama_availability()
        assert proc._ollama_checked is True
        assert proc._ollama_client is None

    @pytest.mark.asyncio
    async def test_check_ollama_availability_model_found(self):
        """Sets client and model when Ollama has models (lines 806-811)."""
        proc = OfflineTierProcessor(use_ollama=True)

        mock_client = MagicMock(spec=OllamaOfflineClient)
        mock_client.get_best_available_model = AsyncMock(return_value=OfflineModel.GEMMA3_270M)

        with patch("aipea.engine.get_ollama_client", return_value=mock_client):
            await proc._check_ollama_availability()

        assert proc._ollama_checked is True
        assert proc._ollama_client is mock_client
        assert proc._ollama_model == OfflineModel.GEMMA3_270M

    @pytest.mark.asyncio
    async def test_check_ollama_availability_no_models(self):
        """Sets client but model stays None when no models (line 812-813)."""
        proc = OfflineTierProcessor(use_ollama=True)

        mock_client = MagicMock(spec=OllamaOfflineClient)
        mock_client.get_best_available_model = AsyncMock(return_value=None)

        with patch("aipea.engine.get_ollama_client", return_value=mock_client):
            await proc._check_ollama_availability()

        assert proc._ollama_client is mock_client
        assert proc._ollama_model is None

    @pytest.mark.asyncio
    async def test_check_ollama_availability_exception(self):
        """On exception, client and model stay None (lines 814-817)."""
        proc = OfflineTierProcessor(use_ollama=True)

        with patch("aipea.engine.get_ollama_client", side_effect=RuntimeError("fail")):
            await proc._check_ollama_availability()

        assert proc._ollama_checked is True
        assert proc._ollama_client is None
        assert proc._ollama_model is None

    # -- process with Ollama path (lines 849-852) --

    @pytest.mark.asyncio
    async def test_process_delegates_to_ollama_when_available(self):
        """When Ollama model is set, process delegates to _process_with_ollama (lines 849-852)."""
        proc = OfflineTierProcessor(use_ollama=True)
        proc._ollama_checked = True

        mock_client = MagicMock(spec=OllamaOfflineClient)
        mock_client.generate = AsyncMock(return_value="LLM response here")
        proc._ollama_client = mock_client
        proc._ollama_model = OfflineModel.GEMMA3_270M

        result = await proc.process("Explain python code patterns")
        assert result.enhancement_metadata.get("llm_enhanced") is True
        assert result.enhancement_metadata.get("ollama_model") == "gemma3:270m"
        assert result.confidence == 0.82

    @pytest.mark.asyncio
    async def test_process_falls_back_on_ollama_failure(self):
        """Ollama failure falls back to templates (line 852)."""
        proc = OfflineTierProcessor(use_ollama=True)
        proc._ollama_checked = True

        mock_client = MagicMock(spec=OllamaOfflineClient)
        mock_client.generate = AsyncMock(side_effect=RuntimeError("ollama died"))
        proc._ollama_client = mock_client
        proc._ollama_model = OfflineModel.GEMMA3_270M

        result = await proc.process("Explain python code")
        # Should fall back to templates
        assert result.enhancement_metadata.get("llm_enhanced") is False
        assert "Technical Query" in result.enhanced_query or "Query:" in result.enhanced_query

    @pytest.mark.asyncio
    async def test_process_skips_ollama_when_use_llm_false(self):
        """When context says use_llm=False, skip Ollama even if available."""
        proc = OfflineTierProcessor(use_ollama=True)
        proc._ollama_checked = True
        proc._ollama_client = MagicMock(spec=OllamaOfflineClient)
        proc._ollama_model = OfflineModel.GEMMA3_270M

        result = await proc.process("Explain code", context={"use_llm": False})
        assert result.enhancement_metadata.get("llm_enhanced") is False


# ---------------------------------------------------------------------------
# 12. OfflineTierProcessor._process_with_ollama (lines 871-904)
# ---------------------------------------------------------------------------


class TestProcessWithOllama:
    """Tests for OfflineTierProcessor._process_with_ollama."""

    @pytest.mark.asyncio
    async def test_process_with_ollama_no_client_raises(self):
        """Raises RuntimeError when client is None (line 871-872)."""
        proc = OfflineTierProcessor(use_ollama=False)
        proc._ollama_client = None
        proc._ollama_model = OfflineModel.GEMMA3_270M
        with pytest.raises(RuntimeError, match="not initialized"):
            await proc._process_with_ollama("test", QueryType.TECHNICAL)

    @pytest.mark.asyncio
    async def test_process_with_ollama_no_model_raises(self):
        """Raises RuntimeError when model is None (line 873-874)."""
        proc = OfflineTierProcessor(use_ollama=False)
        proc._ollama_client = MagicMock(spec=OllamaOfflineClient)
        proc._ollama_model = None
        with pytest.raises(RuntimeError, match="not configured"):
            await proc._process_with_ollama("test", QueryType.TECHNICAL)

    @pytest.mark.asyncio
    async def test_process_with_ollama_all_query_types(self):
        """Each QueryType maps to a system prompt (lines 877-897)."""
        proc = OfflineTierProcessor(use_ollama=True)
        mock_client = MagicMock(spec=OllamaOfflineClient)
        mock_client.generate = AsyncMock(return_value="Response text")
        proc._ollama_client = mock_client
        proc._ollama_model = OfflineModel.PHI3_MINI

        for qtype in QueryType:
            result = await proc._process_with_ollama("test query", qtype)
            assert result.tier_used == ProcessingTier.OFFLINE
            assert result.confidence == 0.82
            assert result.query_type == qtype
            assert result.enhancement_metadata["ollama_model"] == "phi3:mini"
            assert result.enhancement_metadata["llm_enhanced"] is True


# ---------------------------------------------------------------------------
# 21. PromptEngine.classify_query (line 1509)
# ---------------------------------------------------------------------------


class TestPromptEngineClassifyQuery:
    """Tests for PromptEngine.classify_query."""

    def test_classify_query_technical(self):
        """classify_query delegates to offline processor."""
        engine = PromptEngine()
        qtype = engine.classify_query("How do I debug a python function?")
        assert qtype == QueryType.TECHNICAL

    def test_classify_query_research(self):
        """Classifies research queries."""
        engine = PromptEngine()
        qtype = engine.classify_query("What does the latest research study say?")
        assert qtype == QueryType.RESEARCH

    def test_classify_query_unknown(self):
        """Returns UNKNOWN for unclassifiable queries."""
        engine = PromptEngine()
        qtype = engine.classify_query("Hello there")
        assert qtype == QueryType.UNKNOWN


# ---------------------------------------------------------------------------
# Mock-based tests for Ollama code paths (covers skipped integration tests)
# These tests exercise the same code paths as the 15 skipped tests in
# test_ollama.py without requiring a real Ollama installation.
# ---------------------------------------------------------------------------


class TestOllamaClientMocked:
    """Mock-based tests for OllamaOfflineClient methods.

    Covers the same code paths as the skipped integration tests in
    TestOllamaClientIntegration, TestOllamaGeneration, and TestOllamaPerformance.
    """

    @pytest.mark.asyncio
    async def test_is_model_available_found_via_fetch(self):
        """is_model_available returns True after fetching models (mock)."""
        client = OllamaOfflineClient()
        mock_result = SimpleNamespace(
            returncode=0,
            stdout=(
                "NAME   ID   SIZE   MODIFIED\n"
                "gemma3:270m  x  291 MB  now\n"
                "phi3:mini  y  2.2 GB  now\n"
            ),
            stderr="",
        )
        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            assert await client.is_model_available(OfflineModel.GEMMA3_270M) is True
            assert await client.is_model_available(OfflineModel.PHI3_MINI) is True

    @pytest.mark.asyncio
    async def test_is_model_available_not_found_via_fetch(self):
        """is_model_available returns False for model not in list (mock)."""
        client = OllamaOfflineClient()
        mock_result = SimpleNamespace(
            returncode=0,
            stdout="NAME   ID   SIZE   MODIFIED\ngemma3:270m  x  291 MB  now\n",
            stderr="",
        )
        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            assert await client.is_model_available(OfflineModel.GPT_OSS_20B) is False

    @pytest.mark.asyncio
    async def test_get_best_available_model_prefers_phi3_mock(self):
        """get_best_available_model returns phi3 when both available (mock)."""
        client = OllamaOfflineClient()
        mock_result = SimpleNamespace(
            returncode=0,
            stdout=(
                "NAME   ID   SIZE   MODIFIED\n"
                "gemma3:270m  x  291 MB  now\n"
                "phi3:mini  y  2.2 GB  now\n"
            ),
            stderr="",
        )
        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            best = await client.get_best_available_model()
        assert best == OfflineModel.PHI3_MINI

    @pytest.mark.asyncio
    async def test_get_best_available_model_fallback_gemma_mock(self):
        """get_best_available_model falls back to gemma when only gemma available (mock)."""
        client = OllamaOfflineClient()
        mock_result = SimpleNamespace(
            returncode=0,
            stdout="NAME   ID   SIZE   MODIFIED\ngemma3:270m  x  291 MB  now\n",
            stderr="",
        )
        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            best = await client.get_best_available_model()
        assert best == OfflineModel.GEMMA3_270M

    @pytest.mark.asyncio
    async def test_get_best_available_model_none_mock(self):
        """get_best_available_model returns None when no tier1 models (mock)."""
        client = OllamaOfflineClient()
        mock_result = SimpleNamespace(
            returncode=0,
            stdout="NAME   ID   SIZE   MODIFIED\nllama3:8b  x  5 GB  now\n",
            stderr="",
        )
        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            best = await client.get_best_available_model()
        assert best is None

    @pytest.mark.asyncio
    async def test_generate_success_mock(self):
        """generate returns response text on success (mock)."""
        client = OllamaOfflineClient()
        client._available_models = [
            OllamaModelInfo(name="phi3:mini", size_bytes=2_200_000_000, modified=""),
        ]
        gen_result = SimpleNamespace(returncode=0, stdout="The answer is 42.", stderr="")
        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=gen_result):
            response = await client.generate("What is the answer?", OfflineModel.PHI3_MINI)
        assert response == "The answer is 42."

    @pytest.mark.asyncio
    async def test_generate_unavailable_model_raises_mock(self):
        """generate raises RuntimeError when model not in available list (mock)."""
        client = OllamaOfflineClient()
        client._available_models = [
            OllamaModelInfo(name="gemma3:270m", size_bytes=291_000_000, modified=""),
        ]
        with pytest.raises(RuntimeError, match="not available"):
            await client.generate("Hello", OfflineModel.GPT_OSS_20B)


class TestSingletonCachesModelsMocked:
    """Mock-based test for singleton model caching (covers skipped test_singleton_caches_models)."""

    @pytest.mark.asyncio
    async def test_singleton_caches_models_mocked(self):
        """is_model_available uses cached _available_models after first fetch (mock)."""
        import aipea.engine as mod

        original = mod._ollama_client
        try:
            mod._ollama_client = None
            client = get_ollama_client()

            mock_result = SimpleNamespace(
                returncode=0,
                stdout="NAME   ID   SIZE   MODIFIED\ngemma3:270m  x  291 MB  now\n",
                stderr="",
            )
            with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
                models1 = await client.get_available_models()

            assert len(models1) == 1
            # After fetching, _available_models is set — is_model_available
            # uses this cached list without re-fetching
            assert client._available_models is not None
            result = await client.is_model_available(OfflineModel.GEMMA3_270M)
            assert result is True
        finally:
            mod._ollama_client = original


class TestOfflineTierProcessorWithOllamaMocked:
    """Mock-based tests for OfflineTierProcessor Ollama integration.

    Covers the same code paths as the skipped TestOfflineTierProcessorWithOllama.
    """

    @pytest.mark.asyncio
    async def test_processor_uses_ollama_mock(self):
        """Processor with use_ollama=True delegates to Ollama when models available (mock)."""
        proc = OfflineTierProcessor(use_ollama=True)

        mock_client = MagicMock(spec=OllamaOfflineClient)
        mock_client.get_best_available_model = AsyncMock(return_value=OfflineModel.PHI3_MINI)
        mock_client.generate = AsyncMock(return_value="Mocked LLM response about unit testing")

        with patch("aipea.engine.get_ollama_client", return_value=mock_client):
            result = await proc.process("What are three benefits of unit testing?")

        assert isinstance(result, EnhancedQuery)
        assert result.tier_used == ProcessingTier.OFFLINE
        assert result.enhancement_metadata.get("llm_enhanced") is True
        assert result.enhancement_metadata.get("ollama_model") == "phi3:mini"
        assert result.confidence >= 0.80

    @pytest.mark.asyncio
    async def test_processor_classifies_query_type_mock(self):
        """Processor correctly classifies query types without Ollama (mock)."""
        proc = OfflineTierProcessor(use_ollama=False)

        # Technical query
        result = await proc.process("Debug this Python code error")
        assert result.query_type == QueryType.TECHNICAL

        # Research query
        result = await proc.process("Research the latest AI findings")
        assert result.query_type == QueryType.RESEARCH

        # Operational query
        result = await proc.process("How to install Docker on Ubuntu")
        assert result.query_type == QueryType.OPERATIONAL


# =============================================================================
# BUG-HUNT REGRESSION TESTS
# =============================================================================


class TestOllamaGetModelsErrorCaching:
    """Regression: get_available_models must cache empty list on failure."""

    @pytest.mark.asyncio
    async def test_error_path_caches_empty_list(self):
        """After a failure, _available_models should be [] (not None) to prevent re-spawning."""
        client = OllamaOfflineClient()
        assert client._available_models is None

        # Simulate FileNotFoundError (Ollama not installed)
        mock_result = FileNotFoundError("ollama not found")
        with patch("asyncio.to_thread", new_callable=AsyncMock, side_effect=mock_result):
            result = await client.get_available_models()

        assert result == []
        assert client._available_models == [], "_available_models should be cached as [] on error"

    @pytest.mark.asyncio
    async def test_nonzero_returncode_caches_empty_list(self):
        """Non-zero returncode from 'ollama list' should cache _available_models = []."""
        client = OllamaOfflineClient()
        assert client._available_models is None

        mock_result = SimpleNamespace(returncode=1, stdout="", stderr="daemon not running")
        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            result = await client.get_available_models()

        assert result == []
        assert client._available_models == [], (
            "_available_models should be cached on non-zero returncode"
        )


class TestOllamaGenerateErrorNotDoubleWrapped:
    """Regression: RuntimeError from failed ollama run must not be double-wrapped."""

    @pytest.mark.asyncio
    async def test_runtime_error_not_double_wrapped(self):
        """RuntimeError raised inside generate should propagate without re-wrapping."""
        client = OllamaOfflineClient()
        client._available_models = [
            OllamaModelInfo(name="phi3:mini", size_bytes=2_200_000_000, modified=""),
        ]

        # Simulate non-zero exit code
        mock_result = SimpleNamespace(returncode=1, stdout="", stderr="model not found")
        with (
            patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result),
            pytest.raises(RuntimeError, match=r"^Ollama generation failed:"),
        ):
            await client.generate("test", OfflineModel.PHI3_MINI)


# =============================================================================
# WAVE 6 BUG-FIX REGRESSION TESTS
# =============================================================================


class TestOllamaRaceCondition:
    """Regression #9: Concurrent _check_ollama_availability must not race."""

    @pytest.mark.asyncio
    async def test_concurrent_check_ollama_only_probes_once(self):
        """Multiple concurrent calls to _check_ollama_availability should probe Ollama once."""
        processor = OfflineTierProcessor(use_ollama=True)

        probe_count = 0

        async def counting_get_best(_self_client):  # type: ignore[override]
            nonlocal probe_count
            probe_count += 1
            # Simulate a slow probe
            await asyncio.sleep(0.05)
            return None

        with patch.object(OllamaOfflineClient, "get_best_available_model", counting_get_best):
            # Launch 5 concurrent availability checks
            await asyncio.gather(
                processor._check_ollama_availability(),
                processor._check_ollama_availability(),
                processor._check_ollama_availability(),
                processor._check_ollama_availability(),
                processor._check_ollama_availability(),
            )

        # With proper locking, only one probe should run
        assert probe_count == 1
        assert processor._ollama_checked is True


# =============================================================================
# WAVE 7 BUG-FIX REGRESSION TESTS
# =============================================================================


class TestNaNGuardsEngine:
    """Regression: NaN values bypass clamping in engine.py dataclasses (wave 7)."""

    @pytest.mark.unit
    def test_search_context_nan_confidence_defaults_to_zero(self) -> None:
        """SearchContext with NaN confidence should default to 0.0."""
        ctx = SearchContext(query="t", results=[], confidence=float("nan"))
        assert ctx.confidence == 0.0

    @pytest.mark.unit
    def test_enhanced_query_nan_confidence_defaults_to_zero(self) -> None:
        """EnhancedQuery with NaN confidence should default to 0.0."""
        eq = EnhancedQuery(
            original_query="test",
            enhanced_query="test enhanced",
            tier_used=ProcessingTier.OFFLINE,
            confidence=float("nan"),
            query_type=QueryType.TECHNICAL,
        )
        assert eq.confidence == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
