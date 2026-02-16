"""
AIPEA Query Analyzer - Intelligent query analysis and agentic routing.

Part of the AIPEA (AI Prompt Engineer Agent) subsystem.
Analyzes queries to determine optimal processing tier, search strategy,
and enhancement opportunities.

Architecture:
    - Connectivity: Offline (air-gapped) vs Online (cloud)
    - Security Mode: General, HIPAA, Tactical/Strategic
    - Processing Tiers: Offline (<2s), Tactical (2-5s), Strategic (5-15s)

Key Features:
    - Automatic tier selection based on query complexity
    - Security-aware routing (forces offline for classified)
    - Temporal awareness for current information needs
    - Domain detection for specialized handling
    - Confidence-based escalation

Author: Agora Team
Version: 1.0.0
"""

from __future__ import annotations

import logging
import re
import threading
from typing import ClassVar

from aipea._types import ProcessingTier, QueryType, SearchStrategy
from aipea.models import QueryAnalysis
from aipea.security import SecurityContext, SecurityScanner

logger = logging.getLogger(__name__)


# =============================================================================
# QUERY ROUTER
# =============================================================================


class QueryRouter:
    """Agentic tier selection with automatic escalation.

    Analyzes query complexity, temporal needs, and domain to determine
    optimal processing tier. Considers security context for routing
    decisions and supports automatic escalation when confidence is low.

    Routing Logic:
        - Security level SECRET+ -> Force Tier 0 (Offline)
        - No connectivity -> Force Tier 0
        - Low complexity (<=0.3) + no temporal needs -> Tier 0
        - Medium complexity (>0.3 to 0.7) or temporal needs -> Tier 1
        - High complexity (>0.7) or multi-source needed -> Tier 2
        - Confidence < 0.5 -> Escalate to next tier

    Example:
        >>> router = QueryRouter()
        >>> context = SecurityContext()
        >>> tier = router.route("What is Python?", context)
        >>> print(tier)  # ProcessingTier.OFFLINE
    """

    # Temporal detection patterns
    TEMPORAL_PATTERNS: ClassVar[list[str]] = [
        r"\b(latest|recent|current|today|now|this\s+(?:week|month|year))\b",
        r"\b(breaking|news|update|happening)\b",
        r"\b20[2-9][0-9]\b",  # Years 2020-2099
        r"\b(yesterday|tomorrow|last\s+(?:week|month|year))\b",
        r"\b(upcoming|forthcoming|scheduled|planned)\b",
    ]

    # Domain indicator patterns
    DOMAIN_PATTERNS: ClassVar[dict[str, list[str]]] = {
        "medical": [
            r"\b(patient|diagnosis|treatment|symptom|disease)\b",
            r"\b(HIPAA|PHI|medical|clinical|healthcare)\b",
            r"\b(prescription|medication|dosage|therapy)\b",
        ],
        "legal": [
            r"\b(lawsuit|litigation|regulation|compliance|statute)\b",
            r"\b(contract|liability|jurisdiction|plaintiff|defendant)\b",
            r"\b(legal|attorney|lawyer|court|judge)\b",
        ],
        "technical": [
            r"\b(API|SDK|code|implementation|architecture)\b",
            r"\b(database|server|endpoint|microservice)\b",
            r"\b(algorithm|function|class|method|module)\b",
        ],
        "financial": [
            r"\b(market|stock|investment|trading|portfolio)\b",
            r"\b(revenue|profit|loss|ROI|valuation)\b",
            r"\b(SEC|FINRA|compliance|audit|quarterly)\b",
        ],
        "military": [
            r"\b(classified|tactical|strategic|operational)\b",
            r"\b(SECRET|CONFIDENTIAL|NOFORN|SCI)\b",
            r"\b(mission|deployment|reconnaissance|intel)\b",
        ],
    }

    # Complexity indicators
    COMPLEXITY_PATTERNS: ClassVar[dict[str, float]] = {
        r"\bif\b.*\bthen\b": 0.1,  # Conditional reasoning
        r"\bwhen\b.*\bwhile\b": 0.1,  # Nested conditions
        r"\band\b.*\bor\b": 0.05,  # Boolean logic
        r"[?].*[?]": 0.1,  # Multiple questions
        r"\bcompare\b|\bcontrast\b|\bversus\b|\bvs\b": 0.1,  # Comparison
        r"\bexplain\b.*\bwhy\b": 0.1,  # Causal reasoning
        r"\bimpact\b|\bconsequence\b|\bimplication\b": 0.1,  # Impact analysis
    }

    def __init__(self) -> None:
        """Initialize the query router with compiled patterns."""
        # Compile temporal patterns
        self._compiled_temporal: list[re.Pattern[str]] = [
            re.compile(p, re.IGNORECASE) for p in self.TEMPORAL_PATTERNS
        ]

        # Compile domain patterns
        self._compiled_domains: dict[str, list[re.Pattern[str]]] = {}
        for domain, patterns in self.DOMAIN_PATTERNS.items():
            self._compiled_domains[domain] = [re.compile(p, re.IGNORECASE) for p in patterns]

        # Compile complexity patterns
        self._compiled_complexity: dict[re.Pattern[str], float] = {
            re.compile(p, re.IGNORECASE): score for p, score in self.COMPLEXITY_PATTERNS.items()
        }

        logger.debug(
            "QueryRouter initialized: %d temporal patterns, %d domains, %d complexity patterns",
            len(self._compiled_temporal),
            len(self._compiled_domains),
            len(self._compiled_complexity),
        )

    def route(
        self,
        query: str,
        security_context: SecurityContext,
    ) -> ProcessingTier:
        """Determine the optimal processing tier for a query.

        Considers query complexity, temporal needs, domain, and security
        context to select the appropriate processing tier.

        Args:
            query: The query to route
            security_context: Security context for routing decisions

        Returns:
            Recommended ProcessingTier
        """
        logger.debug("Routing query: %s...", query[:50] if len(query) > 50 else query)

        # Security-based forced offline routing
        if security_context.requires_offline():
            logger.info(
                "Forcing OFFLINE tier due to security context: classified=%s, connectivity=%s",
                security_context.is_classified(),
                security_context.has_connectivity,
            )
            return ProcessingTier.OFFLINE

        # Calculate complexity
        complexity = self._calculate_complexity(query)

        # Detect temporal needs
        needs_temporal, _temporal_markers = self._detect_temporal_needs(query)

        # Identify domain
        domains = self._identify_domain(query)

        # Determine confidence (affected by ambiguity)
        confidence = self._calculate_confidence(query, complexity, domains)

        logger.debug(
            "Query analysis: complexity=%.2f, temporal=%s, domains=%s, confidence=%.2f",
            complexity,
            needs_temporal,
            domains,
            confidence,
        )

        # Tier selection logic
        if complexity <= 0.3 and not needs_temporal:
            tier = ProcessingTier.OFFLINE
        elif complexity > 0.7:
            tier = ProcessingTier.STRATEGIC
        else:
            tier = ProcessingTier.TACTICAL

        # Escalation check for low confidence
        if confidence < 0.5:
            tier = self._escalate_tier(tier)
            logger.debug("Escalated to %s due to low confidence (%.2f)", tier.value, confidence)

        logger.info("Routed query to tier: %s", tier.value)
        return tier

    def _calculate_complexity(self, query: str) -> float:
        """Calculate complexity score for a query.

        Scoring factors:
            - Base: 0.1 (gives OFFLINE tier a usable [0.1, 0.3] band; QG38-D6)
            - +0.1 for each sentence beyond the first
            - +0.1 for technical terms (based on patterns)
            - +0.1 for nested conditions
            - +0.1 for multi-part questions
            - Cap at 1.0

        Args:
            query: The query to analyze

        Returns:
            Complexity score from 0.0 to 1.0
        """
        # Base complexity (was 0.3, lowered to give OFFLINE tier usable range)
        complexity = 0.1

        # Sentence count (approximate by counting periods, question marks, exclamations)
        sentences = len(re.findall(r"[.!?]+", query))
        if sentences > 1:
            complexity += min(0.3, 0.1 * (sentences - 1))

        # Pattern-based complexity
        for pattern, score in self._compiled_complexity.items():
            if pattern.search(query):
                complexity += score

        # Word count factor (longer queries tend to be more complex)
        word_count = len(query.split())
        if word_count > 100:
            complexity += 0.2
        elif word_count > 50:
            complexity += 0.1

        # Cap at 1.0
        return min(1.0, complexity)

    def _detect_temporal_needs(self, query: str) -> tuple[bool, list[str]]:
        """Detect if query requires current/real-time information.

        Args:
            query: The query to analyze

        Returns:
            Tuple of (needs_current_info, list of detected temporal markers)
        """
        markers: list[str] = []

        for pattern in self._compiled_temporal:
            matches = pattern.findall(query)
            if matches:
                # Flatten if nested groups
                for match in matches:
                    if isinstance(match, tuple):
                        markers.extend([m for m in match if m])
                    else:
                        markers.append(match)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_markers: list[str] = []
        for marker in markers:
            lower_marker = marker.lower()
            if lower_marker not in seen:
                seen.add(lower_marker)
                unique_markers.append(marker)

        return len(unique_markers) > 0, unique_markers

    def _identify_domain(self, query: str) -> list[str]:
        """Identify domain indicators in the query.

        Args:
            query: The query to analyze

        Returns:
            List of detected domain names
        """
        detected_domains: list[str] = []

        for domain, patterns in self._compiled_domains.items():
            for pattern in patterns:
                if pattern.search(query):
                    if domain not in detected_domains:
                        detected_domains.append(domain)
                    break  # One match per domain is sufficient

        return detected_domains

    def _calculate_confidence(
        self,
        query: str,
        complexity: float,
        domains: list[str],
    ) -> float:
        """Calculate analysis confidence.

        Confidence is reduced by:
            - High complexity (uncertain routing)
            - Multiple domains (cross-domain queries are harder)
            - Short queries (less context)
            - Ambiguous wording

        Args:
            query: The query to analyze
            complexity: Calculated complexity score
            domains: Detected domains

        Returns:
            Confidence score from 0.0 to 1.0
        """
        confidence = 0.9  # Start high

        # Reduce for high complexity
        if complexity > 0.7:
            confidence -= 0.2

        # Reduce for multiple domains (cross-domain queries)
        if len(domains) > 1:
            confidence -= 0.1 * (len(domains) - 1)

        # Reduce for very short queries (less context)
        word_count = len(query.split())
        if word_count < 5:
            confidence -= 0.2

        # Reduce for ambiguous wording
        ambiguous_terms = ["might", "maybe", "possibly", "could be", "not sure"]
        for term in ambiguous_terms:
            if term in query.lower():
                confidence -= 0.1
                break

        return max(0.0, min(1.0, confidence))

    def _escalate_tier(self, current_tier: ProcessingTier) -> ProcessingTier:
        """Escalate to the next higher processing tier.

        Args:
            current_tier: Current processing tier

        Returns:
            Next higher tier, or STRATEGIC if already at highest
        """
        if current_tier == ProcessingTier.OFFLINE:
            return ProcessingTier.TACTICAL
        elif current_tier == ProcessingTier.TACTICAL:
            return ProcessingTier.STRATEGIC
        else:
            return ProcessingTier.STRATEGIC  # Already at highest


