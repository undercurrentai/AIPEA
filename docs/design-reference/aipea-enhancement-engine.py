"""
AI Prompt Engineer Agent - Core Enhancement Engine
A sophisticated, multi-strategy enhancement system with military-grade resilience
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import hashlib
import json
from datetime import datetime
import numpy as np


class QueryType(Enum):
    TECHNICAL = "technical"
    RESEARCH = "research"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    OPERATIONAL = "operational"
    STRATEGIC = "strategic"
    UNKNOWN = "unknown"


class SecurityLevel(Enum):
    UNCLASSIFIED = 0
    SENSITIVE = 1
    SECRET = 2
    TOP_SECRET = 3


@dataclass
class EnhancementStrategy:
    """Defines how to enhance a specific type of query"""
    name: str
    query_type: QueryType
    techniques: List[str]
    context_requirements: List[str]
    output_format: str
    security_clearance: SecurityLevel = SecurityLevel.UNCLASSIFIED


@dataclass
class QueryContext:
    """Seven-lens context model"""
    user: Dict[str, Any]
    task: Dict[str, Any]
    data: List[Any]
    environment: Dict[str, Any]
    history: List[Dict]
    output_requirements: Dict[str, Any]
    feedback: List[Dict]
    security_classification: SecurityLevel = SecurityLevel.UNCLASSIFIED
    
    def to_vector(self) -> np.ndarray:
        """Convert context to vector for similarity matching"""
        # Simplified vectorization for demonstration
        vector = []
        vector.extend([len(self.history), len(self.data), len(self.feedback)])
        vector.append(self.security_classification.value)
        vector.extend([1 if k in self.user else 0 for k in ['expertise', 'clearance', 'role']])
        return np.array(vector)


@dataclass
class EnhancedQuery:
    original: str
    enhanced: str
    metadata: Dict[str, Any]
    confidence: float
    strategy_used: str
    processing_tier: int
    security_flags: List[str] = field(default_factory=list)
    enhancement_trace: List[str] = field(default_factory=list)


class EnhancementEngine:
    """Core engine that orchestrates query enhancement with graceful degradation"""
    
    def __init__(self):
        self.strategies = self._initialize_strategies()
        self.security_scanner = SecurityScanner()
        self.context_builder = ContextBuilder()
        self.quality_assessor = QualityAssessor()
        
    def _initialize_strategies(self) -> Dict[QueryType, EnhancementStrategy]:
        """Initialize enhancement strategies for different query types"""
        return {
            QueryType.TECHNICAL: EnhancementStrategy(
                name="Technical Deep Dive",
                query_type=QueryType.TECHNICAL,
                techniques=[
                    "specification_extraction",
                    "constraint_identification", 
                    "solution_space_mapping",
                    "edge_case_enumeration",
                    "performance_requirement_injection"
                ],
                context_requirements=["tech_stack", "constraints", "performance_targets"],
                output_format="structured_technical_spec"
            ),
            
            QueryType.RESEARCH: EnhancementStrategy(
                name="Academic Research Enhancement",
                query_type=QueryType.RESEARCH,
                techniques=[
                    "hypothesis_clarification",
                    "methodology_suggestion",
                    "literature_context_injection",
                    "citation_requirement_detection",
                    "statistical_rigor_enhancement"
                ],
                context_requirements=["domain", "academic_level", "publication_target"],
                output_format="research_methodology_framework"
            ),
            
            QueryType.CREATIVE: EnhancementStrategy(
                name="Creative Amplification",
                query_type=QueryType.CREATIVE,
                techniques=[
                    "constraint_liberation",
                    "perspective_multiplication",
                    "sensory_detail_injection",
                    "emotional_resonance_mapping",
                    "narrative_structure_suggestion"
                ],
                context_requirements=["audience", "medium", "style_preferences"],
                output_format="creative_brief"
            ),
            
            QueryType.ANALYTICAL: EnhancementStrategy(
                name="Analytical Precision Enhancement",
                query_type=QueryType.ANALYTICAL,
                techniques=[
                    "metric_definition",
                    "data_source_identification",
                    "statistical_method_selection",
                    "visualization_recommendation",
                    "insight_framework_construction"
                ],
                context_requirements=["data_availability", "analysis_goals", "stakeholders"],
                output_format="analytical_framework"
            ),
            
            QueryType.OPERATIONAL: EnhancementStrategy(
                name="Operational Clarity",
                query_type=QueryType.OPERATIONAL,
                techniques=[
                    "task_decomposition",
                    "resource_requirement_mapping",
                    "timeline_construction",
                    "risk_identification",
                    "success_metric_definition"
                ],
                context_requirements=["resources", "constraints", "timeline"],
                output_format="operational_plan"
            ),
            
            QueryType.STRATEGIC: EnhancementStrategy(
                name="Strategic Vision Enhancement",
                query_type=QueryType.STRATEGIC,
                techniques=[
                    "objective_hierarchy_construction",
                    "stakeholder_impact_analysis",
                    "scenario_planning_injection",
                    "decision_criteria_elaboration",
                    "long_term_consequence_mapping"
                ],
                context_requirements=["organizational_goals", "market_context", "risk_tolerance"],
                output_format="strategic_framework"
            )
        }
    
    async def enhance(self, query: str, context: Optional[QueryContext] = None, 
                     tier: Optional[int] = None) -> EnhancedQuery:
        """Main enhancement method with automatic tier selection"""
        
        # Security pre-screening
        security_result = await self.security_scanner.scan(query)
        if security_result.is_blocked:
            return self._create_blocked_response(query, security_result)
        
        # Build or enrich context
        if context is None:
            context = await self.context_builder.build_minimal_context(query)
        
        # Detect query type
        query_type = self._detect_query_type(query, context)
        
        # Select processing tier if not specified
        if tier is None:
            tier = self._select_optimal_tier(query, context, query_type)
        
        # Route to appropriate enhancement method
        enhancement_method = {
            0: self._enhance_offline,
            1: self._enhance_tactical,
            2: self._enhance_strategic
        }.get(tier, self._enhance_offline)
        
        # Perform enhancement
        enhanced = await enhancement_method(query, context, query_type)
        
        # Quality assessment and potential revision
        quality_score = await self.quality_assessor.assess(query, enhanced)
        if quality_score < 0.8 and tier > 0:
            # Try once more with increased scrutiny
            enhanced = await self._revise_enhancement(enhanced, quality_score)
        
        # Add security classifications
        enhanced.security_flags = security_result.flags
        
        return enhanced
    
    def _detect_query_type(self, query: str, context: QueryContext) -> QueryType:
        """Detect the type of query using linguistic patterns and context"""
        query_lower = query.lower()
        
        # Technical indicators
        technical_keywords = ['implement', 'code', 'api', 'system', 'architecture', 
                            'debug', 'optimize', 'algorithm', 'database', 'deployment']
        if any(keyword in query_lower for keyword in technical_keywords):
            return QueryType.TECHNICAL
        
        # Research indicators
        research_keywords = ['research', 'study', 'analyze', 'hypothesis', 'literature',
                           'evidence', 'methodology', 'findings', 'publication']
        if any(keyword in query_lower for keyword in research_keywords):
            return QueryType.RESEARCH
        
        # Creative indicators
        creative_keywords = ['create', 'design', 'imagine', 'story', 'artistic',
                           'innovative', 'novel', 'original', 'aesthetic']
        if any(keyword in query_lower for keyword in creative_keywords):
            return QueryType.CREATIVE
        
        # Analytical indicators
        analytical_keywords = ['analyze', 'compare', 'evaluate', 'measure', 'metric',
                             'data', 'statistics', 'trend', 'correlation']
        if any(keyword in query_lower for keyword in analytical_keywords):
            return QueryType.ANALYTICAL
        
        # Operational indicators
        operational_keywords = ['process', 'procedure', 'workflow', 'task', 'execute',
                              'manage', 'coordinate', 'schedule', 'resource']
        if any(keyword in query_lower for keyword in operational_keywords):
            return QueryType.OPERATIONAL
        
        # Strategic indicators
        strategic_keywords = ['strategy', 'vision', 'goal', 'objective', 'long-term',
                            'roadmap', 'initiative', 'transformation', 'competitive']
        if any(keyword in query_lower for keyword in strategic_keywords):
            return QueryType.STRATEGIC
        
        # Context-based detection
        if context.user.get('role') == 'executive':
            return QueryType.STRATEGIC
        elif context.user.get('role') == 'researcher':
            return QueryType.RESEARCH
        elif context.user.get('role') == 'engineer':
            return QueryType.TECHNICAL
        
        return QueryType.UNKNOWN
    
    def _select_optimal_tier(self, query: str, context: QueryContext, 
                           query_type: QueryType) -> int:
        """Select the optimal processing tier based on multiple factors"""
        
        # Tier 0 (Offline) criteria
        if not context.environment.get('connectivity', True):
            return 0
        if context.security_classification >= SecurityLevel.SECRET:
            return 0  # Sensitive queries stay local
        
        # Calculate complexity score
        complexity = 0.0
        complexity += len(query.split()) / 100.0  # Length factor
        complexity += len(context.history) / 10.0  # History factor
        complexity += 0.2 if query_type in [QueryType.STRATEGIC, QueryType.RESEARCH] else 0
        complexity += 0.3 if '?' in query and query.count('?') > 1 else 0  # Multiple questions
        
        # Tier selection based on complexity
        if complexity < 0.3:
            return 0  # Simple enough for offline
        elif complexity < 0.7:
            return 1  # Tactical enhancement needed
        else:
            return 2  # Full strategic enhancement
    
    async def _enhance_offline(self, query: str, context: QueryContext, 
                              query_type: QueryType) -> EnhancedQuery:
        """Tier 0: Offline enhancement using local models"""
        strategy = self.strategies.get(query_type, self.strategies[QueryType.UNKNOWN])
        
        enhanced_text = query
        trace = ["Offline enhancement initiated"]
        
        # Apply basic enhancement techniques
        for technique in strategy.techniques[:2]:  # Limited techniques offline
            if technique == "specification_extraction":
                enhanced_text = self._extract_specifications(enhanced_text)
                trace.append("Specifications extracted")
            elif technique == "constraint_identification":
                enhanced_text = self._identify_constraints(enhanced_text, context)
                trace.append("Constraints identified")
            elif technique == "hypothesis_clarification":
                enhanced_text = self._clarify_hypothesis(enhanced_text)
                trace.append("Hypothesis clarified")
        
        # Add minimal context
        enhanced_text = self._inject_minimal_context(enhanced_text, context)
        trace.append("Minimal context injected")
        
        return EnhancedQuery(
            original=query,
            enhanced=enhanced_text,
            metadata={
                "query_type": query_type.value,
                "techniques_applied": strategy.techniques[:2],
                "offline_mode": True
            },
            confidence=0.7,  # Lower confidence for offline
            strategy_used=strategy.name,
            processing_tier=0,
            enhancement_trace=trace
        )
    
    async def _enhance_tactical(self, query: str, context: QueryContext,
                               query_type: QueryType) -> EnhancedQuery:
        """Tier 1: Tactical enhancement with online resources"""
        strategy = self.strategies.get(query_type, self.strategies[QueryType.UNKNOWN])
        
        enhanced_text = query
        trace = ["Tactical enhancement initiated"]
        
        # Apply full strategy techniques
        for technique in strategy.techniques:
            enhanced_text = await self._apply_technique(technique, enhanced_text, context)
            trace.append(f"Applied {technique}")
        
        # Enrich with external context (Context7, etc.)
        if context.environment.get('mcp_available', False):
            external_context = await self._fetch_external_context(enhanced_text, query_type)
            enhanced_text = self._merge_external_context(enhanced_text, external_context)
            trace.append("External context integrated")
        
        # Format according to strategy
        enhanced_text = self._format_output(enhanced_text, strategy.output_format)
        trace.append(f"Formatted as {strategy.output_format}")
        
        return EnhancedQuery(
            original=query,
            enhanced=enhanced_text,
            metadata={
                "query_type": query_type.value,
                "techniques_applied": strategy.techniques,
                "external_sources": ["Context7", "MCPTools"],
                "format": strategy.output_format
            },
            confidence=0.85,
            strategy_used=strategy.name,
            processing_tier=1,
            enhancement_trace=trace
        )
    
    async def _enhance_strategic(self, query: str, context: QueryContext,
                                query_type: QueryType) -> EnhancedQuery:
        """Tier 2: Strategic enhancement with multi-agent orchestration"""
        strategy = self.strategies.get(query_type, self.strategies[QueryType.UNKNOWN])
        
        trace = ["Strategic enhancement initiated"]
        
        # Spawn specialized sub-agents
        sub_agents = self._spawn_sub_agents(query_type)
        trace.append(f"Spawned {len(sub_agents)} specialized agents")
        
        # Parallel analysis
        analyses = await asyncio.gather(*[
            agent.analyze(query, context) for agent in sub_agents
        ])
        trace.append("Parallel analysis completed")
        
        # Synthesis phase
        synthesis = await self._synthesize_analyses(analyses, query, context)
        trace.append("Synthesis completed")
        
        # Multi-stage critique and refinement
        for i in range(3):  # Up to 3 refinement rounds
            critique = await self._critique_enhancement(synthesis, query, context)
            if critique.score > 0.95:
                break
            synthesis = await self._refine_based_on_critique(synthesis, critique)
            trace.append(f"Refinement round {i+1} completed")
        
        # Final formatting and enrichment
        final_enhanced = self._apply_strategic_formatting(synthesis, strategy)
        trace.append("Strategic formatting applied")
        
        return EnhancedQuery(
            original=query,
            enhanced=final_enhanced,
            metadata={
                "query_type": query_type.value,
                "techniques_applied": strategy.techniques,
                "sub_agents_used": [agent.name for agent in sub_agents],
                "refinement_rounds": i + 1,
                "synthesis_method": "multi_agent_consensus",
                "format": strategy.output_format
            },
            confidence=0.95,
            strategy_used=strategy.name,
            processing_tier=2,
            enhancement_trace=trace
        )
    
    # Technique implementations (simplified for demonstration)
    def _extract_specifications(self, text: str) -> str:
        """Extract implicit specifications from query"""
        specs = []
        
        # Look for implicit requirements
        if "fast" in text.lower():
            specs.append("Performance requirement: Low latency (<100ms)")
        if "secure" in text.lower():
            specs.append("Security requirement: End-to-end encryption")
        if "scale" in text.lower():
            specs.append("Scalability requirement: Support 10K+ concurrent users")
        
        if specs:
            return f"{text}\n\nExtracted specifications:\n" + "\n".join(f"- {s}" for s in specs)
        return text
    
    def _identify_constraints(self, text: str, context: QueryContext) -> str:
        """Identify constraints from query and context"""
        constraints = []
        
        # Budget constraints
        if context.user.get('organization_size') == 'startup':
            constraints.append("Budget constraint: Optimize for cost-effectiveness")
        
        # Time constraints
        if "urgent" in text.lower() or "asap" in text.lower():
            constraints.append("Time constraint: Required within 24-48 hours")
        
        # Technical constraints
        if context.environment.get('infrastructure') == 'cloud':
            constraints.append("Infrastructure constraint: Cloud-native solution required")
        
        if constraints:
            return f"{text}\n\nIdentified constraints:\n" + "\n".join(f"- {c}" for c in constraints)
        return text
    
    def _inject_minimal_context(self, text: str, context: QueryContext) -> str:
        """Inject minimal context for offline processing"""
        context_items = []
        
        if context.user.get('expertise_level'):
            context_items.append(f"User expertise: {context.user['expertise_level']}")
        
        if context.output_requirements.get('format'):
            context_items.append(f"Preferred format: {context.output_requirements['format']}")
        
        if context_items:
            return f"{text}\n\nContext:\n" + "\n".join(f"- {c}" for c in context_items)
        return text
    
    async def _apply_technique(self, technique: str, text: str, 
                              context: QueryContext) -> str:
        """Apply a specific enhancement technique"""
        # This would implement each technique with appropriate logic
        # Simplified for demonstration
        technique_map = {
            "specification_extraction": self._extract_specifications,
            "constraint_identification": lambda t: self._identify_constraints(t, context),
            "hypothesis_clarification": self._clarify_hypothesis,
            "metric_definition": self._define_metrics,
            "task_decomposition": self._decompose_tasks,
            "objective_hierarchy_construction": self._construct_objective_hierarchy
        }
        
        if technique in technique_map:
            return technique_map[technique](text)
        return text
    
    def _clarify_hypothesis(self, text: str) -> str:
        """Clarify research hypothesis"""
        if "hypothesis" not in text.lower() and "?" in text:
            return f"{text}\n\nResearch framing:\n- Hypothesis: [To be defined based on investigation]\n- Null hypothesis: [Opposite of main hypothesis]\n- Variables: [Independent and dependent variables to examine]"
        return text
    
    def _define_metrics(self, text: str) -> str:
        """Define analytical metrics"""
        return f"{text}\n\nSuggested metrics:\n- Primary KPIs: [Define based on goals]\n- Secondary metrics: [Supporting measurements]\n- Success criteria: [Thresholds for decision-making]"
    
    def _decompose_tasks(self, text: str) -> str:
        """Decompose operational tasks"""
        return f"{text}\n\nTask breakdown:\n1. Initiation phase\n2. Planning phase\n3. Execution phase\n4. Monitoring phase\n5. Closure phase"
    
    def _construct_objective_hierarchy(self, text: str) -> str:
        """Construct strategic objective hierarchy"""
        return f"{text}\n\nObjective hierarchy:\n- Vision: [Long-term aspiration]\n- Mission: [Purpose and approach]\n- Strategic objectives: [3-5 key goals]\n- Tactical objectives: [Supporting goals]\n- KPIs: [Measurable outcomes]"


class SecurityScanner:
    """Scan queries for security issues and policy violations"""
    
    def __init__(self):
        self.sensitive_patterns = [
            r'password|pwd|passwd',
            r'api[_-]?key|apikey',
            r'secret|token|auth',
            r'ssn|social.?security',
            r'credit.?card|cc.?num'
        ]
    
    async def scan(self, query: str) -> 'SecurityResult':
        """Perform security scan on query"""
        flags = []
        is_blocked = False
        
        # Check for PII patterns
        import re
        for pattern in self.sensitive_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                flags.append(f"potential_pii:{pattern}")
        
        # Check for injection attempts
        if any(char in query for char in ['<script', 'DROP TABLE', 'INSERT INTO']):
            flags.append("potential_injection")
            is_blocked = True
        
        # Check for classified markers
        if any(marker in query.upper() for marker in ['TOP SECRET', 'SECRET', 'CONFIDENTIAL']):
            flags.append("classified_content")
        
        return SecurityResult(flags=flags, is_blocked=is_blocked)


@dataclass
class SecurityResult:
    flags: List[str]
    is_blocked: bool


class ContextBuilder:
    """Build query context from available information"""
    
    async def build_minimal_context(self, query: str) -> QueryContext:
        """Build minimal context when full context isn't available"""
        return QueryContext(
            user={"role": "unknown", "expertise_level": "intermediate"},
            task={"type": "general_inquiry"},
            data=[],
            environment={"connectivity": True, "mcp_available": False},
            history=[],
            output_requirements={"format": "structured"},
            feedback=[]
        )


