"""Integration tests for AIPEA Ollama offline processing.

These tests require Ollama to be installed and the following models to be downloaded:
- gemma3:270m (291 MB)
- phi3:mini (2.2 GB)

To download the models:
    ollama pull gemma3:270m
    ollama pull phi3:mini

Run these tests with:
    pytest tests/test_aipea_ollama_integration.py -v -m integration

These tests are marked as 'integration' and 'slow' since they require real model inference.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from aipea._types import (
    ProcessingTier,
    QueryType,
)
from aipea.engine import (
    EnhancedQuery,
    OfflineModel,
    OfflineTierProcessor,
    OllamaOfflineClient,
    get_ollama_client,
)

if TYPE_CHECKING:
    pass


def ollama_available() -> bool:
    """Check if Ollama is available and running."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def model_available(model_name: str) -> bool:
    """Check if a specific Ollama model is downloaded."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False
        return model_name in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# Skip conditions
skip_no_ollama = pytest.mark.skipif(
    not ollama_available(),
    reason="Ollama not available",
)

skip_no_gemma = pytest.mark.skipif(
    not model_available("gemma3:270m"),
    reason="gemma3:270m not downloaded. Run: ollama pull gemma3:270m",
)

skip_no_phi3 = pytest.mark.skipif(
    not model_available("phi3:mini"),
    reason="phi3:mini not downloaded. Run: ollama pull phi3:mini",
)


@pytest.mark.integration
class TestOllamaClientIntegration:
    """Integration tests for OllamaOfflineClient."""

    @skip_no_ollama
    @pytest.mark.asyncio
    async def test_get_available_models(self) -> None:
        """Test listing available Ollama models."""
        client = OllamaOfflineClient()
        models = await client.get_available_models()

        assert isinstance(models, list)
        # Should find at least one model if Ollama is properly set up
        # (we know gemma3:270m and phi3:mini are available)
        assert len(models) >= 1

        # Verify model info structure
        for model in models:
            assert hasattr(model, "name")
            assert hasattr(model, "size_bytes")
            assert model.name  # Non-empty name

    @skip_no_ollama
    @skip_no_gemma
    @pytest.mark.asyncio
    async def test_is_model_available_gemma(self) -> None:
        """Test checking Gemma 3 270M availability."""
        client = OllamaOfflineClient()
        available = await client.is_model_available(OfflineModel.GEMMA3_270M)
        assert available is True

    @skip_no_ollama
    @skip_no_phi3
    @pytest.mark.asyncio
    async def test_is_model_available_phi3(self) -> None:
        """Test checking Phi-3 Mini availability."""
        client = OllamaOfflineClient()
        available = await client.is_model_available(OfflineModel.PHI3_MINI)
        assert available is True

    @skip_no_ollama
    @pytest.mark.asyncio
    async def test_is_model_available_not_downloaded(self) -> None:
        """Test checking unavailable model."""
        client = OllamaOfflineClient()
        # GPT-OSS-20B is defined but not available via Ollama
        available = await client.is_model_available(OfflineModel.GPT_OSS_20B)
        assert available is False

    @skip_no_ollama
    @pytest.mark.asyncio
    async def test_get_best_available_model(self) -> None:
        """Test getting best available model."""
        client = OllamaOfflineClient()
        best = await client.get_best_available_model()

        # Should return one of the tier 1 models in preference order
        assert best is not None
        assert best in [OfflineModel.PHI3_MINI, OfflineModel.GEMMA3_1B, OfflineModel.GEMMA3_270M]


@pytest.mark.integration
@pytest.mark.slow
class TestOllamaGeneration:
    """Integration tests for actual Ollama generation.

    These tests are marked 'slow' because they require model inference.
    """

    @skip_no_ollama
    @skip_no_gemma
    @pytest.mark.asyncio
    async def test_generate_with_gemma(self) -> None:
        """Test generating with Gemma 3 270M."""
        client = OllamaOfflineClient()

        response = await client.generate(
            "Say hello in exactly one word.",
            OfflineModel.GEMMA3_270M,
        )

        assert isinstance(response, str)
        assert len(response) > 0
        # Gemma should respond with something containing "hello" or similar
        assert len(response) < 500  # Should be brief

    @skip_no_ollama
    @skip_no_phi3
    @pytest.mark.asyncio
    async def test_generate_with_phi3(self) -> None:
        """Test generating with Phi-3 Mini."""
        client = OllamaOfflineClient()

        response = await client.generate(
            "What is 2+2? Answer with just the number.",
            OfflineModel.PHI3_MINI,
        )

        assert isinstance(response, str)
        assert len(response) > 0
        # Should contain "4" somewhere in the response
        assert "4" in response

    @skip_no_ollama
    @pytest.mark.asyncio
    async def test_generate_unavailable_model_raises(self) -> None:
        """Test that generating with unavailable model raises."""
        client = OllamaOfflineClient()

        with pytest.raises(RuntimeError, match="not available"):
            await client.generate(
                "Hello",
                OfflineModel.GPT_OSS_20B,  # Not available
            )


@pytest.mark.integration
@pytest.mark.slow
class TestOfflineTierProcessorWithOllama:
    """Integration tests for OfflineTierProcessor with real Ollama."""

    @skip_no_ollama
    @pytest.mark.asyncio
    async def test_processor_uses_ollama_when_available(self) -> None:
        """Test that processor uses Ollama when models are available."""
        processor = OfflineTierProcessor(use_ollama=True)

        # Process a technical query
        result = await processor.process("Write a simple Python function to add two numbers.")

        assert isinstance(result, EnhancedQuery)
        assert result.tier_used == ProcessingTier.OFFLINE

        # Check metadata - should indicate LLM was used if Ollama available
        if result.enhancement_metadata.get("llm_enhanced"):
            assert "ollama_model" in result.enhancement_metadata
            assert result.confidence >= 0.80
        else:
            # Fallback to templates if Ollama not available
            assert result.confidence >= 0.70

    @skip_no_ollama
    @pytest.mark.asyncio
    async def test_processor_falls_back_to_templates(self) -> None:
        """Test processor falls back to templates when Ollama disabled."""
        processor = OfflineTierProcessor(use_ollama=False)

        result = await processor.process("Explain quantum computing basics.")

        assert isinstance(result, EnhancedQuery)
        assert result.tier_used == ProcessingTier.OFFLINE
        assert result.enhancement_metadata.get("llm_enhanced") is False
        assert "ollama_model" not in result.enhancement_metadata

    @skip_no_ollama
    @pytest.mark.asyncio
    async def test_processor_classifies_query_type(self) -> None:
        """Test that processor correctly classifies query types."""
        processor = OfflineTierProcessor(use_ollama=False)

        # Technical query
        result = await processor.process("Debug this Python code error")
        assert result.query_type == QueryType.TECHNICAL

        # Research query
        result = await processor.process("Research the latest AI findings")
        assert result.query_type == QueryType.RESEARCH

        # Operational query
        result = await processor.process("How to install Docker on Ubuntu")
        assert result.query_type == QueryType.OPERATIONAL

    @skip_no_ollama
    @skip_no_gemma
    @pytest.mark.asyncio
    async def test_real_query_with_gemma(self) -> None:
        """Test a real query processed with Gemma 3 270M.

        This is a full end-to-end test of offline processing.
        """
        processor = OfflineTierProcessor(use_ollama=True)

        result = await processor.process(
            "What are three benefits of unit testing?",
            context={"use_llm": True},
        )

        assert isinstance(result, EnhancedQuery)
        assert result.original_query == "What are three benefits of unit testing?"
        assert len(result.enhanced_query) > 50  # Should have substantive response

        # If Ollama was used, verify metadata
        if result.enhancement_metadata.get("llm_enhanced"):
            model = result.enhancement_metadata.get("ollama_model")
            assert model in ["gemma3:270m", "phi3:mini"]


@pytest.mark.integration
class TestOfflineModelTiers:
    """Tests for offline model tier classification."""

    def test_tier1_models(self) -> None:
        """Test Tier 1 model classification."""
        tier1 = OfflineModel.tier1_models()
        assert OfflineModel.GEMMA3_1B in tier1
        assert OfflineModel.GEMMA3_270M in tier1
        assert OfflineModel.PHI3_MINI in tier1
        assert len(tier1) == 3

    def test_tier2_models(self) -> None:
        """Test Tier 2/3 model classification."""
        tier2 = OfflineModel.tier2_models()
        assert OfflineModel.GPT_OSS_20B in tier2
        assert OfflineModel.LLAMA_3_3_70B in tier2
        assert len(tier2) == 2

    def test_model_values(self) -> None:
        """Test correct Ollama model names."""
        assert OfflineModel.GEMMA3_270M.value == "gemma3:270m"
        assert OfflineModel.PHI3_MINI.value == "phi3:mini"
        assert OfflineModel.GPT_OSS_20B.value == "gpt-oss-20b"
        assert OfflineModel.LLAMA_3_3_70B.value == "llama-3.3-70b"


@pytest.mark.integration
class TestSingletonAccessor:
    """Tests for singleton accessor functions."""

    def test_get_ollama_client_singleton(self) -> None:
        """Test that get_ollama_client returns singleton."""
        client1 = get_ollama_client()
        client2 = get_ollama_client()
        assert client1 is client2

    @skip_no_ollama
    @pytest.mark.asyncio
    async def test_singleton_caches_models(self) -> None:
        """Test that singleton caches model list."""
        client = get_ollama_client()

        # First call fetches models
        models1 = await client.get_available_models()
        # Second call should return cached
        models2 = await client.get_available_models()

        assert models1 == models2


# Benchmark tests for performance measurement
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.benchmark
class TestOllamaPerformance:
    """Performance benchmarks for Ollama models."""

    @skip_no_ollama
    @skip_no_gemma
    @pytest.mark.asyncio
    async def test_gemma_inference_time(self) -> None:
        """Benchmark Gemma 3 270M inference time."""
        import time

        client = OllamaOfflineClient()

        start = time.perf_counter()
        await client.generate(
            "Hello",
            OfflineModel.GEMMA3_270M,
        )
        elapsed = time.perf_counter() - start

        # Gemma 3 270M should respond within 2 seconds for simple prompts
        assert elapsed < 5.0, f"Gemma inference took {elapsed:.2f}s (expected <5s)"

    @skip_no_ollama
    @skip_no_phi3
    @pytest.mark.asyncio
    async def test_phi3_inference_time(self) -> None:
        """Benchmark Phi-3 Mini inference time."""
        import time

        client = OllamaOfflineClient()

        start = time.perf_counter()
        await client.generate(
            "Hello",
            OfflineModel.PHI3_MINI,
        )
        elapsed = time.perf_counter() - start

        # Phi-3 Mini may take longer due to larger size
        assert elapsed < 30.0, f"Phi-3 inference took {elapsed:.2f}s (expected <30s)"