# =============================================================================
# MAIN ANALYZER
# =============================================================================


class QueryAnalyzer:
    """Main query analyzer for AIPEA prompt engine integration.

    Provides comprehensive query analysis including complexity scoring,
    temporal detection, domain identification, and search strategy
    recommendation.

    Example:
        >>> analyzer = QueryAnalyzer()
        >>> analysis = analyzer.analyze("What are the latest Python features?")
        >>> print(analysis.complexity)  # 0.4
        >>> print(analysis.needs_current_info)  # True
        >>> print(analysis.search_strategy)  # SearchStrategy.QUICK_FACTS
    """

    # Query type patterns (more comprehensive than QueryRouter)
    QUERY_TYPE_PATTERNS: ClassVar[dict[QueryType, list[str]]] = {
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

    def __init__(self) -> None:
        """Initialize the query analyzer."""
        self._router = QueryRouter()
        self._scanner = SecurityScanner()

        # Compile query type patterns
        self._compiled_query_types: dict[QueryType, list[re.Pattern[str]]] = {}
        for qtype, patterns in self.QUERY_TYPE_PATTERNS.items():
            self._compiled_query_types[qtype] = [re.compile(p, re.IGNORECASE) for p in patterns]

        # Pre-compile entity detection patterns (avoid recompilation per call)
        self._cap_pattern = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")
        self._tech_pattern = re.compile(
            r"\b(Python|JavaScript|TypeScript|React|Angular|Vue|Django|"
            r"FastAPI|PostgreSQL|MongoDB|Redis|Docker|Kubernetes|AWS|"
            r"Azure|GCP|OpenAI|Anthropic|Google|Microsoft|Apple)\b",
            re.IGNORECASE,
        )

        logger.debug(
            "QueryAnalyzer initialized with %d query types", len(self._compiled_query_types)
        )

    def analyze(
        self,
        query: str,
        security_context: SecurityContext | None = None,
    ) -> QueryAnalysis:
        """Analyze a query for routing and enhancement decisions.

        Performs comprehensive analysis including:
            - Query type classification
            - Complexity scoring
            - Temporal needs detection
            - Domain identification
            - Search strategy recommendation
            - Tier suggestion

        Args:
            query: The query to analyze
            security_context: Optional security context (defaults to general)

        Returns:
            QueryAnalysis with all analysis results
        """
        logger.debug("Analyzing query: %s...", query[:50] if len(query) > 50 else query)

        # Use default security context if not provided
        if security_context is None:
            security_context = SecurityContext()

        # Classify query type
        query_type = self._classify_query_type(query)

        # Calculate complexity
        complexity = self._router._calculate_complexity(query)

        # Detect temporal needs
        needs_temporal, temporal_markers = self._router._detect_temporal_needs(query)

        # Identify domains
        domains = self._router._identify_domain(query)

        # Calculate confidence
        confidence = self._router._calculate_confidence(query, complexity, domains)

        # Detect entities (simplified)
        entities = self._detect_entities(query)

        # Calculate ambiguity score
        ambiguity = self._calculate_ambiguity(query)

        # Create initial analysis
        analysis = QueryAnalysis(
            query=query,
            query_type=query_type,
            complexity=complexity,
            confidence=confidence,
            needs_current_info=needs_temporal,
            temporal_markers=temporal_markers,
            domain_indicators=domains,
            ambiguity_score=ambiguity,
            detected_entities=entities,
        )

        # Determine search necessity and strategy
        needs_search = self._determine_search_necessity(analysis)
        if needs_search:
            analysis.search_strategy = self._determine_search_strategy(analysis)
        else:
            analysis.search_strategy = SearchStrategy.NONE

        # Suggest processing tier
        analysis.suggested_tier = self._router.route(query, security_context)

        logger.info(
            "Query analysis complete: type=%s, complexity=%.2f, tier=%s, search=%s",
            analysis.query_type.value,
            analysis.complexity,
            analysis.suggested_tier.value if analysis.suggested_tier else "none",
            analysis.search_strategy.name,
        )

        return analysis

    def _classify_query_type(self, query: str) -> QueryType:
        """Classify query into a type using pattern matching.

        Args:
            query: The query to classify

        Returns:
            Best matching QueryType, or UNKNOWN if no patterns match
        """
        scores: dict[QueryType, int] = {}

        for qtype, patterns in self._compiled_query_types.items():
            score = sum(1 for p in patterns if p.search(query))
            if score > 0:
                scores[qtype] = score

        if not scores:
            return QueryType.UNKNOWN

        return max(scores.keys(), key=lambda k: scores[k])

    def _detect_entities(self, query: str) -> list[str]:
        """Detect named entities in query (simplified implementation).

        Uses basic patterns to detect:
            - Capitalized multi-word phrases
            - Technology names
            - Company/product names

        Args:
            query: The query to analyze

        Returns:
            List of detected entity names
        """
        entities: list[str] = []

        # Detect capitalized phrases (potential proper nouns)
        matches = self._cap_pattern.findall(query)
        entities.extend(matches)

        # Detect known technology patterns
        tech_matches = self._tech_pattern.findall(query)
        entities.extend(tech_matches)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_entities: list[str] = []
        for entity in entities:
            if entity.lower() not in seen:
                seen.add(entity.lower())
                unique_entities.append(entity)

        return unique_entities

    def _calculate_ambiguity(self, query: str) -> float:
        """Calculate ambiguity score for a query.

        Higher scores indicate more ambiguous queries.

        Args:
            query: The query to analyze

        Returns:
            Ambiguity score from 0.0 to 1.0
        """
        ambiguity = 0.0

        # Ambiguous terms increase score
        # Ordered longest-first so "it depends" is matched before "depends",
        # preventing double-counting on overlapping substrings.
        ambiguous_terms = [
            "it depends",
            "not sure",
            "kind of",
            "sort of",
            "possibly",
            "uncertain",
            "depends",
            "perhaps",
            "might",
            "maybe",
            "could",
        ]
        query_lower = query.lower()
        matched_spans: list[tuple[int, int]] = []
        for term in ambiguous_terms:
            start = 0
            while True:
                idx = query_lower.find(term, start)
                if idx == -1:
                    break
                end = idx + len(term)
                # Only count if this span doesn't overlap with an already-matched span
                if not any(s < end and e > idx for s, e in matched_spans):
                    ambiguity += 0.15
                    matched_spans.append((idx, end))
                start = end

        # Very short queries are ambiguous
        word_count = len(query.split())
        if word_count < 3:
            ambiguity += 0.3
        elif word_count < 5:
            ambiguity += 0.1

        # Queries without question marks or clear intent
        if "?" not in query and not any(
            kw in query_lower for kw in ["how", "what", "why", "when", "where", "who", "explain"]
        ):
            ambiguity += 0.1

        return min(1.0, ambiguity)

    def _determine_search_necessity(self, analysis: QueryAnalysis) -> bool:
        """Determine if search is necessary for the query.

        Search is needed when:
            - Query requires current information
            - Query involves factual claims that need verification
            - Query complexity suggests multi-source research

        Args:
            analysis: The query analysis

        Returns:
            True if search is recommended
        """
        # Temporal needs always require search
        if analysis.needs_current_info:
            return True

        # High complexity queries benefit from search
        if analysis.complexity > 0.6:
            return True

        # Research and analytical queries often need search
        if analysis.query_type in (QueryType.RESEARCH, QueryType.ANALYTICAL):
            return True

        # Domain-specific queries may need specialized search
        specialized_domains = {"financial", "legal", "medical"}
        return any(d in specialized_domains for d in analysis.domain_indicators)

    def _determine_search_strategy(self, analysis: QueryAnalysis) -> SearchStrategy:
        """Determine the appropriate search strategy.

        Strategy selection:
            - QUICK_FACTS: Simple factual query, low complexity
            - DEEP_RESEARCH: Complex query, research type
            - MULTI_SOURCE: Comparative or verification needed

        Args:
            analysis: The query analysis

        Returns:
            Recommended SearchStrategy
        """
        # Multi-source for comparative queries
        comparative_terms = ["compare", "versus", "vs", "difference", "better", "best"]
        query_lower = analysis.query.lower()
        if any(term in query_lower for term in comparative_terms):
            return SearchStrategy.MULTI_SOURCE

        # Multi-source for verification queries
        verification_terms = ["verify", "confirm", "fact-check", "true", "accurate"]
        if any(term in query_lower for term in verification_terms):
            return SearchStrategy.MULTI_SOURCE

        # Deep research for complex research queries
        if analysis.query_type == QueryType.RESEARCH and analysis.complexity > 0.5:
            return SearchStrategy.DEEP_RESEARCH

        # Deep research for high complexity
        if analysis.complexity > 0.7:
            return SearchStrategy.DEEP_RESEARCH

        # Default to quick facts
        return SearchStrategy.QUICK_FACTS

    def suggest_enhancements(
        self,
        query: str,
        analysis: QueryAnalysis,
    ) -> list[str]:
        """Suggest enhancements to improve query quality.

        Provides actionable suggestions for:
            - Adding specificity
            - Clarifying ambiguous terms
            - Providing context
            - Scoping the query

        Args:
            query: The original query
            analysis: The query analysis

        Returns:
            List of enhancement suggestions
        """
        suggestions: list[str] = []

        # High ambiguity suggestions
        if analysis.ambiguity_score > 0.5:
            suggestions.append("Consider adding more specific details to reduce ambiguity.")

        # Short query suggestions
        word_count = len(query.split())
        if word_count < 5:
            suggestions.append("Adding more context would help provide a more accurate response.")

        # Domain-specific suggestions
        if len(analysis.domain_indicators) > 1:
            suggestions.append(
                "Your query spans multiple domains. Consider focusing on one aspect at a time."
            )

        # Complexity suggestions
        if analysis.complexity > 0.8:
            suggestions.append(
                "This is a complex query. Consider breaking it into smaller, focused questions."
            )

        # Low confidence suggestions
        if analysis.confidence < 0.5:
            suggestions.append(
                "The query intent is unclear. Try rephrasing with more specific language."
            )

        # Technical query suggestions
        if analysis.query_type == QueryType.TECHNICAL and not any(
            entity.lower() in ["python", "javascript", "typescript", "java"]
            for entity in analysis.detected_entities
        ):
            suggestions.append(
                "Specifying the programming language or technology would help provide "
                "more relevant code examples."
            )

        return suggestions


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def analyze_query(
    query: str,
    security_context: SecurityContext | None = None,
) -> QueryAnalysis:
    """Convenience function to analyze a query.

    Creates a QueryAnalyzer instance and performs analysis.

    Args:
        query: The query to analyze
        security_context: Optional security context

    Returns:
        QueryAnalysis with all analysis results
    """
    analyzer = QueryAnalyzer()
    return analyzer.analyze(query, security_context)


def route_query(
    query: str,
    security_context: SecurityContext | None = None,
) -> ProcessingTier:
    """Convenience function to route a query to appropriate tier.

    Args:
        query: The query to route
        security_context: Optional security context

    Returns:
        Recommended ProcessingTier
    """
    if security_context is None:
        security_context = SecurityContext()

    router = QueryRouter()
    return router.route(query, security_context)


# Module-level singleton for easy access
_query_analyzer_instance: QueryAnalyzer | None = None
_query_analyzer_lock = threading.Lock()


def get_query_analyzer() -> QueryAnalyzer:
    """Get or create the default query analyzer singleton.

    Thread-safe via double-checked locking pattern.

    Returns:
        The default QueryAnalyzer instance
    """
    global _query_analyzer_instance
    if _query_analyzer_instance is None:
        with _query_analyzer_lock:
            if _query_analyzer_instance is None:
                _query_analyzer_instance = QueryAnalyzer()
    return _query_analyzer_instance


# =============================================================================
# EXPORTS
# =============================================================================


__all__ = [
    "QueryAnalyzer",
    "QueryRouter",
    "analyze_query",
    "get_query_analyzer",
    "route_query",
]
