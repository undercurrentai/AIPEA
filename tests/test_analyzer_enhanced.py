"""Tests for aipea.analyzer — QueryAnalyzer comprehensive analysis.

Tests the QueryAnalyzer class which provides:
- Query type classification
- Complexity scoring via QueryRouter
- Temporal needs detection
- Domain identification
- Search strategy recommendation
- Enhancement suggestions
- Singleton access
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from aipea._types import ProcessingTier, QueryType, SearchStrategy
from aipea.analyzer import QueryAnalyzer, get_query_analyzer
from aipea.models import QueryAnalysis
from aipea.security import SecurityContext

pytestmark = [pytest.mark.unit]


# =============================================================================
# QUERY TYPE CLASSIFICATION
# =============================================================================


class TestQueryTypeClassification:
    """Tests for QueryAnalyzer._classify_query_type()."""

    @pytest.fixture
    def analyzer(self) -> QueryAnalyzer:
        return QueryAnalyzer()

    def test_technical_query(self, analyzer: QueryAnalyzer) -> None:
        assert analyzer._classify_query_type("implement a Python function") == QueryType.TECHNICAL

    def test_research_query(self, analyzer: QueryAnalyzer) -> None:
        assert (
            analyzer._classify_query_type("research study on neural networks") == QueryType.RESEARCH
        )

    def test_creative_query(self, analyzer: QueryAnalyzer) -> None:
        assert (
            analyzer._classify_query_type("write a creative story about AI") == QueryType.CREATIVE
        )

    def test_analytical_query(self, analyzer: QueryAnalyzer) -> None:
        assert (
            analyzer._classify_query_type("analyze and evaluate performance metrics")
            == QueryType.ANALYTICAL
        )

    def test_operational_query(self, analyzer: QueryAnalyzer) -> None:
        assert (
            analyzer._classify_query_type("how to install Docker step by step")
            == QueryType.OPERATIONAL
        )

    def test_strategic_query(self, analyzer: QueryAnalyzer) -> None:
        assert (
            analyzer._classify_query_type("long-term strategy plan for roadmap")
            == QueryType.STRATEGIC
        )

    def test_unknown_query(self, analyzer: QueryAnalyzer) -> None:
        assert analyzer._classify_query_type("hello world") == QueryType.UNKNOWN


# =============================================================================
# FULL ANALYSIS
# =============================================================================


class TestAnalyze:
    """Tests for QueryAnalyzer.analyze()."""

    @pytest.fixture
    def analyzer(self) -> QueryAnalyzer:
        return QueryAnalyzer()

    def test_returns_query_analysis(self, analyzer: QueryAnalyzer) -> None:
        result = analyzer.analyze("What are the latest Python features?")
        assert isinstance(result, QueryAnalysis)
        assert result.query == "What are the latest Python features?"

    def test_temporal_query_needs_current_info(self, analyzer: QueryAnalyzer) -> None:
        result = analyzer.analyze("latest AI developments 2025")
        assert result.needs_current_info is True

    def test_simple_query_no_current_info(self, analyzer: QueryAnalyzer) -> None:
        result = analyzer.analyze("hello")
        assert result.needs_current_info is False

    def test_complexity_is_bounded(self, analyzer: QueryAnalyzer) -> None:
        result = analyzer.analyze("word " * 200)
        assert 0.0 <= result.complexity <= 1.0

    def test_confidence_is_bounded(self, analyzer: QueryAnalyzer) -> None:
        result = analyzer.analyze("explain machine learning algorithms in detail")
        assert 0.0 <= result.confidence <= 1.0

    def test_suggested_tier_is_set(self, analyzer: QueryAnalyzer) -> None:
        result = analyzer.analyze("hello")
        assert result.suggested_tier is not None
        assert isinstance(result.suggested_tier, ProcessingTier)

    def test_search_strategy_set_for_temporal(self, analyzer: QueryAnalyzer) -> None:
        result = analyzer.analyze("latest news about quantum computing")
        assert result.search_strategy != SearchStrategy.NONE

    def test_search_strategy_none_for_simple(self, analyzer: QueryAnalyzer) -> None:
        result = analyzer.analyze("hello")
        assert result.search_strategy == SearchStrategy.NONE

    def test_security_context_defaults_when_none(self, analyzer: QueryAnalyzer) -> None:
        """Passing security_context=None should not error."""
        result = analyzer.analyze("test query", security_context=None)
        assert isinstance(result, QueryAnalysis)

    def test_security_context_passed_through(self, analyzer: QueryAnalyzer) -> None:
        ctx = SecurityContext()
        result = analyzer.analyze("test query", security_context=ctx)
        assert isinstance(result, QueryAnalysis)

    def test_domain_indicators_populated(self, analyzer: QueryAnalyzer) -> None:
        result = analyzer.analyze("explain quantum computing applications")
        assert isinstance(result.domain_indicators, list)

    def test_detected_entities_populated(self, analyzer: QueryAnalyzer) -> None:
        result = analyzer.analyze("How does Python compare to JavaScript?")
        assert isinstance(result.detected_entities, list)
        assert len(result.detected_entities) > 0


# =============================================================================
# SEARCH NECESSITY
# =============================================================================


class TestSearchNecessity:
    """Tests for QueryAnalyzer._determine_search_necessity()."""

    @pytest.fixture
    def analyzer(self) -> QueryAnalyzer:
        return QueryAnalyzer()

    def _make_analysis(
        self,
        needs_current: bool = False,
        complexity: float = 0.3,
        query_type: QueryType = QueryType.UNKNOWN,
        domains: list[str] | None = None,
    ) -> QueryAnalysis:
        return QueryAnalysis(
            query="test",
            query_type=query_type,
            complexity=complexity,
            confidence=0.8,
            needs_current_info=needs_current,
            domain_indicators=domains or [],
        )

    def test_temporal_needs_require_search(self, analyzer: QueryAnalyzer) -> None:
        analysis = self._make_analysis(needs_current=True)
        assert analyzer._determine_search_necessity(analysis) is True

    def test_high_complexity_requires_search(self, analyzer: QueryAnalyzer) -> None:
        analysis = self._make_analysis(complexity=0.7)
        assert analyzer._determine_search_necessity(analysis) is True

    def test_research_type_requires_search(self, analyzer: QueryAnalyzer) -> None:
        analysis = self._make_analysis(query_type=QueryType.RESEARCH)
        assert analyzer._determine_search_necessity(analysis) is True

    def test_analytical_type_requires_search(self, analyzer: QueryAnalyzer) -> None:
        analysis = self._make_analysis(query_type=QueryType.ANALYTICAL)
        assert analyzer._determine_search_necessity(analysis) is True

    def test_specialized_domain_requires_search(self, analyzer: QueryAnalyzer) -> None:
        analysis = self._make_analysis(domains=["financial"])
        assert analyzer._determine_search_necessity(analysis) is True

    def test_simple_no_temporal_no_search(self, analyzer: QueryAnalyzer) -> None:
        analysis = self._make_analysis(complexity=0.2, query_type=QueryType.UNKNOWN)
        assert analyzer._determine_search_necessity(analysis) is False


# =============================================================================
# SEARCH STRATEGY
# =============================================================================


class TestSearchStrategyDetermination:
    """Tests for QueryAnalyzer._determine_search_strategy()."""

    @pytest.fixture
    def analyzer(self) -> QueryAnalyzer:
        return QueryAnalyzer()

    def _make_analysis(
        self,
        query: str = "test",
        complexity: float = 0.5,
        query_type: QueryType = QueryType.UNKNOWN,
    ) -> QueryAnalysis:
        return QueryAnalysis(
            query=query,
            query_type=query_type,
            complexity=complexity,
            confidence=0.8,
            needs_current_info=False,
        )

    def test_comparative_query_multi_source(self, analyzer: QueryAnalyzer) -> None:
        analysis = self._make_analysis(query="compare Python vs JavaScript")
        assert analyzer._determine_search_strategy(analysis) == SearchStrategy.MULTI_SOURCE

    def test_verification_query_multi_source(self, analyzer: QueryAnalyzer) -> None:
        analysis = self._make_analysis(query="verify this claim is accurate")
        assert analyzer._determine_search_strategy(analysis) == SearchStrategy.MULTI_SOURCE

    def test_complex_research_deep(self, analyzer: QueryAnalyzer) -> None:
        analysis = self._make_analysis(
            query="neural network study",
            complexity=0.6,
            query_type=QueryType.RESEARCH,
        )
        assert analyzer._determine_search_strategy(analysis) == SearchStrategy.DEEP_RESEARCH

    def test_high_complexity_deep(self, analyzer: QueryAnalyzer) -> None:
        analysis = self._make_analysis(complexity=0.8)
        assert analyzer._determine_search_strategy(analysis) == SearchStrategy.DEEP_RESEARCH

    def test_default_quick_facts(self, analyzer: QueryAnalyzer) -> None:
        analysis = self._make_analysis(complexity=0.3)
        assert analyzer._determine_search_strategy(analysis) == SearchStrategy.QUICK_FACTS


# =============================================================================
# AMBIGUITY SCORING
# =============================================================================


class TestAmbiguity:
    """Tests for QueryAnalyzer._calculate_ambiguity()."""

    @pytest.fixture
    def analyzer(self) -> QueryAnalyzer:
        return QueryAnalyzer()

    def test_short_query_high_ambiguity(self, analyzer: QueryAnalyzer) -> None:
        score = analyzer._calculate_ambiguity("hi")
        assert score >= 0.3

    def test_clear_query_low_ambiguity(self, analyzer: QueryAnalyzer) -> None:
        score = analyzer._calculate_ambiguity("How do I install Python 3.12 on Ubuntu?")
        assert score == 0.0

    def test_ambiguous_terms_increase_score(self, analyzer: QueryAnalyzer) -> None:
        score = analyzer._calculate_ambiguity("maybe it depends on possibly uncertain factors")
        assert score > 0.3

    def test_capped_at_one(self, analyzer: QueryAnalyzer) -> None:
        score = analyzer._calculate_ambiguity("maybe perhaps possibly uncertain it depends")
        assert score <= 1.0

    def test_no_question_mark_adds_ambiguity(self, analyzer: QueryAnalyzer) -> None:
        """Queries without ? and without question words are more ambiguous."""
        score = analyzer._calculate_ambiguity("large complex statement about many topics at once")
        assert score >= 0.1


# =============================================================================
# ENTITY DETECTION
# =============================================================================


class TestEntityDetection:
    """Tests for QueryAnalyzer._detect_entities()."""

    @pytest.fixture
    def analyzer(self) -> QueryAnalyzer:
        return QueryAnalyzer()

    def test_technology_names(self, analyzer: QueryAnalyzer) -> None:
        entities = analyzer._detect_entities("Compare Python and JavaScript performance")
        assert "Python" in entities
        assert "JavaScript" in entities

    def test_capitalized_phrases(self, analyzer: QueryAnalyzer) -> None:
        entities = analyzer._detect_entities("What is Machine Learning used for?")
        assert "Machine Learning" in entities

    def test_deduplicated(self, analyzer: QueryAnalyzer) -> None:
        entities = analyzer._detect_entities("Python uses Python extensively")
        assert entities.count("Python") == 1

    def test_empty_query(self, analyzer: QueryAnalyzer) -> None:
        entities = analyzer._detect_entities("")
        assert entities == []


# =============================================================================
# SUGGEST ENHANCEMENTS
# =============================================================================


class TestSuggestEnhancements:
    """Tests for QueryAnalyzer.suggest_enhancements()."""

    @pytest.fixture
    def analyzer(self) -> QueryAnalyzer:
        return QueryAnalyzer()

    def _make_analysis(self, **kwargs) -> QueryAnalysis:  # type: ignore[no-untyped-def]
        defaults: dict = {
            "query": "test",
            "query_type": QueryType.UNKNOWN,
            "complexity": 0.5,
            "confidence": 0.8,
            "needs_current_info": False,
            "ambiguity_score": 0.0,
        }
        defaults.update(kwargs)
        return QueryAnalysis(**defaults)

    def test_high_ambiguity_suggestion(self, analyzer: QueryAnalyzer) -> None:
        analysis = self._make_analysis(ambiguity_score=0.6)
        suggestions = analyzer.suggest_enhancements("test", analysis)
        assert any("ambiguity" in s.lower() for s in suggestions)

    def test_short_query_suggestion(self, analyzer: QueryAnalyzer) -> None:
        analysis = self._make_analysis()
        suggestions = analyzer.suggest_enhancements("hi", analysis)
        assert any("context" in s.lower() for s in suggestions)

    def test_complex_query_suggestion(self, analyzer: QueryAnalyzer) -> None:
        analysis = self._make_analysis(complexity=0.9)
        suggestions = analyzer.suggest_enhancements("very complex query", analysis)
        assert any("complex" in s.lower() for s in suggestions)

    def test_low_confidence_suggestion(self, analyzer: QueryAnalyzer) -> None:
        analysis = self._make_analysis(confidence=0.3)
        suggestions = analyzer.suggest_enhancements("vague query", analysis)
        assert any("unclear" in s.lower() for s in suggestions)


# =============================================================================
# SINGLETON
# =============================================================================


class TestSingleton:
    """Tests for get_query_analyzer() singleton."""

    def test_returns_same_instance(self) -> None:
        a1 = get_query_analyzer()
        a2 = get_query_analyzer()
        assert a1 is a2
        assert isinstance(a1, QueryAnalyzer)

    def test_analyze_works_on_singleton(self) -> None:
        analyzer = get_query_analyzer()
        result = analyzer.analyze("test query")
        assert isinstance(result, QueryAnalysis)


# =============================================================================
# PERFORMANCE
# =============================================================================


class TestPerformance:
    """Tests for analysis performance."""

    @pytest.fixture
    def analyzer(self) -> QueryAnalyzer:
        return QueryAnalyzer()

    def test_simple_analysis_performance(self, analyzer: QueryAnalyzer) -> None:
        queries = ["what is AI", "2 + 2", "hello world"] * 100
        start = time.time()
        for q in queries:
            analyzer.analyze(q)
        elapsed = time.time() - start
        assert elapsed < 3.0, "300 simple analyses should complete within 3 seconds"

    def test_complex_analysis_performance(self, analyzer: QueryAnalyzer) -> None:
        queries = [
            "latest comprehensive research study on machine learning developments",
            "breaking news about quantum computing breakthroughs and implications",
        ] * 50
        start = time.time()
        for q in queries:
            analyzer.analyze(q)
        elapsed = time.time() - start
        assert elapsed < 5.0, "100 complex analyses should complete within 5 seconds"


# =============================================================================
# QUERY ANALYSIS MODEL
# =============================================================================


class TestQueryAnalysisModel:
    """Tests for QueryAnalysis dataclass."""

    def test_to_dict(self) -> None:
        analysis = QueryAnalysis(
            query="test",
            query_type=QueryType.TECHNICAL,
            complexity=0.5,
            confidence=0.8,
            needs_current_info=True,
            temporal_markers=["latest"],
            domain_indicators=["tech"],
            suggested_tier=ProcessingTier.TACTICAL,
            search_strategy=SearchStrategy.QUICK_FACTS,
        )
        d = analysis.to_dict()
        assert d["query"] == "test"
        assert d["query_type"] == "technical"
        assert d["complexity"] == 0.5
        assert d["suggested_tier"] == "tactical"
        assert d["search_strategy"] == "QUICK_FACTS"

    def test_complexity_clamped(self) -> None:
        analysis = QueryAnalysis(
            query="test",
            query_type=QueryType.UNKNOWN,
            complexity=1.5,
            confidence=0.5,
            needs_current_info=False,
        )
        assert analysis.complexity == 1.0

    def test_confidence_clamped(self) -> None:
        analysis = QueryAnalysis(
            query="test",
            query_type=QueryType.UNKNOWN,
            complexity=0.5,
            confidence=-0.1,
            needs_current_info=False,
        )
        assert analysis.confidence == 0.0


# =============================================================================
# LOGGING
# =============================================================================


class TestLogging:
    """Tests for analyzer logging behavior."""

    @pytest.fixture
    def analyzer(self) -> QueryAnalyzer:
        return QueryAnalyzer()

    def test_analyze_logs_completion(self, analyzer: QueryAnalyzer) -> None:
        with patch("aipea.analyzer.logger") as mock_logger:
            analyzer.analyze("latest AI news 2025")
            mock_logger.info.assert_called()