class QualityAssessor:
    """Assess the quality of enhanced queries"""
    
    async def assess(self, original: str, enhanced: EnhancedQuery) -> float:
        """Assess enhancement quality on 0-1 scale"""
        score = 1.0
        
        # Check if enhancement added value
        if enhanced.enhanced == original:
            score -= 0.3
        
        # Check if enhancement is too verbose
        if len(enhanced.enhanced) > len(original) * 5:
            score -= 0.1
        
        # Check if key information preserved
        original_words = set(original.lower().split())
        enhanced_words = set(enhanced.enhanced.lower().split())
        preservation_ratio = len(original_words & enhanced_words) / len(original_words)
        if preservation_ratio < 0.7:
            score -= 0.2
        
        # Boost score for structured enhancements
        if any(marker in enhanced.enhanced for marker in ['\n-', '\n•', '\n1.', ':\n']):
            score += 0.1
        
        return max(0.0, min(1.0, score))


# Example usage
async def demonstrate_enhancement():
    engine = EnhancementEngine()
    
    # Example 1: Technical query
    technical_query = "How do I implement a secure API?"
    context = QueryContext(
        user={"role": "developer", "expertise_level": "intermediate"},
        task={"type": "implementation"},
        data=[],
        environment={"connectivity": True, "mcp_available": True},
        history=[],
        output_requirements={"format": "code_examples"},
        feedback=[]
    )
    
    enhanced = await engine.enhance(technical_query, context)
    print(f"Original: {technical_query}")
    print(f"Enhanced: {enhanced.enhanced}")
    print(f"Confidence: {enhanced.confidence}")
    print(f"Strategy: {enhanced.strategy_used}")
    print(f"Trace: {enhanced.enhancement_trace}")


if __name__ == "__main__":
    asyncio.run(demonstrate_enhancement())
