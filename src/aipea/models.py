"""Shared data models for AIPEA.

Data classes used across AIPEA modules for passing enhancement results
between components and back to consumers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from aipea._types import ProcessingTier, QueryType, SearchStrategy

logger = logging.getLogger(__name__)


@dataclass
class QueryAnalysis:
    """Result of analyzing a query for routing decisions.

    Populated during Phase 2 extraction. This placeholder defines
    the public interface contract.
    """

    query: str
    query_type: QueryType
    complexity: float  # 0.0-1.0
    confidence: float  # 0.0-1.0
    needs_current_info: bool
    temporal_markers: list[str] = field(default_factory=list)
    domain_indicators: list[str] = field(default_factory=list)
    ambiguity_score: float = 0.0
    detected_entities: list[str] = field(default_factory=list)
    suggested_tier: ProcessingTier | None = None
    search_strategy: SearchStrategy = SearchStrategy.NONE

    def __post_init__(self) -> None:
        """Validate and clamp scores to valid ranges."""
        # Clamp complexity
        if not 0.0 <= self.complexity <= 1.0:
            logger.warning(
                "QueryAnalysis complexity %f outside [0, 1] range, clamping", self.complexity
            )
            self.complexity = max(0.0, min(1.0, self.complexity))

        # Clamp confidence
        if not 0.0 <= self.confidence <= 1.0:
            logger.warning(
                "QueryAnalysis confidence %f outside [0, 1] range, clamping", self.confidence
            )
            self.confidence = max(0.0, min(1.0, self.confidence))

        # Clamp ambiguity score
        if not 0.0 <= self.ambiguity_score <= 1.0:
            logger.warning(
                "QueryAnalysis ambiguity_score %f outside [0, 1] range, clamping",
                self.ambiguity_score,
            )
            self.ambiguity_score = max(0.0, min(1.0, self.ambiguity_score))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "query": self.query,
            "query_type": self.query_type.value,
            "complexity": self.complexity,
            "confidence": self.confidence,
            "needs_current_info": self.needs_current_info,
            "temporal_markers": self.temporal_markers,
            "domain_indicators": self.domain_indicators,
            "ambiguity_score": self.ambiguity_score,
            "detected_entities": self.detected_entities,
            "suggested_tier": self.suggested_tier.value if self.suggested_tier else None,
            "search_strategy": self.search_strategy.name,
        }


__all__ = [
    "QueryAnalysis",
]
