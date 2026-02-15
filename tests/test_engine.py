#!/usr/bin/env python3
"""
Unit Tests for Prompt Engine - Claude Code SDK Integration
Tests the enhanced prompt engineering capabilities with search context
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

# Import the module under test
from aipea.engine import (
    OfflineTierProcessor,
    PromptEngine,
    SearchContext,
    get_prompt_engine,
)


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
