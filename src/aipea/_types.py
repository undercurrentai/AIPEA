"""Shared type definitions for AIPEA.

Enums and type aliases used across multiple AIPEA modules.
These are extracted here to prevent circular imports.
"""

from __future__ import annotations

from enum import Enum, auto


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

    NONE = auto()
    QUICK_FACTS = auto()
    DEEP_RESEARCH = auto()
    MULTI_SOURCE = auto()


__all__ = [
    "ProcessingTier",
    "QueryType",
    "SearchStrategy",
]
