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

    @property
    def confidence_threshold(self) -> float:
        """Minimum confidence score for successful processing."""
        thresholds = {
            ProcessingTier.OFFLINE: 0.70,
            ProcessingTier.TACTICAL: 0.85,
            ProcessingTier.STRATEGIC: 0.95,
        }
        return thresholds[self]


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


__all__ = [
    "QUERY_TYPE_PRIORITY",
    "ProcessingTier",
    "QueryType",
    "SearchStrategy",
]
