"""Tests for aipea.strategies — named enhancement strategies and technique functions."""

from __future__ import annotations

import pytest

from aipea._types import QueryType
from aipea.strategies import (
    STRATEGY_REGISTRY,
    TECHNIQUE_FUNCTIONS,
    EnhancementStrategy,
    ScoredEnhancement,
    StrategyResult,
    apply_strategy,
    apply_strategy_ranked,
    constraint_identification,
    hypothesis_clarification,
    metric_definition,
    objective_hierarchy_construction,
    select_strategy_for_query_type,
    specification_extraction,
    task_decomposition,
)

# =============================================================================
# TECHNIQUE FUNCTION TESTS
# =============================================================================


class TestSpecificationExtraction:
    @pytest.mark.unit
    def test_comparison_query(self) -> None:
        result = specification_extraction("Compare Python vs JavaScript for web dev")
        assert "comparison" in result.lower()

    @pytest.mark.unit
    def test_evaluation_query(self) -> None:
        result = specification_extraction("Which database should I use?")
        assert "evaluation" in result.lower() or "trade-off" in result.lower()

    @pytest.mark.unit
    def test_implementation_query(self) -> None:
        result = specification_extraction("How to build a REST API")
        assert "implementation" in result.lower() or "step-by-step" in result.lower()

    @pytest.mark.unit
    def test_explanation_query(self) -> None:
        result = specification_extraction("Explain the GIL in Python")
        assert "explanation" in result.lower()

    @pytest.mark.unit
    def test_no_match(self) -> None:
        result = specification_extraction("Hello")
        assert result == ""


class TestConstraintIdentification:
    @pytest.mark.unit
    def test_time_constraint(self) -> None:
        result = constraint_identification("I need this done quickly by tomorrow")
        assert "time" in result.lower()

    @pytest.mark.unit
    def test_resource_constraint(self) -> None:
        result = constraint_identification("Find a free lightweight solution")
        assert "resource" in result.lower()

    @pytest.mark.unit
    def test_technology_constraint(self) -> None:
        result = constraint_identification("Build this in Python with Django")
        assert "python" in result.lower() or "django" in result.lower()

    @pytest.mark.unit
    def test_no_constraints(self) -> None:
        result = constraint_identification("Hello world")
        assert result == ""


class TestHypothesisClarification:
    @pytest.mark.unit
    def test_vague_qualifier(self) -> None:
        result = hypothesis_clarification("Is React better for large apps?")
        assert "metric" in result.lower() or "quality" in result.lower()

    @pytest.mark.unit
    def test_generalization(self) -> None:
        result = hypothesis_clarification("Everyone always uses Docker")
        assert "edge case" in result.lower() or "exception" in result.lower()

    @pytest.mark.unit
    def test_no_clarification(self) -> None:
        result = hypothesis_clarification("List the Python standard library modules")
        assert result == ""


class TestMetricDefinition:
    @pytest.mark.unit
    def test_performance_query(self) -> None:
        result = metric_definition("How to optimize database performance?")
        assert "metric" in result.lower()

    @pytest.mark.unit
    def test_quality_query(self) -> None:
        result = metric_definition("Make this code more reliable and robust")
        assert "metric" in result.lower()

    @pytest.mark.unit
    def test_no_metrics(self) -> None:
        result = metric_definition("Hello there")
        assert result == ""


class TestTaskDecomposition:
    @pytest.mark.unit
    def test_multi_concern_query(self) -> None:
        result = task_decomposition("Build an API, add authentication, and implement caching")
        assert "sub-task" in result.lower()

    @pytest.mark.unit
    def test_simple_query(self) -> None:
        result = task_decomposition("What is Python?")
        assert result == ""


class TestObjectiveHierarchy:
    @pytest.mark.unit
    def test_strategic_query(self) -> None:
        result = objective_hierarchy_construction(
            "Define a strategy and roadmap for our platform architecture"
        )
        assert "objective" in result.lower()

    @pytest.mark.unit
    def test_risk_query(self) -> None:
        result = objective_hierarchy_construction("Identify the risks and mitigation strategies")
        assert "risk" in result.lower() or "mitigation" in result.lower()

    @pytest.mark.unit
    def test_non_strategic_query(self) -> None:
        result = objective_hierarchy_construction("What time is it?")
        assert result == ""


# =============================================================================
# STRATEGY REGISTRY TESTS
# =============================================================================


