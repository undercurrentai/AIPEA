"""AIPEA Named Enhancement Strategies — technique-based prompt enhancement.

Provides a strategy pattern for applying structured enhancement techniques
to queries based on their type and characteristics.

Each strategy bundles a set of pure-function techniques that transform
a query into a richer, more structured prompt. Strategies are selected
automatically by query type or can be specified explicitly.

Features:
- Relevance-scored technique outputs (ranked by match strength)
- Domain-aware suggestion templates (technical vs research vs creative)
- Conflict detection between competing constraints
- Backward-compatible: apply_strategy() still returns str

Design principles:
- Zero external dependencies (stdlib only + aipea._types)
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
# SCORED ENHANCEMENT DATA STRUCTURES
# =============================================================================


@dataclass
class ScoredEnhancement:
    """A single enhancement suggestion with relevance metadata.

    Attributes:
        text: The enhancement text.
        technique: Name of the technique that produced it.
        relevance: Relevance score [0.0-1.0] based on pattern match strength.
        domain: Domain tag (e.g. "technical", "research", "general").
    """

    text: str
    technique: str
    relevance: float
    domain: str = "general"


@dataclass
class StrategyResult:
    """Result of applying a strategy with ranking and conflict detection.

    Attributes:
        enhancements: Ranked list of scored enhancements (highest first).
        conflicts: List of detected conflicts between suggestions.
        strategy_name: Name of the strategy that was applied.
    """

    enhancements: list[ScoredEnhancement] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    strategy_name: str = "general"

    def to_text(self, max_items: int = 5) -> str:
        """Format as plain text for backward compatibility.

        Args:
            max_items: Maximum number of enhancements to include.

        Returns:
            Formatted enhancement text string.
        """
        parts = [e.text for e in self.enhancements[:max_items]]
        if self.conflicts:
            parts.append("Trade-off: " + " ".join(self.conflicts))
        return " ".join(parts)


# =============================================================================
# DOMAIN-AWARE SUGGESTION TEMPLATES
# =============================================================================

# Templates keyed by (pattern_type, domain) -> domain-specific text.
# Falls back to "general" domain if a specific domain is not found.
_DOMAIN_TEMPLATES: dict[str, dict[str, str]] = {
    "comparison": {
        "technical": (
            "Requirement: provide a side-by-side comparison with "
            "performance benchmarks, API ergonomics, ecosystem maturity, "
            "and use-case suitability."
        ),
        "research": (
            "Requirement: conduct a systematic comparison using "
            "methodological frameworks, empirical findings, and "
            "identified research gaps."
        ),
        "creative": (
            "Requirement: compare the stylistic qualities, audience impact, "
            "and expressive range of each option."
        ),
        "general": ("Requirement: provide a structured comparison with clear criteria."),
    },
    "evaluation": {
        "technical": (
            "Requirement: include evaluation criteria covering "
            "correctness, performance, maintainability, and "
            "community support with concrete trade-offs."
        ),
        "research": (
            "Requirement: evaluate using reproducibility, "
            "statistical rigor, and methodological soundness."
        ),
        "general": ("Requirement: include evaluation criteria and trade-offs."),
    },
    "implementation": {
        "technical": (
            "Requirement: provide step-by-step implementation with "
            "code examples, error handling, and testing approach."
        ),
        "general": ("Requirement: provide step-by-step implementation guidance."),
    },
    "explanation": {
        "technical": (
            "Requirement: provide a clear explanation with architecture "
            "diagrams (ASCII), key abstractions, and concrete examples."
        ),
        "research": (
            "Requirement: explain with theoretical foundations, "
            "key citations, and current state of the art."
        ),
        "general": ("Requirement: provide a clear, structured explanation."),
    },
    "time_constraint": {
        "technical": (
            "Constraint: time-sensitive — prioritize proven solutions "
            "and existing libraries over custom implementations."
        ),
        "general": "Constraint: time-sensitive response needed.",
    },
    "resource_constraint": {
        "technical": (
            "Constraint: resource-constrained — prefer lightweight "
            "dependencies, minimal infrastructure, and cost-efficient services."
        ),
        "general": "Constraint: resource-constrained solution preferred.",
    },
    "scope_constraint": {
        "general": "Constraint: narrowly scoped response expected.",
    },
    "performance_metric": {
        "technical": (
            "Metric: quantify with p50/p99 latency, throughput (req/s), "
            "CPU/memory utilization, and cold-start time."
        ),
        "general": ("Metric: quantify with response time, throughput, or resource usage."),
    },
    "quality_metric": {
        "technical": (
            "Metric: define quality in terms of error rates, uptime SLA, "
            "test coverage, and mean time to recovery."
        ),
        "general": ("Metric: define quality in terms of error rates, uptime, or test coverage."),
    },
    "scale_metric": {
        "technical": (
            "Metric: specify scale targets — concurrent users, "
            "requests per second, data volume, and geographic distribution."
        ),
        "general": ("Metric: specify the scale in terms of users, requests, or data volume."),
    },
    "vague_qualifier": {
        "research": (
            "Clarification: define the evaluation metric precisely — "
            "specify the dependent variable, measurement method, and baseline."
        ),
        "general": ("Clarification: define the metric for the quality assessment."),
    },
    "causality": {
        "research": (
            "Clarification: verify causation vs correlation with "
            "controlled experiments or longitudinal evidence."
        ),
        "general": ("Clarification: verify the causal relationship with evidence."),
    },
    "generalization": {
        "general": "Clarification: consider edge cases and exceptions.",
    },
    "strategic_goal": {
        "general": "Primary objective: define the strategic direction.",
    },
    "milestones": {
        "general": "Sub-goal: identify key milestones and decision points.",
    },
    "stakeholders": {
        "general": "Sub-goal: map stakeholders and responsibilities.",
    },
    "risk": {
        "general": "Sub-goal: enumerate risks and mitigation strategies.",
    },
}


def _get_template(pattern_type: str, domain: str) -> str:
    """Look up a domain-specific template, falling back to 'general'.

    Args:
        pattern_type: The template category key.
        domain: Preferred domain (e.g. "technical", "research").

    Returns:
        Template text, or empty string if no template exists.
    """
    templates = _DOMAIN_TEMPLATES.get(pattern_type, {})
    return templates.get(domain, templates.get("general", ""))


# =============================================================================
# INTERNAL SCORED TECHNIQUE FUNCTIONS
# =============================================================================

# Technology regex shared by constraint identification.
_TECH_PATTERN = (
    r"\b(python|javascript|typescript|java|go|rust|sql|react|django|"
    r"fastapi|flask|node|kubernetes|docker|terraform|aws|gcp|azure)\b"
)


def _specification_extraction_scored(
    query: str,
    domain: str = "general",
) -> list[ScoredEnhancement]:
    """Extract implicit requirements with relevance scoring.

    Detects comparison, evaluation, implementation, and explanation
    patterns in the query and returns scored suggestions.

    Args:
        query: The user's query.
        domain: Domain for template selection.

    Returns:
        List of scored enhancements found.
    """
    results: list[ScoredEnhancement] = []
    q_lower = query.lower()

    # Comparison patterns
    if re.search(r"\b(compare|vs|versus|difference|between)\b", query, re.IGNORECASE):
        count = len(re.findall(r"\b(compare|vs|versus|difference|between)\b", query, re.IGNORECASE))
        results.append(
            ScoredEnhancement(
                text=_get_template("comparison", domain),
                technique="specification_extraction",
                relevance=min(0.7 + count * 0.1, 1.0),
                domain=domain,
            )
        )

    # Evaluation patterns
    if re.search(r"\b(best|worst|recommend|should I|which)\b", query, re.IGNORECASE):
        results.append(
            ScoredEnhancement(
                text=_get_template("evaluation", domain),
                technique="specification_extraction",
                relevance=0.7,
                domain=domain,
            )
        )

    # Implementation patterns
    if re.search(r"\b(how to|implement|build|create|write)\b", query, re.IGNORECASE):
        count = len(re.findall(r"\b(how to|implement|build|create|write)\b", query, re.IGNORECASE))
        results.append(
            ScoredEnhancement(
                text=_get_template("implementation", domain),
                technique="specification_extraction",
                relevance=min(0.6 + count * 0.1, 1.0),
                domain=domain,
            )
        )

    # Explanation patterns (lower priority if implementation also present)
    if re.search(r"\b(explain|what is|how does|why)\b", query, re.IGNORECASE):
        has_impl = "implement" in q_lower or "build" in q_lower
        base = 0.4 if has_impl else 0.6
        results.append(
            ScoredEnhancement(
                text=_get_template("explanation", domain),
                technique="specification_extraction",
                relevance=base,
                domain=domain,
            )
        )

    return results


def _constraint_identification_scored(
    query: str,
    domain: str = "general",
) -> list[ScoredEnhancement]:
    """Identify constraints with relevance scoring.

    Detects time, resource, scope, and technology constraints.

    Args:
        query: The user's query.
        domain: Domain for template selection.

    Returns:
        List of scored enhancements found.
    """
    results: list[ScoredEnhancement] = []

    # Time constraint
    if re.search(
        r"\b(quickly|fast|urgent|asap|deadline|today|tomorrow)\b",
        query,
        re.IGNORECASE,
    ):
        results.append(
            ScoredEnhancement(
                text=_get_template("time_constraint", domain),
                technique="constraint_identification",
                relevance=0.8,
                domain=domain,
            )
        )

    # Resource constraint
    if re.search(
        r"\b(cheap|free|budget|minimal|lightweight|simple)\b",
        query,
        re.IGNORECASE,
    ):
        results.append(
            ScoredEnhancement(
                text=_get_template("resource_constraint", domain),
                technique="constraint_identification",
                relevance=0.7,
                domain=domain,
            )
        )

    # Scope constraint
    if re.search(
        r"\b(only|just|specifically|limited to|without)\b",
        query,
        re.IGNORECASE,
    ):
        results.append(
            ScoredEnhancement(
                text=_get_template("scope_constraint", domain),
                technique="constraint_identification",
                relevance=0.5,
                domain=domain,
            )
        )

    # Technology constraint
    tech_match = re.search(_TECH_PATTERN, query, re.IGNORECASE)
    if tech_match:
        tech = tech_match.group(0)
        all_techs = re.findall(_TECH_PATTERN, query, re.IGNORECASE)
        relevance = min(0.6 + len(all_techs) * 0.1, 0.9)
        results.append(
            ScoredEnhancement(
                text=f"Constraint: technology stack includes {tech}.",
                technique="constraint_identification",
                relevance=relevance,
                domain=domain,
            )
        )

    return results


def _hypothesis_clarification_scored(
    query: str,
    domain: str = "general",
) -> list[ScoredEnhancement]:
    """Reformulate ambiguous claims into testable hypotheses.

    Detects vague qualifiers, causal claims, and overgeneralizations.

    Args:
        query: The user's query.
        domain: Domain for template selection.

    Returns:
        List of scored enhancements found.
    """
    results: list[ScoredEnhancement] = []

    # Vague qualifier
    if re.search(
        r"\b(better|worse|good|bad|effective|efficient)\b",
        query,
        re.IGNORECASE,
    ):
        results.append(
            ScoredEnhancement(
                text=_get_template("vague_qualifier", domain),
                technique="hypothesis_clarification",
                relevance=0.75,
                domain=domain,
            )
        )

    # Causality
    if re.search(
        r"\b(because|causes?|leads? to|results? in)\b",
        query,
        re.IGNORECASE,
    ):
        results.append(
            ScoredEnhancement(
                text=_get_template("causality", domain),
                technique="hypothesis_clarification",
                relevance=0.8,
                domain=domain,
            )
        )

    # Generalization
    if re.search(
        r"\b(always|never|everyone|nobody|all|none)\b",
        query,
        re.IGNORECASE,
    ):
        results.append(
            ScoredEnhancement(
                text=_get_template("generalization", domain),
                technique="hypothesis_clarification",
                relevance=0.7,
                domain=domain,
            )
        )

    return results


def _metric_definition_scored(
    query: str,
    domain: str = "general",
) -> list[ScoredEnhancement]:
    """Define measurable success criteria for a query.

    Detects performance, quality, and scale metric patterns.

    Args:
        query: The user's query.
        domain: Domain for template selection.

    Returns:
        List of scored enhancements found.
    """
    results: list[ScoredEnhancement] = []

    # Performance metric
    if re.search(
        r"\b(performance|speed|latency|throughput|optimize)\b",
        query,
        re.IGNORECASE,
    ):
        results.append(
            ScoredEnhancement(
                text=_get_template("performance_metric", domain),
                technique="metric_definition",
                relevance=0.8,
                domain=domain,
            )
        )

    # Quality metric
    if re.search(
        r"\b(quality|reliable|robust|stable|secure)\b",
        query,
        re.IGNORECASE,
    ):
        results.append(
            ScoredEnhancement(
                text=_get_template("quality_metric", domain),
                technique="metric_definition",
                relevance=0.75,
                domain=domain,
            )
        )

    # Scale metric
    if re.search(
        r"\b(scale|grow|handle|capacity|concurrent)\b",
        query,
        re.IGNORECASE,
    ):
        results.append(
            ScoredEnhancement(
                text=_get_template("scale_metric", domain),
                technique="metric_definition",
                relevance=0.75,
                domain=domain,
            )
        )

    return results


def _objective_hierarchy_construction_scored(
    query: str,
    domain: str = "general",
) -> list[ScoredEnhancement]:
    """Build a goal tree from strategic queries.

    Identifies high-level objectives and maps them to sub-goals
    for strategic or planning-oriented queries.

    Args:
        query: The user's query.
        domain: Domain for template selection.

    Returns:
        List of scored enhancements found.
    """
    results: list[ScoredEnhancement] = []

    # Strategic goal + milestones
    if re.search(
        r"\b(strategy|plan|roadmap|vision|architecture)\b",
        query,
        re.IGNORECASE,
    ):
        results.append(
            ScoredEnhancement(
                text=_get_template("strategic_goal", domain),
                technique="objective_hierarchy_construction",
                relevance=0.85,
                domain=domain,
            )
        )
        results.append(
            ScoredEnhancement(
                text=_get_template("milestones", domain),
                technique="objective_hierarchy_construction",
                relevance=0.7,
                domain=domain,
            )
        )

    # Stakeholders
    if re.search(
        r"\b(team|organization|process|workflow|pipeline)\b",
        query,
        re.IGNORECASE,
    ):
        results.append(
            ScoredEnhancement(
                text=_get_template("stakeholders", domain),
                technique="objective_hierarchy_construction",
                relevance=0.65,
                domain=domain,
            )
        )

    # Risk
    if re.search(
        r"\b(risk|challenge|obstacle|mitigation|contingency)\b",
        query,
        re.IGNORECASE,
    ):
        results.append(
            ScoredEnhancement(
                text=_get_template("risk", domain),
                technique="objective_hierarchy_construction",
                relevance=0.8,
                domain=domain,
            )
        )

    return results


# =============================================================================
# PUBLIC STRING-RETURNING WRAPPERS (backward compatibility)
# =============================================================================


def specification_extraction(query: str) -> str:
    """Extract implicit requirements from a query.

    Args:
        query: The user's query.

    Returns:
        Extracted specification text, or empty string if none found.
    """
    return " ".join(e.text for e in _specification_extraction_scored(query))


def constraint_identification(query: str) -> str:
    """Identify constraints present in a query.

    Args:
        query: The user's query.

    Returns:
        Constraint text, or empty string if none found.
    """
    return " ".join(e.text for e in _constraint_identification_scored(query))


def hypothesis_clarification(query: str) -> str:
    """Reformulate ambiguous claims into testable hypotheses.

    Args:
        query: The user's query.

    Returns:
        Clarification text, or empty string if none found.
    """
    return " ".join(e.text for e in _hypothesis_clarification_scored(query))


def metric_definition(query: str) -> str:
    """Define measurable success criteria for a query.

    Args:
        query: The user's query.

    Returns:
        Metric definition text, or empty string if none found.
    """
    return " ".join(e.text for e in _metric_definition_scored(query))


def objective_hierarchy_construction(query: str) -> str:
    """Build a goal hierarchy from strategic queries.

    Args:
        query: The user's query.

    Returns:
        Objective hierarchy text, or empty string if none found.
    """
    return " ".join(e.text for e in _objective_hierarchy_construction_scored(query))


def task_decomposition(query: str) -> str:
    """Break complex queries into sub-tasks.

    Identifies when a query involves multiple concerns and suggests
    a decomposition into manageable sub-tasks.

    Args:
        query: The user's query.

    Returns:
        Task decomposition text, or empty string for simple queries.
    """
    conjunction_count = len(
        re.findall(
            r"\b(and|also|additionally|plus|as well as)\b",
            query,
            re.IGNORECASE,
        )
    )
    comma_count = query.count(",")
    concern_count = conjunction_count + comma_count

    if concern_count < 2:
        return ""

    parts: list[str] = []
    segments = re.split(
        r"\b(?:and|also|additionally|plus|as\s+well\s+as)\b|,",
        query,
        flags=re.IGNORECASE,
    )
    # Use a separate counter for accepted sub-tasks so dropped segments
    # (empty or too-short) don't create gaps in the numbering. (#87)
    task_num = 0
    for segment in segments:
        segment = segment.strip()
        if segment and len(segment) > 5:
            task_num += 1
            parts.append(f"Sub-task {task_num}: {segment}")

    if parts:
        return "Decomposition: " + " | ".join(parts)
    return ""


# =============================================================================
# CONFLICT DETECTION
# =============================================================================

# Pairs of template types that are commonly in tension.
_CONFLICT_PAIRS: list[tuple[str, str, str]] = [
    (
        "resource_constraint",
        "scale_metric",
        "Cost minimization and scalability are often in tension — "
        "consider auto-scaling with reserved capacity for cost-effective scale.",
    ),
    (
        "time_constraint",
        "quality_metric",
        "Speed-to-delivery and quality can conflict — "
        "prioritize critical-path quality gates and defer non-blocking improvements.",
    ),
    (
        "resource_constraint",
        "performance_metric",
        "Budget constraints may limit performance optimization options — "
        "profile first to find the highest-ROI optimizations.",
    ),
]


def _detect_conflicts(enhancements: list[ScoredEnhancement]) -> list[str]:
    """Detect conflicts between enhancement suggestions.

    Checks for known tension pairs (e.g., cheap + scale, fast + quality)
    by matching enhancement text against domain template text.

    Args:
        enhancements: List of scored enhancements to check.

    Returns:
        List of conflict advisory strings.
    """
    # Collect all template types present by checking text against templates
    present: set[str] = set()
    for enh in enhancements:
        text_lower = enh.text.lower()
        for template_key, template_variants in _DOMAIN_TEMPLATES.items():
            for tmpl_text in template_variants.values():
                if tmpl_text.lower() in text_lower or text_lower in tmpl_text.lower():
                    present.add(template_key)
                    break

    conflicts: list[str] = []
    for key_a, key_b, advisory in _CONFLICT_PAIRS:
        if key_a in present and key_b in present:
            conflicts.append(advisory)

    return conflicts


# =============================================================================
# TECHNIQUE REGISTRIES
# =============================================================================

# Type aliases for technique function signatures.
TechniqueFunc = Callable[[str], str]
ScoredTechniqueFunc = Callable[[str, str], list[ScoredEnhancement]]

# Public string-returning functions (backward compat).
TECHNIQUE_FUNCTIONS: dict[str, TechniqueFunc] = {
    "specification_extraction": specification_extraction,
    "constraint_identification": constraint_identification,
    "hypothesis_clarification": hypothesis_clarification,
    "metric_definition": metric_definition,
    "task_decomposition": task_decomposition,
    "objective_hierarchy_construction": objective_hierarchy_construction,
}

# Internal scored functions (for apply_strategy_ranked).
_SCORED_TECHNIQUES: dict[str, ScoredTechniqueFunc] = {
    "specification_extraction": _specification_extraction_scored,
    "constraint_identification": _constraint_identification_scored,
    "hypothesis_clarification": _hypothesis_clarification_scored,
    "metric_definition": _metric_definition_scored,
    "objective_hierarchy_construction": _objective_hierarchy_construction_scored,
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

# Map QueryType to default strategy name.
QUERY_TYPE_STRATEGY: dict[QueryType, str] = {
    QueryType.TECHNICAL: "technical",
    QueryType.RESEARCH: "research",
    QueryType.CREATIVE: "creative",
    QueryType.ANALYTICAL: "analytical",
    QueryType.OPERATIONAL: "technical",
    QueryType.STRATEGIC: "strategic",
    QueryType.UNKNOWN: "general",
}

# Map QueryType to domain string for template selection.
_QUERY_TYPE_DOMAIN: dict[QueryType, str] = {
    QueryType.TECHNICAL: "technical",
    QueryType.RESEARCH: "research",
    QueryType.CREATIVE: "creative",
    QueryType.ANALYTICAL: "technical",
    QueryType.OPERATIONAL: "technical",
    QueryType.STRATEGIC: "general",
    QueryType.UNKNOWN: "general",
}


# =============================================================================
# STRATEGY APPLICATION
# =============================================================================


def apply_strategy(query: str, strategy_name: str | None = None) -> str:
    """Apply a named enhancement strategy to a query.

    Runs the strategy's technique chain and concatenates the results
    into a structured enhancement prefix. This is the backward-compatible
    interface -- for richer output, use apply_strategy_ranked().

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


