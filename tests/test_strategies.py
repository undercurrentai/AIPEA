"""Tests for aipea.strategies — named enhancement strategies and technique functions."""

from __future__ import annotations

import pytest

from aipea._types import QueryType
from aipea.strategies import (
    STRATEGY_REGISTRY,
    TECHNIQUE_FUNCTIONS,
    EnhancementStrategy,
    apply_strategy,
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