class TestStrategyRegistry:
    @pytest.mark.unit
    def test_all_strategies_exist(self) -> None:
        expected = {"general", "technical", "research", "creative", "analytical", "strategic"}
        assert set(STRATEGY_REGISTRY.keys()) == expected

    @pytest.mark.unit
    def test_strategy_dataclass(self) -> None:
        s = EnhancementStrategy(name="test", techniques=["a", "b"])
        assert s.name == "test"
        assert s.techniques == ["a", "b"]
        assert s.context_requirements == []

    @pytest.mark.unit
    def test_each_strategy_has_valid_techniques(self) -> None:
        for name, strategy in STRATEGY_REGISTRY.items():
            for tech in strategy.techniques:
                assert tech in TECHNIQUE_FUNCTIONS, (
                    f"Strategy '{name}' references unknown technique '{tech}'"
                )


# =============================================================================
# APPLY STRATEGY TESTS
# =============================================================================


class TestApplyStrategy:
    @pytest.mark.unit
    def test_general_strategy(self) -> None:
        result = apply_strategy("Compare Python vs Go for APIs", strategy_name="general")
        assert isinstance(result, str)
        assert len(result) > 0  # Should find specification_extraction match

    @pytest.mark.unit
    def test_technical_strategy(self) -> None:
        result = apply_strategy("How to optimize database performance?", strategy_name="technical")
        assert isinstance(result, str)

    @pytest.mark.unit
    def test_unknown_strategy_falls_back(self) -> None:
        result = apply_strategy("Hello", strategy_name="nonexistent")
        assert isinstance(result, str)  # Falls back to general

    @pytest.mark.unit
    def test_none_strategy_uses_general(self) -> None:
        result = apply_strategy("Compare X vs Y")
        assert isinstance(result, str)

    @pytest.mark.unit
    def test_no_output_for_simple_query(self) -> None:
        result = apply_strategy("Hi", strategy_name="general")
        assert result == ""


# =============================================================================
# STRATEGY SELECTION TESTS
# =============================================================================


class TestSelectStrategy:
    @pytest.mark.unit
    def test_technical_type(self) -> None:
        assert select_strategy_for_query_type(QueryType.TECHNICAL) == "technical"

    @pytest.mark.unit
    def test_research_type(self) -> None:
        assert select_strategy_for_query_type(QueryType.RESEARCH) == "research"

    @pytest.mark.unit
    def test_unknown_type(self) -> None:
        assert select_strategy_for_query_type(QueryType.UNKNOWN) == "general"

    @pytest.mark.unit
    def test_all_query_types_mapped(self) -> None:
        for qt in QueryType:
            result = select_strategy_for_query_type(qt)
            assert result in STRATEGY_REGISTRY


# =============================================================================
# REGRESSION TESTS (bug-hunt wave 14)
# =============================================================================


class TestTaskDecompositionRegression:
    """Regression: counting pattern included 'plus'/'as well as' but split did not."""

    @pytest.mark.unit
    def test_plus_conjunction_splits_correctly(self) -> None:
        result = task_decomposition("Build an API plus deploy it plus test it")
        assert "sub-task" in result.lower()
        # Must produce multiple sub-tasks, not just one
        assert result.count("Sub-task") >= 2

    @pytest.mark.unit
    def test_as_well_as_conjunction_splits(self) -> None:
        result = task_decomposition(
            "Design the schema as well as build the API as well as write tests"
        )
        assert "sub-task" in result.lower()
        assert result.count("Sub-task") >= 2


# =============================================================================
# RANKED STRATEGY TESTS
# =============================================================================


class TestScoredEnhancement:
    @pytest.mark.unit
    def test_dataclass_fields(self) -> None:
        enh = ScoredEnhancement(text="test", technique="spec", relevance=0.8, domain="technical")
        assert enh.text == "test"
        assert enh.technique == "spec"
        assert enh.relevance == 0.8
        assert enh.domain == "technical"

    @pytest.mark.unit
    def test_default_domain(self) -> None:
        enh = ScoredEnhancement(text="t", technique="t", relevance=0.5)
        assert enh.domain == "general"


class TestStrategyResult:
    @pytest.mark.unit
    def test_to_text_joins_enhancements(self) -> None:
        result = StrategyResult(
            enhancements=[
                ScoredEnhancement(text="A.", technique="t", relevance=0.9),
                ScoredEnhancement(text="B.", technique="t", relevance=0.5),
            ],
            strategy_name="test",
        )
        text = result.to_text()
        assert "A." in text
        assert "B." in text

    @pytest.mark.unit
    def test_to_text_respects_max_items(self) -> None:
        result = StrategyResult(
            enhancements=[
                ScoredEnhancement(text=f"Item{i}.", technique="t", relevance=0.5) for i in range(10)
            ],
        )
        text = result.to_text(max_items=3)
        assert "Item0." in text
        assert "Item2." in text
        assert "Item3." not in text

    @pytest.mark.unit
    def test_to_text_includes_conflicts(self) -> None:
        result = StrategyResult(
            enhancements=[
                ScoredEnhancement(text="A.", technique="t", relevance=0.9),
            ],
            conflicts=["Cost vs scale tension."],
        )
        text = result.to_text()
        assert "Trade-off:" in text
        assert "Cost vs scale" in text

    @pytest.mark.unit
    def test_empty_result(self) -> None:
        result = StrategyResult()
        assert result.to_text() == ""
        assert result.conflicts == []