def apply_strategy_ranked(
    query: str,
    strategy_name: str | None = None,
    query_type: QueryType = QueryType.UNKNOWN,
    max_items: int = 5,
) -> StrategyResult:
    """Apply a strategy with relevance ranking and conflict detection.

    Runs the strategy's technique chain, scores each suggestion by
    relevance, ranks them, detects conflicts, and returns a rich result.

    Args:
        query: The user's query.
        strategy_name: Strategy to apply (default: "general").
        query_type: The classified query type (for domain-aware templates).
        max_items: Maximum number of enhancements to return.

    Returns:
        StrategyResult with ranked enhancements and detected conflicts.
    """
    name = strategy_name or "general"
    strategy = STRATEGY_REGISTRY.get(name)
    if strategy is None:
        logger.warning("Unknown strategy %r, falling back to 'general'", name)
        strategy = STRATEGY_REGISTRY["general"]
        name = strategy.name

    domain = _QUERY_TYPE_DOMAIN.get(query_type, "general")
    all_enhancements: list[ScoredEnhancement] = []

    for technique_name in strategy.techniques:
        # Use scored technique if available, else handle task_decomposition
        scored_func = _SCORED_TECHNIQUES.get(technique_name)
        if scored_func is not None:
            enhancements = scored_func(query, domain)
            all_enhancements.extend(enhancements)
        elif technique_name == "task_decomposition":
            text = task_decomposition(query)
            if text:
                all_enhancements.append(
                    ScoredEnhancement(
                        text=text,
                        technique="task_decomposition",
                        relevance=0.65,
                        domain=domain,
                    )
                )

    # Sort by relevance (highest first)
    all_enhancements.sort(key=lambda e: e.relevance, reverse=True)

    # Truncate first, then detect conflicts only against the visible set
    # so callers don't see advisories referencing enhancements they can't see. (#88)
    visible = all_enhancements[:max_items]
    conflicts = _detect_conflicts(visible)

    return StrategyResult(
        enhancements=visible,
        conflicts=conflicts,
        strategy_name=name,
    )


def select_strategy_for_query_type(query_type: QueryType) -> str:
    """Select the default strategy name for a given query type.

    Args:
        query_type: The analyzed query type.

    Returns:
        Strategy name string.
    """
    return QUERY_TYPE_STRATEGY.get(query_type, "general")


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    "STRATEGY_REGISTRY",
    "TECHNIQUE_FUNCTIONS",
    "EnhancementStrategy",
    "ScoredEnhancement",
    "StrategyResult",
    "apply_strategy",
    "apply_strategy_ranked",
    "constraint_identification",
    "hypothesis_clarification",
    "metric_definition",
    "objective_hierarchy_construction",
    "select_strategy_for_query_type",
    "specification_extraction",
    "task_decomposition",
]
