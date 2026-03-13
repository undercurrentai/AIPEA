"""Shared type definitions for AIPEA.

Enums and type aliases used across multiple AIPEA modules.
These are extracted here to prevent circular imports.
"""

from __future__ import annotations

from enum import Enum


class ProcessingTier(Enum):
    """Processing tiers for query enhancement.

    Each tier represents a different level of processing complexity,
    with increasing latency and sophistication.
    """

    OFFLINE = "offline"  # <2s, pattern-based, no external calls
    TACTICAL = "tactical"  # 2-5s, LLM-assisted with search context
    STRATEGIC = "strategic"  # 5-15s, multi-agent reasoning chains


class QueryType(Enum):
    """Query type classification for processing strategy selection."""

    TECHNICAL = "technical"
    RESEARCH = "research"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    OPERATIONAL = "operational"
    STRATEGIC = "strategic"
    UNKNOWN = "unknown"


class SearchStrategy(Enum):
    """Search strategy based on query analysis."""

    NONE = "none"
    QUICK_FACTS = "quick_facts"
    DEEP_RESEARCH = "deep_research"
    MULTI_SOURCE = "multi_source"


# Explicit priority for deterministic tie-breaking (lower = higher priority).
# Used by analyzer.py and engine.py when classifying query types via max().
QUERY_TYPE_PRIORITY: dict[QueryType, int] = {
    QueryType.TECHNICAL: 0,
    QueryType.RESEARCH: 1,
    QueryType.ANALYTICAL: 2,
    QueryType.CREATIVE: 3,
    QueryType.OPERATIONAL: 4,
    QueryType.STRATEGIC: 5,
    QueryType.UNKNOWN: 6,
}


# Canonical query type regex patterns — single source of truth for both
# analyzer.py (QueryAnalyzer) and engine.py (OfflineTierProcessor).
QUERY_TYPE_PATTERNS: dict[QueryType, list[str]] = {
    QueryType.TECHNICAL: [
        r"\b(code|program|api|function|class|method|debug|error|exception)\b",
        r"\b(python|javascript|java|c\+\+|rust|golang|typescript)\b",
        r"\b(database|sql|query|schema|table|index)\b",
        r"\b(implement|develop|build|create|design)\b",
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


# ---- Model family detection (canonical, used by enhancer.py + search.py) ----

MODEL_FAMILY_MAP: dict[str, str] = {
    # OpenAI models
    "gpt-5.2": "openai",
    "gpt-5.2-mini": "openai",
    "gpt-4-turbo": "openai",
    "gpt-oss-20b": "openai",
    # Anthropic models
    "claude-opus-4-6": "claude",
    "claude-opus-4-5": "claude",
    "claude-sonnet-4-6": "claude",
    "claude-sonnet-4-5": "claude",
    "claude-haiku-4-5": "claude",
    # Google models
    "gemini-2": "gemini",
    "gemini-2-flash": "gemini",
    "gemini-1.5-pro": "gemini",
    "gemini-1.5-flash": "gemini",
    "gemini-3-pro-preview": "gemini",
    "gemini-3-flash-preview": "gemini",
    "gemma-3n": "gemini",
    # Meta models (offline)
    "llama-3.3-70b": "llama",
    "llama-3.2-3b": "llama",
}


def get_model_family(model_id: str) -> str:
    """Get the model family for a given model ID.

    This is the canonical model family detector. Both enhancer.py and
    search.py use this function to avoid divergent detection logic.

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


__all__ = [
    "MODEL_FAMILY_MAP",
    "QUERY_TYPE_PATTERNS",
    "QUERY_TYPE_PRIORITY",
    "ProcessingTier",
    "QueryType",
    "SearchStrategy",
    "get_model_family",
]