class TestApplyStrategyRanked:
    @pytest.mark.unit
    def test_returns_strategy_result(self) -> None:
        result = apply_strategy_ranked("Compare Python vs Go for APIs")
        assert isinstance(result, StrategyResult)

    @pytest.mark.unit
    def test_enhancements_sorted_by_relevance(self) -> None:
        result = apply_strategy_ranked(
            "Compare Python vs JavaScript for web development",
            strategy_name="technical",
            query_type=QueryType.TECHNICAL,
        )
        relevances = [e.relevance for e in result.enhancements]
        assert relevances == sorted(relevances, reverse=True)

    @pytest.mark.unit
    def test_max_items_limits_output(self) -> None:
        result = apply_strategy_ranked(
            "Build a scalable, fast, reliable, secure API with Python and Django "
            "and also add caching and rate limiting",
            strategy_name="technical",
            max_items=3,
        )
        assert len(result.enhancements) <= 3

    @pytest.mark.unit
    def test_technical_domain_templates(self) -> None:
        result = apply_strategy_ranked(
            "Compare PostgreSQL vs MongoDB",
            strategy_name="technical",
            query_type=QueryType.TECHNICAL,
        )
        texts = " ".join(e.text for e in result.enhancements)
        # Technical domain should use specific template
        assert "benchmark" in texts.lower() or "ergonomic" in texts.lower()

    @pytest.mark.unit
    def test_research_domain_templates(self) -> None:
        result = apply_strategy_ranked(
            "Is deep learning better than traditional ML?",
            strategy_name="research",
            query_type=QueryType.RESEARCH,
        )
        texts = " ".join(e.text for e in result.enhancements)
        # Research domain for vague qualifier uses precise evaluation language
        assert "metric" in texts.lower() or "evaluation" in texts.lower()

    @pytest.mark.unit
    def test_unknown_strategy_falls_back(self) -> None:
        result = apply_strategy_ranked("Compare X vs Y", strategy_name="nonexistent")
        # Falls back to general strategy behavior (produces output)
        assert len(result.enhancements) > 0

    @pytest.mark.unit
    def test_no_match_returns_empty(self) -> None:
        result = apply_strategy_ranked("Hi")
        assert len(result.enhancements) == 0
        assert result.conflicts == []

    @pytest.mark.unit
    def test_conflict_detected_cost_vs_scale(self) -> None:
        result = apply_strategy_ranked(
            "Build a cheap, budget-friendly system that can scale "
            "to handle millions of concurrent users",
            strategy_name="technical",
            query_type=QueryType.TECHNICAL,
        )
        assert len(result.conflicts) > 0
        assert any("cost" in c.lower() or "scale" in c.lower() for c in result.conflicts)

    @pytest.mark.unit
    def test_no_conflict_for_simple_query(self) -> None:
        result = apply_strategy_ranked(
            "Explain Python list comprehensions",
            strategy_name="general",
        )
        assert result.conflicts == []

    @pytest.mark.unit
    def test_task_decomposition_included(self) -> None:
        result = apply_strategy_ranked(
            "Build auth, add caching, and implement rate limiting",
            strategy_name="technical",
        )
        techniques = [e.technique for e in result.enhancements]
        assert "task_decomposition" in techniques

    @pytest.mark.unit
    def test_all_enhancements_have_valid_relevance(self) -> None:
        result = apply_strategy_ranked(
            "How to optimize database performance for scale?",
            strategy_name="technical",
            query_type=QueryType.TECHNICAL,
        )
        for enh in result.enhancements:
            assert 0.0 <= enh.relevance <= 1.0

    @pytest.mark.unit
    def test_expanded_tech_regex(self) -> None:
        result = apply_strategy_ranked(
            "Deploy with Kubernetes on AWS using Terraform",
            strategy_name="technical",
        )
        texts = " ".join(e.text.lower() for e in result.enhancements)
        assert "kubernetes" in texts or "aws" in texts or "terraform" in texts
