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
    StrategicTierProcessor,
    TacticalTierProcessor,
    get_ollama_client,
    get_prompt_engine,
)
from aipea.search import SearchContext as AIPEASearchContext
from aipea.search import SearchResult


class TestSearchContext:
    """Test SearchContext data class functionality"""

    def test_search_context_creation(self):
        """Test creating SearchContext with valid data"""
        results = [
            {
                "title": "Test Article",
                "snippet": "Test content snippet",
                "url": "https://example.com",
            }
        ]

        context = SearchContext(
            results=results,
            sources=["example.com"],
            confidence_score=0.85,
            search_timestamp="2025-01-01T12:00:00",
            query_type="web",
        )

        assert context.results == results
        assert context.sources == ["example.com"]
        assert context.confidence_score == 0.85
        assert context.query_type == "web"

    def test_formatted_for_model_openai(self):
        """Test OpenAI-specific formatting"""
        results = [
            {
                "title": "AI Development 2025",
                "snippet": "Latest AI developments in machine learning",
                "url": "https://example.com/ai-2025",
            }
        ]

        context = SearchContext(
            results=results,
            sources=["example.com"],
            confidence_score=0.9,
            search_timestamp="2025-01-01T12:00:00",
        )

        formatted = context.formatted_for_model("openai")

        assert "# Current Information Context" in formatted
        assert "AI Development 2025" in formatted
        assert "Latest AI developments" in formatted
        assert "example.com" in formatted
        assert "1. **" in formatted  # OpenAI structured format

    def test_formatted_for_model_openai_numbers_each_result(self):
        """Ensure OpenAI formatting numbers results sequentially."""
        results = [
            {
                "title": "Result One",
                "snippet": "First snippet",
                "url": "https://example.com/one",
            },
            {
                "title": "Result Two",
                "snippet": "Second snippet",
                "url": "https://example.com/two",
            },
        ]

        context = SearchContext(
            results=results,
            sources=["example.com"],
            confidence_score=0.9,
            search_timestamp="2025-01-01T12:00:00",
        )

        formatted = context.formatted_for_model("openai")

        assert "1. **Result One**" in formatted
        assert "2. **Result Two**" in formatted

    def test_formatted_for_model_claude(self):
        """Test Claude-specific formatting"""
        results = [
            {
                "title": "Python Best Practices",
                "snippet": "Modern Python development guidelines",
                "url": "https://python.org/guide",
            }
        ]

        context = SearchContext(
            results=results,
            sources=["python.org"],
            confidence_score=0.8,
            search_timestamp="2025-01-01T12:00:00",
        )

        formatted = context.formatted_for_model("claude")

        assert "## Source 1:" in formatted  # Claude detailed format
        assert "**URL:**" in formatted
        assert "**Content:**" in formatted
        assert "python.org" in formatted

    def test_empty_results_formatting(self):
        """Test formatting with no search results"""
        context = SearchContext(
            results=[],
            sources=[],
            confidence_score=0.0,
            search_timestamp="2025-01-01T12:00:00",
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
            results=[
                {
                    "title": "AI Safety Research 2025",
                    "snippet": "Recent developments in AI alignment and safety protocols",
                    "url": "https://ai-safety.org/2025-research",
                },
                {
                    "title": "Machine Learning Advances",
                    "snippet": "Breakthrough in transformer architecture efficiency",
                    "url": "https://ml-research.com/advances",
                },
            ],
            sources=["ai-safety.org", "ml-research.com"],
            confidence_score=0.88,
            search_timestamp="2025-01-01T15:30:00",
            query_type="web",
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
        """Test model-specific prompt optimization for OpenAI"""
        base_prompt = "Analyze the current state of artificial intelligence"

        optimized = await prompt_engine.create_model_specific_prompt(
            base_prompt=base_prompt,
            model_type="gpt-4",
            search_context=mock_search_context,
        )

        assert "System:" in optimized  # OpenAI system message format
        assert "Clear headings and structure" in optimized
        assert "AI Safety Research 2025" in optimized  # Search context included

    @pytest.mark.asyncio
    async def test_model_specific_optimization_claude(self, prompt_engine, mock_search_context):
        """Test model-specific prompt optimization for Claude"""
        base_prompt = "Evaluate ethical implications of AI development"

        optimized = await prompt_engine.create_model_specific_prompt(
            base_prompt=base_prompt,
            model_type="claude-4",
            search_context=mock_search_context,
        )

        assert "sophisticated analysis" in optimized
        assert "nuanced understanding" in optimized
        assert "## Source 1:" in optimized  # Claude-formatted search context

    @pytest.mark.asyncio
    async def test_model_specific_optimization_gemini(self, prompt_engine, mock_search_context):
        """Test model-specific prompt optimization for Gemini"""
        base_prompt = "Create a comprehensive technology roadmap"

        optimized = await prompt_engine.create_model_specific_prompt(
            base_prompt=base_prompt,
            model_type="gemini-pro",
            search_context=mock_search_context,
        )

        assert "comprehensive response" in optimized
        assert "practical application" in optimized
        assert "Supporting Information:" in optimized  # Gemini-formatted search context

    def test_prompt_template_complexity_simple(self, prompt_engine):
        """Test prompt template for simple complexity"""
        template = prompt_engine._get_prompt_template("simple", "general")

        assert "straightforward query" in template
        assert "direct, accurate response" in template
        assert "clear, concise" in template

    def test_prompt_template_complexity_complex(self, prompt_engine):
        """Test prompt template for complex complexity"""
        template = prompt_engine._get_prompt_template("complex", "general")

        assert "complex query" in template
        assert "deep, systematic analysis" in template
        assert "comprehensive reasoning" in template

    def test_prompt_template_model_specific_instructions(self, prompt_engine):
        """Test model-specific instructions in templates"""
        openai_template = prompt_engine._get_prompt_template("medium", "openai")
        claude_template = prompt_engine._get_prompt_template("medium", "claude")
        gemini_template = prompt_engine._get_prompt_template("medium", "gemini")

        # OpenAI specific
        assert "structured, logical responses" in openai_template
        assert "step-by-step reasoning" in openai_template

        # Claude specific
        assert "detailed, nuanced analysis" in claude_template
        assert "sophisticated reasoning" in claude_template

        # Gemini specific
        assert "comprehensive, well-structured" in gemini_template
        assert "practical applications" in gemini_template

    def test_current_date_integration(self, prompt_engine):
        """Test that current date is properly integrated"""
        template = prompt_engine._get_prompt_template("medium", "general")

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
            results=[
                {
                    "title": None,  # Missing title
                    "snippet": "",  # Empty snippet
                    "url": "invalid-url",  # Invalid URL
                }
            ],
            sources=[],
            confidence_score=-1.0,  # Invalid confidence
            search_timestamp="invalid-date",
            query_type="unknown",
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
                {
                    "title": f"Large Result {i}" * 10,  # Long titles
                    "snippet": f"Very long snippet content for result {i}. " * 50,  # Long snippets
                    "url": f"https://example{i}.com/very/long/url/path",
                }
            )

        large_context = SearchContext(
            results=large_results,
            sources=[f"example{i}.com" for i in range(100)],
            confidence_score=0.5,
            search_timestamp="2025-01-01T12:00:00",
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
        """tier1_models returns Gemma3 and Phi3."""
        tier1 = OfflineModel.tier1_models()
        assert OfflineModel.GEMMA3_270M in tier1
        assert OfflineModel.PHI3_MINI in tier1
        assert len(tier1) == 2

    def test_tier2_models_returns_future_models(self):
        """tier2_models returns GPT-OSS and Llama 3.3."""
        tier2 = OfflineModel.tier2_models()
        assert OfflineModel.GPT_OSS_20B in tier2
        assert OfflineModel.LLAMA_3_3_70B in tier2
        assert len(tier2) == 2


# ---------------------------------------------------------------------------
# 2. OllamaOfflineClient (lines 138-337)
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
# 3. get_ollama_client() singleton (lines 354-358)
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
# 4. SearchContext.__post_init__ confidence clamping (line 390)
# ---------------------------------------------------------------------------


class TestSearchContextPostInit:
    """Tests for SearchContext __post_init__ auto-timestamp and clamping."""

    def test_auto_timestamp_when_empty(self):
        """Generates ISO timestamp when search_timestamp is empty (line 390)."""
        ctx = SearchContext(results=[], sources=[], confidence_score=0.5)
        assert ctx.search_timestamp != ""
        # Should be a valid ISO format string
        assert "T" in ctx.search_timestamp


# ---------------------------------------------------------------------------
# 5. SearchContext._format_generic() with results (line 501)
# ---------------------------------------------------------------------------


class TestSearchContextFormatGeneric:
    """Tests for _format_generic with non-empty results."""

    def test_format_generic_with_results(self):
        """Generic format includes 'Supporting Information' header (line 501+)."""
        ctx = SearchContext(
            results=[
                {"title": "Result A", "snippet": "Content A", "url": "https://a.com"},
            ],
            sources=["a.com"],
            confidence_score=0.7,
            search_timestamp="2025-06-01T00:00:00",
        )
        formatted = ctx.formatted_for_model("gemini")
        assert "Supporting Information:" in formatted
        assert "1. Result A" in formatted
        assert "https://a.com" in formatted


# ---------------------------------------------------------------------------
# 6. SearchContext.from_aipea_context() (lines 535-545)
# ---------------------------------------------------------------------------


class TestSearchContextFromAIPEA:
    """Tests for SearchContext.from_aipea_context conversion."""

    def test_from_aipea_context_basic(self):
        """Converts an AIPEA SearchContext to legacy SearchContext."""
        aipea_ctx = AIPEASearchContext(
            query="test query",
            results=[
                SearchResult(title="Title1", url="https://x.com", snippet="Snip1", score=0.9),
                SearchResult(title="Title2", url="https://y.com", snippet="Snip2", score=0.5),
            ],
            source="exa",
            confidence=0.85,
        )
        legacy = SearchContext.from_aipea_context(aipea_ctx)

        assert len(legacy.results) == 2
        assert legacy.results[0]["title"] == "Title1"
        assert legacy.results[1]["url"] == "https://y.com"
        assert legacy.sources == ["exa"]
        assert legacy.confidence_score == 0.85
        assert legacy.query_type == "web"

    def test_from_aipea_context_empty(self):
        """Handles empty AIPEA context."""
        aipea_ctx = AIPEASearchContext(query="empty", results=[], source="none", confidence=0.0)
        legacy = SearchContext.from_aipea_context(aipea_ctx)
        assert legacy.results == []
        assert legacy.is_empty()


# ---------------------------------------------------------------------------
# 7. EnhancedQuery.__post_init__ confidence clamping (lines 582-585)
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


# ---------------------------------------------------------------------------
# 8. TierProcessor abstract (lines 615, 625) — tested via subclasses below
# 9. OfflineTierProcessor.tier property (line 767)
# ---------------------------------------------------------------------------


class TestOfflineTierProcessorProperties:
    """Tests for OfflineTierProcessor.tier and Ollama integration."""

    def test_tier_returns_offline(self):
        """tier property returns ProcessingTier.OFFLINE (line 767)."""
        proc = OfflineTierProcessor(use_ollama=False)
        assert proc.tier == ProcessingTier.OFFLINE

    # -- _check_ollama_availability (lines 798-817) --

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
# 14. TacticalTierProcessor (lines 998, 1014-1073, 1089-1094)
# ---------------------------------------------------------------------------


class TestTacticalTierProcessor:
    """Tests for TacticalTierProcessor.tier, process, and _get_available_models."""

    def test_tier_returns_tactical(self):
        """tier property returns ProcessingTier.TACTICAL (line 998)."""
        proc = TacticalTierProcessor()
        assert proc.tier == ProcessingTier.TACTICAL

    @pytest.mark.asyncio
    async def test_process_without_orchestrator(self):
        """Processes with template fallback when no orchestrator (lines 1014-1073)."""
        proc = TacticalTierProcessor(orchestrator=None)
        result = await proc.process("How to install python packages")

        assert result.tier_used == ProcessingTier.TACTICAL
        assert result.confidence == 0.85
        assert "tactical analysis" in result.enhanced_query.lower()
        assert result.enhancement_metadata["llm_assisted"] is False

    @pytest.mark.asyncio
    async def test_process_with_search_context(self):
        """Includes search context when provided in context dict."""
        proc = TacticalTierProcessor(orchestrator=None)
        sc = SearchContext(
            results=[{"title": "T", "snippet": "S", "url": "https://t.com"}],
            sources=["t.com"],
            confidence_score=0.8,
            search_timestamp="2025-01-01T00:00:00",
        )
        result = await proc.process("test", context={"search_context": sc})

        assert result.search_context is sc
        assert result.enhancement_metadata["has_search_context"] is True

    @pytest.mark.asyncio
    async def test_process_with_orchestrator_success(self):
        """Uses orchestrator.consult for LLM disambiguation (lines 1051-1069)."""
        mock_response = SimpleNamespace(content="Improved query: what are best practices?")
        mock_orch = MagicMock()
        mock_orch.consult = AsyncMock(return_value=[mock_response])
        mock_orch.providers = {"openai": True}

        proc = TacticalTierProcessor(orchestrator=mock_orch)
        result = await proc.process("best practices")

        assert result.enhancement_metadata["llm_assisted"] is True
        assert result.confidence == 0.88
        assert "Improved query" in result.enhanced_query

    @pytest.mark.asyncio
    async def test_process_with_orchestrator_exception_fallback(self):
        """Falls back on orchestrator exception (line 1070-1071)."""
        mock_orch = MagicMock()
        mock_orch.consult = AsyncMock(side_effect=RuntimeError("API down"))
        mock_orch.providers = {"openai": True}

        proc = TacticalTierProcessor(orchestrator=mock_orch)
        result = await proc.process("test query")

        assert result.enhancement_metadata["llm_assisted"] is False
        assert result.confidence == 0.85

    @pytest.mark.asyncio
    async def test_process_with_orchestrator_empty_response(self):
        """Handles empty response content from orchestrator."""
        mock_response = SimpleNamespace(content="")
        mock_orch = MagicMock()
        mock_orch.consult = AsyncMock(return_value=[mock_response])
        mock_orch.providers = {"openai": True}

        proc = TacticalTierProcessor(orchestrator=mock_orch)
        result = await proc.process("test query")

        # Empty content means llm_assisted stays False
        assert result.enhancement_metadata["llm_assisted"] is False

    def test_get_available_models_no_orchestrator(self):
        """Returns empty list without orchestrator (line 1089)."""
        proc = TacticalTierProcessor(orchestrator=None)
        assert proc._get_available_models() == []

    def test_get_available_models_with_providers(self):
        """Returns at most 1 model tuple for tactical tier (lines 1091-1094)."""
        mock_orch = MagicMock()
        mock_orch.providers = {"openai": True, "anthropic": True}

        proc = TacticalTierProcessor(orchestrator=mock_orch)
        models = proc._get_available_models()
        assert len(models) == 1
        assert models[0][1] == "default"


# ---------------------------------------------------------------------------
# 17. StrategicTierProcessor (lines 1141, 1157-1203, 1229-1315, 1319-1324)
# ---------------------------------------------------------------------------


class TestStrategicTierProcessor:
    """Tests for StrategicTierProcessor."""

    def test_tier_returns_strategic(self):
        """tier property returns ProcessingTier.STRATEGIC (line 1141)."""
        proc = StrategicTierProcessor()
        assert proc.tier == ProcessingTier.STRATEGIC

    @pytest.mark.asyncio
    async def test_process_without_orchestrator(self):
        """Template-only strategic processing (lines 1157-1203)."""
        proc = StrategicTierProcessor(orchestrator=None)
        result = await proc.process("What is the future of quantum computing?")

        assert result.tier_used == ProcessingTier.STRATEGIC
        assert result.confidence == 0.92
        assert "Strategic Analysis Required" in result.enhanced_query
        assert result.enhancement_metadata["multi_agent"] is False
        assert result.enhancement_metadata["critique_rounds"] == 0

    @pytest.mark.asyncio
    async def test_process_with_orchestrator_success(self):
        """Multi-step reasoning when orchestrator provided (lines 1191-1199)."""
        # Create mock responses for each stage
        decompose_resp = SimpleNamespace(content="Sub Q1\nSub Q2")
        analysis_resp = SimpleNamespace(content="Analysis for sub-question")
        synthesis_resp = SimpleNamespace(content="Final synthesis")
        critique_resp = SimpleNamespace(content="APPROVED")

        mock_orch = MagicMock()
        mock_orch.consult = AsyncMock(
            side_effect=[
                # Tactical process call (internal)
                [],
                # Decompose
                [decompose_resp],
                # Analyze sub Q1
                [analysis_resp],
                # Analyze sub Q2
                [analysis_resp],
                # Synthesis
                [synthesis_resp],
                # Critique (APPROVED on first round)
                [critique_resp],
            ]
        )
        mock_orch.providers = {"openai": True}

        proc = StrategicTierProcessor(orchestrator=mock_orch)
        result = await proc.process("Complex multi-domain question")

        assert result.enhancement_metadata["multi_agent"] is True
        assert result.enhancement_metadata["critique_rounds"] >= 1
        assert result.tier_used == ProcessingTier.STRATEGIC

    @pytest.mark.asyncio
    async def test_process_with_orchestrator_exception_fallback(self):
        """Falls back on orchestrator exception (line 1200-1201)."""
        mock_orch = MagicMock()
        mock_orch.consult = AsyncMock(side_effect=RuntimeError("API down"))
        mock_orch.providers = {"openai": True}

        proc = StrategicTierProcessor(orchestrator=mock_orch)
        result = await proc.process("test")

        assert result.enhancement_metadata["multi_agent"] is False
        assert "Strategic Analysis Required" in result.enhanced_query

    @pytest.mark.asyncio
    async def test_run_strategic_reasoning_no_orchestrator_raises(self):
        """Raises RuntimeError when orchestrator is None (line 1229-1230)."""
        proc = StrategicTierProcessor(orchestrator=None)
        with pytest.raises(RuntimeError, match="not initialized"):
            await proc._run_strategic_reasoning("q", "ctx", [("openai", "default")])

    @pytest.mark.asyncio
    async def test_run_strategic_reasoning_critique_loop(self):
        """Critique loop refines until APPROVED (lines 1279-1315)."""
        critique_call_count = 0

        async def mock_consult(prompt, **_kwargs):
            nonlocal critique_call_count
            if "Break the following" in prompt:
                return [SimpleNamespace(content="Sub question 1")]
            elif "concise analysis" in prompt:
                return [SimpleNamespace(content="Analysis result")]
            elif "Synthesize" in prompt:
                return [SimpleNamespace(content="Initial synthesis")]
            elif "Critically evaluate" in prompt:
                critique_call_count += 1
                if critique_call_count >= 2:
                    return [SimpleNamespace(content="APPROVED")]
                return [SimpleNamespace(content="Needs more detail on X")]
            elif "Improve this response" in prompt:
                return [SimpleNamespace(content="Refined synthesis")]
            return []

        mock_orch = MagicMock()
        mock_orch.consult = AsyncMock(side_effect=mock_consult)

        proc = StrategicTierProcessor(orchestrator=mock_orch)
        proc._orchestrator = mock_orch

        result_text, rounds = await proc._run_strategic_reasoning(
            "complex query", "tactical context", [("openai", "default")]
        )
        assert rounds == 2
        assert (
            "Refined synthesis" in result_text or "APPROVED" in result_text or len(result_text) > 0
        )

    def test_get_available_models_no_orchestrator(self):
        """Returns empty list without orchestrator (line 1319)."""
        proc = StrategicTierProcessor(orchestrator=None)
        assert proc._get_available_models() == []

    def test_get_available_models_with_providers(self):
        """Returns at most 2 model tuples for strategic tier (lines 1321-1324)."""
        mock_orch = MagicMock()
        mock_orch.providers = {"openai": True, "anthropic": True, "gemini": True}

        proc = StrategicTierProcessor(orchestrator=mock_orch)
        models = proc._get_available_models()
        assert len(models) == 2


# ---------------------------------------------------------------------------
# 21-22. PromptEngine.classify_query and enhance_query (lines 1428, 1446-1454)
# ---------------------------------------------------------------------------


class TestPromptEngineClassifyAndEnhance:
    """Tests for PromptEngine.classify_query and enhance_query."""

    def test_classify_query_technical(self):
        """classify_query delegates to offline processor (line 1428)."""
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

    @pytest.mark.asyncio
    async def test_enhance_query_offline_tier(self):
        """enhance_query routes to offline processor (line 1447-1448)."""
        engine = PromptEngine()
        result = await engine.enhance_query("How to deploy code", ProcessingTier.OFFLINE)
        assert result.tier_used == ProcessingTier.OFFLINE
        assert isinstance(result, EnhancedQuery)

    @pytest.mark.asyncio
    async def test_enhance_query_tactical_tier(self):
        """enhance_query routes to tactical processor (line 1449-1450)."""
        engine = PromptEngine()
        result = await engine.enhance_query("Analyze data metrics", ProcessingTier.TACTICAL)
        assert result.tier_used == ProcessingTier.TACTICAL

    @pytest.mark.asyncio
    async def test_enhance_query_strategic_tier(self):
        """enhance_query routes to strategic processor (line 1451-1452)."""
        engine = PromptEngine()
        result = await engine.enhance_query("Plan a long-term roadmap", ProcessingTier.STRATEGIC)
        assert result.tier_used == ProcessingTier.STRATEGIC

    @pytest.mark.asyncio
    async def test_enhance_query_invalid_tier_raises(self):
        """enhance_query raises ValueError for unsupported tier (line 1453-1454)."""
        engine = PromptEngine()
        # Create a mock enum value that doesn't match any case
        fake_tier = MagicMock(spec=ProcessingTier)
        fake_tier.value = "nonexistent"
        fake_tier.name = "NONEXISTENT"
        with pytest.raises(ValueError, match="Unsupported processing tier"):
            await engine.enhance_query("test", fake_tier)


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
