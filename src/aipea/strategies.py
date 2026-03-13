"""AIPEA Named Enhancement Strategies — technique-based prompt enhancement.

Provides a strategy pattern for applying structured enhancement techniques
to queries based on their type and characteristics.

Each strategy bundles a set of pure-function techniques that transform
a query into a richer, more structured prompt. Strategies are selected
automatically by query type or can be specified explicitly.

Design principles:
- Zero external dependencies (stdlib only)
- Pure functions for all techniques (no side effects)
- Backward-compatible: no strategy = existing behavior
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from aipea._types import QueryType

logger = logging.getLogger(__name__)


# =============================================================================
# TECHNIQUE FUNCTIONS
# =============================================================================


def specification_extraction(query: str) -> str:
    """Extract implicit requirements from a query.

    Identifies unstated assumptions and makes them explicit by detecting
    common requirement patterns (comparisons, evaluations, choices).

    Args:
        query: The user's query.

    Returns:
        Extracted specification text, or empty string if none found.
    """
    specs: list[str] = []

    # Detect comparison patterns
    if re.search(r"\b(compare|vs|versus|difference|between)\b", query, re.IGNORECASE):
        specs.append("Requirement: provide a structured comparison with clear criteria.")

    # Detect evaluation patterns
    if re.search(r"\b(best|worst|recommend|should I|which)\b", query, re.IGNORECASE):
        specs.append("Requirement: include evaluation criteria and trade-offs.")

    # Detect implementation patterns
    if re.search(r"\b(how to|implement|build|create|write)\b", query, re.IGNORECASE):
        specs.append("Requirement: provide step-by-step implementation guidance.")

    # Detect explanation patterns
    if re.search(r"\b(explain|what is|how does|why)\b", query, re.IGNORECASE):
        specs.append("Requirement: provide a clear, structured explanation.")

    return " ".join(specs)


def constraint_identification(query: str) -> str:
    """Identify explicit and implicit constraints in a query.

    Detects time, resource, scope, and technology constraints
    mentioned or implied in the query.

    Args:
        query: The user's query.

    Returns:
        Identified constraints text, or empty string if none found.
    """
    constraints: list[str] = []

    # Time constraints
    if re.search(r"\b(quickly|fast|urgent|asap|deadline|today|tomorrow)\b", query, re.IGNORECASE):
        constraints.append("Constraint: time-sensitive response needed.")

    # Resource constraints
    if re.search(r"\b(cheap|free|budget|minimal|lightweight|simple)\b", query, re.IGNORECASE):
        constraints.append("Constraint: resource-constrained solution preferred.")

    # Scope constraints
    if re.search(r"\b(only|just|specifically|limited to|without)\b", query, re.IGNORECASE):
        constraints.append("Constraint: narrowly scoped response expected.")

    # Technology constraints
    tech_match = re.search(
        r"\b(python|javascript|typescript|java|go|rust|sql|react|django)\b",
        query,
        re.IGNORECASE,
    )
    if tech_match:
        constraints.append(f"Constraint: technology stack includes {tech_match.group(0)}.")

    return " ".join(constraints)


def hypothesis_clarification(query: str) -> str:
    """Reformulate ambiguous claims into testable hypotheses.

    Transforms vague or assumption-laden queries into more precise
    formulations that can be addressed systematically.

    Args:
        query: The user's query.

    Returns:
        Clarified hypothesis text, or empty string if not applicable.
    """
    clarifications: list[str] = []

    # Detect vague qualifiers
    if re.search(r"\b(better|worse|good|bad|effective|efficient)\b", query, re.IGNORECASE):
        clarifications.append("Clarification: define the metric for the quality assessment.")

    # Detect assumed causality
    if re.search(r"\b(because|causes?|leads? to|results? in)\b", query, re.IGNORECASE):
        clarifications.append("Clarification: verify the causal relationship with evidence.")

    # Detect generalizations
    if re.search(r"\b(always|never|everyone|nobody|all|none)\b", query, re.IGNORECASE):
        clarifications.append("Clarification: consider edge cases and exceptions.")

    return " ".join(clarifications)


def metric_definition(query: str) -> str:
    """Define measurable success criteria for a query.

    Identifies what success looks like for the query and suggests
    concrete metrics or evaluation criteria.

    Args:
        query: The user's query.

    Returns:
        Suggested metrics text, or empty string if not applicable.
    """
    metrics: list[str] = []

    # Performance queries
    if re.search(r"\b(performance|speed|latency|throughput|optimize)\b", query, re.IGNORECASE):
        metrics.append("Metric: quantify with response time, throughput, or resource usage.")

    # Quality queries
    if re.search(r"\b(quality|reliable|robust|stable|secure)\b", query, re.IGNORECASE):
        metrics.append("Metric: define quality in terms of error rates, uptime, or test coverage.")

    # Scale queries
    if re.search(r"\b(scale|grow|handle|capacity|concurrent)\b", query, re.IGNORECASE):
        metrics.append("Metric: specify the scale in terms of users, requests, or data volume.")

    return " ".join(metrics)


def task_decomposition(query: str) -> str:
    """Break complex queries into sub-tasks.

    Identifies when a query involves multiple concerns and suggests
    a decomposition into manageable sub-tasks.

    Args:
        query: The user's query.

    Returns:
        Task decomposition text, or empty string for simple queries.
    """
    # Count distinct concerns (rough heuristic: conjunctions and commas)
    conjunction_count = len(
        re.findall(r"\b(and|also|additionally|plus|as well as)\b", query, re.IGNORECASE)
    )
    comma_count = query.count(",")
    concern_count = conjunction_count + comma_count

    if concern_count < 2:
        return ""

    parts: list[str] = []
    # Split on conjunctions for sub-task identification
    segments = re.split(
        r"\b(?:and|also|additionally|plus|as\s+well\s+as)\b|,", query, flags=re.IGNORECASE
    )
    for i, segment in enumerate(segments, 1):
        segment = segment.strip()
        if segment and len(segment) > 5:
            parts.append(f"Sub-task {i}: {segment}")

    if parts:
        return "Decomposition: " + " | ".join(parts)
    return ""


def objective_hierarchy_construction(query: str) -> str:
    """Build a goal tree from strategic queries.

    Identifies high-level objectives and maps them to sub-goals
    for strategic or planning-oriented queries.

    Args:
        query: The user's query.

    Returns:
        Objective hierarchy text, or empty string if not applicable.
    """
    objectives: list[str] = []

    # Strategic goal patterns
    if re.search(r"\b(strategy|plan|roadmap|vision|architecture)\b", query, re.IGNORECASE):
        objectives.append("Primary objective: define the strategic direction.")
        objectives.append("Sub-goal: identify key milestones and decision points.")

    # Organizational patterns
    if re.search(r"\b(team|organization|process|workflow|pipeline)\b", query, re.IGNORECASE):
        objectives.append("Sub-goal: map stakeholders and responsibilities.")

    # Risk patterns
    if re.search(r"\b(risk|challenge|obstacle|mitigation|contingency)\b", query, re.IGNORECASE):
        objectives.append("Sub-goal: enumerate risks and mitigation strategies.")

    if objectives:
        return "Objective hierarchy: " + " → ".join(objectives)
    return ""


# =============================================================================
# TECHNIQUE REGISTRY
# =============================================================================

TechniqueFunc = Callable[[str], str]

TECHNIQUE_FUNCTIONS: dict[str, TechniqueFunc] = {
    "specification_extraction": specification_extraction,
    "constraint_identification": constraint_identification,
    "hypothesis_clarification": hypothesis_clarification,
    "metric_definition": metric_definition,
    "task_decomposition": task_decomposition,
    "objective_hierarchy_construction": objective_hierarchy_construction,
}


# =============================================================================
# STRATEGY DATACLASS AND REGISTRY
# =============================================================================


@dataclass
class EnhancementStrategy:
    """A named enhancement strategy combining multiple techniques.

    Attributes:
        name: Strategy identifier (e.g., "technical", "research").
        techniques: Ordered list of technique names to apply.
        context_requirements: What context this strategy needs.
    """

    name: str
    techniques: list[str] = field(default_factory=list)
    context_requirements: list[str] = field(default_factory=list)


STRATEGY_REGISTRY: dict[str, EnhancementStrategy] = {
    "general": EnhancementStrategy(
        name="general",
        techniques=["specification_extraction", "constraint_identification"],
        context_requirements=[],
    ),
    "technical": EnhancementStrategy(
        name="technical",
        techniques=[
            "specification_extraction",
            "constraint_identification",
            "metric_definition",
            "task_decomposition",
        ],
        context_requirements=["code_context", "technical_domain"],
    ),
    "research": EnhancementStrategy(
        name="research",
        techniques=[
            "specification_extraction",
            "hypothesis_clarification",
            "metric_definition",
        ],
        context_requirements=["literature_context", "domain_expertise"],
    ),
    "creative": EnhancementStrategy(
        name="creative",
        techniques=["specification_extraction", "hypothesis_clarification"],
        context_requirements=["style_context"],
    ),
    "analytical": EnhancementStrategy(
        name="analytical",
        techniques=[
            "specification_extraction",
            "constraint_identification",
            "metric_definition",
            "task_decomposition",
        ],
        context_requirements=["data_context"],
    ),
    "strategic": EnhancementStrategy(
        name="strategic",
        techniques=[
            "specification_extraction",
            "constraint_identification",
            "objective_hierarchy_construction",
            "task_decomposition",
        ],
        context_requirements=["organizational_context"],
    ),
}

# Map QueryType to default strategy name
QUERY_TYPE_STRATEGY: dict[QueryType, str] = {
    QueryType.TECHNICAL: "technical",
    QueryType.RESEARCH: "research",
    QueryType.CREATIVE: "creative",
    QueryType.ANALYTICAL: "analytical",
    QueryType.OPERATIONAL: "technical",
    QueryType.STRATEGIC: "strategic",
    QueryType.UNKNOWN: "general",
}


def apply_strategy(query: str, strategy_name: str | None = None) -> str:
    """Apply a named enhancement strategy to a query.

    Runs the strategy's technique chain and concatenates the results
    into a structured enhancement prefix.

    Args:
        query: The user's query.
        strategy_name: Strategy to apply (default: "general").

    Returns:
        Enhancement text to prepend to the query. Empty string if
        no techniques produced output.
    """
    name = strategy_name or "general"
    strategy = STRATEGY_REGISTRY.get(name)
    if strategy is None:
        logger.warning("Unknown strategy %r, falling back to 'general'", name)
        strategy = STRATEGY_REGISTRY["general"]

    outputs: list[str] = []
    for technique_name in strategy.techniques:
        func = TECHNIQUE_FUNCTIONS.get(technique_name)
        if func is None:
            logger.debug("Unknown technique %r in strategy %r", technique_name, name)
            continue
        result = func(query)
        if result:
            outputs.append(result)

    return " ".join(outputs)


def select_strategy_for_query_type(query_type: QueryType) -> str:
    """Select the default strategy name for a given query type.

    Args:
        query_type: The analyzed query type.

    Returns:
        Strategy name string.
    """
    return QUERY_TYPE_STRATEGY.get(query_type, "general")


__all__ = [
    "STRATEGY_REGISTRY",
    "TECHNIQUE_FUNCTIONS",
    "EnhancementStrategy",
    "apply_strategy",
    "constraint_identification",
    "hypothesis_clarification",
    "metric_definition",
    "objective_hierarchy_construction",
    "select_strategy_for_query_type",
    "specification_extraction",
    "task_decomposition",
]
