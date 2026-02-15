"""
AIPEA Market-Specific Configuration Templates
Practical implementation configs for each customer segment
"""

from typing import Dict, Any, List
from enum import Enum
from dataclasses import dataclass, field
import json


class MarketSegment(Enum):
    CONSUMER = "consumer"
    SMALL_BUSINESS = "small_business"
    ENTERPRISE = "enterprise"
    GOVERNMENT = "government"
    DEFENSE = "defense"


@dataclass
class MarketConfig:
    """Configuration template for specific market segment"""
    segment: MarketSegment
    display_name: str
    tagline: str
    base_config: Dict[str, Any]
    ui_config: Dict[str, Any]
    pricing_tier: str
    default_models: List[str]
    hidden_features: List[str] = field(default_factory=list)
    compliance_requirements: List[str] = field(default_factory=list)


class MarketConfigurationManager:
    """Manages market-specific configurations for AIPEA"""
    
    def __init__(self):
        self.configs = self._initialize_market_configs()
    
    def _initialize_market_configs(self) -> Dict[MarketSegment, MarketConfig]:
        """Initialize all market-specific configurations"""
        
        configs = {}
        
        # Consumer Configuration
        configs[MarketSegment.CONSUMER] = MarketConfig(
            segment=MarketSegment.CONSUMER,
            display_name="AIPEA Personal",
            tagline="Your AI-Powered Writing & Research Assistant",
            base_config={
                "system": {
                    "deployment": {
                        "environment": "cloud",
                        "tier": "cloud",
                        "region": "auto",
                        "classification": "UNCLASSIFIED"
                    }
                },
                "agent": {
                    "capabilities": {
                        "max_concurrent_requests": 1,
                        "timeout_seconds": 30,
                        "retry_policy": {
                            "max_retries": 2,
                            "backoff_multiplier": 1.5
                        }
                    }
                },
                "models": {
                    "tactical": {
                        "primary": {
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "temperature": 0.7,
                            "max_tokens": 2048
                        }
                    }
                },
                "routing": {
                    "complexity_thresholds": {
                        "offline_max": 0.5,
                        "tactical_max": 1.0,
                        "strategic_min": 2.0  # Effectively disabled
                    },
                    "cost_controls": {
                        "daily_budget_usd": 1.0,
                        "per_query_limit_usd": 0.10,
                        "fallback_on_budget_exceeded": True
                    }
                },
                "enhancement_strategies": {
                    "technical": {"enabled": True, "priority": 3},
                    "creative": {"enabled": True, "priority": 5},
                    "research": {"enabled": True, "priority": 4}
                },
                "security": {
                    "input_validation": {
                        "max_query_length": 2000,
                        "pii_detection": {"enabled": True}
                    }
                },
                "monitoring": {
                    "metrics": {"enabled": False},  # Privacy-focused
                    "logging": {
                        "level": "error",
                        "destinations": ["file"]
                    }
                }
            },
            ui_config={
                "interface_mode": "simple",
                "welcome_message": "Hi! I'm here to help with writing, research, and answering questions. What can I do for you today?",
                "example_queries": [
                    "Help me write a professional email",
                    "Explain blockchain in simple terms",
                    "Plan a healthy meal for the week",
                    "Debug this code snippet"
                ],
                "features_exposed": [
                    "chat", "write", "research", "explain"
                ],
                "simplified_options": {
                    "response_style": ["concise", "detailed", "creative"],
                    "expertise_level": ["beginner", "intermediate", "expert"]
                },
                "hide_technical_details": True,
                "show_token_usage": False
            },
            pricing_tier="personal",
            default_models=["gpt-4o-mini", "claude-haiku"],
            hidden_features=[
                "multi_agent_coordination",
                "security_classification", 
                "offline_knowledge_base",
                "mcp_integration",
                "audit_trail"
            ],
            compliance_requirements=["GDPR", "CCPA"]
        )
        
        # Small Business Configuration
        configs[MarketSegment.SMALL_BUSINESS] = MarketConfig(
            segment=MarketSegment.SMALL_BUSINESS,
            display_name="AIPEA Business",
            tagline="Smart AI Assistant for Growing Businesses",
            base_config={
                "system": {
                    "deployment": {
                        "environment": "cloud",
                        "tier": "hybrid",
                        "region": "us-east-1",
                        "classification": "UNCLASSIFIED"
                    }
                },
                "agent": {
                    "capabilities": {
                        "max_concurrent_requests": 10,
                        "timeout_seconds": 60,
                        "retry_policy": {
                            "max_retries": 3,
                            "backoff_multiplier": 2.0
                        }
                    }
                },
                "models": {
                    "offline": {
                        "primary": {
                            "name": "llama-3.2-8b",
                            "path": "/models/llama-3.2-8b-q5.gguf",
                            "context_length": 4096
                        }
                    },
                    "tactical": {
                        "primary": {
                            "provider": "anthropic",
                            "model": "claude-3-sonnet-20240229",
                            "temperature": 0.3,
                            "max_tokens": 4096
                        },
                        "fallback": {
                            "provider": "openai",
                            "model": "gpt-4o",
                            "temperature": 0.3
                        }
                    }
                },
                "routing": {
                    "complexity_thresholds": {
                        "offline_max": 0.3,
                        "tactical_max": 0.8,
                        "strategic_min": 0.9
                    },
                    "cost_controls": {
                        "daily_budget_usd": 10.0,
                        "per_query_limit_usd": 0.50,
                        "fallback_on_budget_exceeded": True
                    }
                },
                "enhancement_strategies": {
                    "technical": {"enabled": True, "priority": 4},
                    "operational": {"enabled": True, "priority": 5},
                    "analytical": {"enabled": True, "priority": 5}
                },
                "security": {
                    "input_validation": {
                        "max_query_length": 5000,
                        "pii_detection": {"enabled": True}
                    },
                    "compliance": {
                        "gdpr": {"enabled": True},
                        "pci_dss": {"enabled": False}  # Optional
                    }
                },
                "knowledge_base": {
                    "offline": {
                        "storage_tier": "compact",
                        "domains": ["business", "technical", "general"]
                    }
                },
                "monitoring": {
                    "metrics": {
                        "enabled": True,
                        "export_interval_seconds": 300
                    },
                    "logging": {
                        "level": "info",
                        "destinations": ["file", "cloudwatch"]
                    }
                }
            },
            ui_config={
                "interface_mode": "professional",
                "welcome_message": "Welcome to AIPEA Business! How can I help your business today?",
                "example_queries": [
                    "Draft a proposal for a new client",
                    "Analyze last month's sales data",
                    "Create social media content for our product launch",
                    "Generate customer service response templates"
                ],
                "features_exposed": [
                    "chat", "write", "analyze", "create", "optimize", "integrate"
                ],
                "business_tools": {
                    "templates": ["proposal", "invoice", "email", "report"],
                    "integrations": ["csv_import", "basic_api"],
                    "collaboration": ["share_results", "export_formats"]
                },
                "show_cost_estimate": True,
                "show_processing_time": True
            },
            pricing_tier="business",
            default_models=["gpt-4o", "claude-sonnet", "llama-3.2"],
            hidden_features=[
                "security_classification",
                "multi_agent_coordination",
                "compliance_engine"
            ],
            compliance_requirements=["GDPR", "CCPA", "SOC2-Type1"]
        )
        
        # Enterprise Configuration
        configs[MarketSegment.ENTERPRISE] = MarketConfig(
            segment=MarketSegment.ENTERPRISE,
            display_name="AIPEA Enterprise",
            tagline="Enterprise AI Platform for Digital Transformation",
            base_config={
                "system": {
                    "deployment": {
                        "environment": "prod",
                        "tier": "hybrid",
                        "region": "multi-region",
                        "classification": "UNCLASSIFIED"
                    }
                },
                "agent": {
                    "identity": {
                        "id": "enterprise_deployment_001",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "max_concurrent_requests": 500,
                        "timeout_seconds": 120,
                        "retry_policy": {
                            "max_retries": 5,
                            "backoff_multiplier": 2.0
                        }
                    }
                },
                "models": {
                    # Full model configuration
                    "offline": {
                        "primary": {
                            "name": "llama-3.3-70b",
                            "path": "/models/llama-3.3-70b-q4.gguf",
                            "quantization": "q4_0",
                            "context_length": 16384,
                            "gpu_layers": 35
                        },
                        "fallback": {
                            "name": "mixtral-8x7b",
                            "path": "/models/mixtral-8x7b-q4.gguf"
                        }
                    },
                    "tactical": {
                        "primary": {
                            "provider": "anthropic",
                            "model": "claude-3-opus-20240229",
                            "temperature": 0.2,
                            "max_tokens": 8192
                        },
                        "fallback": {
                            "provider": "openai",
                            "model": "gpt-4-turbo",
                            "temperature": 0.2
                        }
                    },
                    "strategic": {
                        "coordinator": {
                            "model": "claude-3-opus-20240229",
                            "agent_configs": [
                                {"role": "analyst", "model": "claude-3-sonnet"},
                                {"role": "builder", "model": "gpt-4"},
                                {"role": "specialist", "model": "domain-specific"},
                                {"role": "validator", "model": "claude-3-opus"}
                            ]
                        }
                    }
                },
                "routing": {
                    "complexity_thresholds": {
                        "offline_max": 0.3,
                        "tactical_max": 0.7,
                        "strategic_min": 0.7
                    },
                    "forced_routing": {
                        "security_sensitive": "tactical",
                        "high_priority": "strategic"
                    },
                    "cost_controls": {
                        "daily_budget_usd": 1000.0,
                        "per_query_limit_usd": 5.00,
                        "fallback_on_budget_exceeded": False
                    }
                },
                "enhancement_strategies": {
                    # All strategies enabled
                    "technical": {"enabled": True, "priority": 5},
                    "research": {"enabled": True, "priority": 5},
                    "creative": {"enabled": True, "priority": 4},
                    "analytical": {"enabled": True, "priority": 5},
                    "operational": {"enabled": True, "priority": 5},
                    "strategic": {"enabled": True, "priority": 5}
                },
                "security": {
                    "input_validation": {
                        "max_query_length": 50000,
                        "blocked_patterns": [
                            "system prompt override",
                            "ignore instructions",
                            "DROP TABLE",
                            "</script>"
                        ],
                        "pii_detection": {
                            "enabled": True,
                            "patterns": ["ssn", "credit_card", "api_key"]
                        }
                    },
                    "compliance": {
                        "soc2": {"enabled": True},
                        "iso27001": {"enabled": True},
                        "hipaa": {"enabled": False},  # Industry-specific
                        "gdpr": {"enabled": True}
                    }
                },
                "knowledge_base": {
                    "offline": {
                        "storage_tier": "extended",
                        "domains": ["technical", "business", "industry", "company"],
                        "sync_policy": {
                            "frequency": "hourly",
                            "conflict_resolution": "newest_wins"
                        }
                    }
                },
                "mcp_integration": {
                    "enabled": True,
                    "servers": [
                        {
                            "name": "enterprise_data",
                            "url": "mcp://internal.company.com",
                            "transport": "http"
                        }
                    ]
                },
                "monitoring": {
                    "metrics": {
                        "enabled": True,
                        "export_interval_seconds": 60,
                        "retention_days": 90
                    },
                    "logging": {
                        "level": "info",
                        "structured": True,
                        "destinations": ["elasticsearch", "cloudwatch", "splunk"]
                    },
                    "tracing": {
                        "enabled": True,
                        "sampling_rate": 0.1,
                        "exporter": "datadog"
                    }
                },
                "feature_flags": {
                    "experimental": {
                        "multimodal_input": True,
                        "voice_interface": False,
                        "predictive_enhancement": True
                    }
                }
            },
            ui_config={
                "interface_mode": "advanced",
                "customizable_dashboard": True,
                "role_based_access": True,
                "features_exposed": "all",
                "enterprise_features": {
                    "sso_integration": True,
                    "team_workspaces": True,
                    "custom_models": True,
                    "api_management": True,
                    "usage_analytics": True,
                    "compliance_reporting": True
                },
                "white_label_options": {
                    "custom_branding": True,
                    "custom_domain": True,
                    "custom_ui_theme": True
                }
            },
            pricing_tier="enterprise",
            default_models=["gpt-4", "claude-opus", "custom-fine-tuned"],
            hidden_features=[],  # All features available
            compliance_requirements=["SOC2", "ISO27001", "GDPR", "CCPA"]
        )
        
        # Government Configuration
        configs[MarketSegment.GOVERNMENT] = MarketConfig(
            segment=MarketSegment.GOVERNMENT,
            display_name="AIPEA GovCloud",
            tagline="Secure AI for Government Excellence",
            base_config={
                "system": {
                    "deployment": {
                        "environment": "gov",
                        "tier": "hybrid",
                        "region": "us-gov-west-1",
                        "classification": "CUI"  # Controlled Unclassified Information
                    }
                },
                # Similar structure to Enterprise but with government-specific settings
                "agent": {
                    "identity": {
                        "id": "govcloud_deployment_001",
                        "version": "1.0.0-fedramp"
                    },
                    "capabilities": {
                        "max_concurrent_requests": 200,
                        "timeout_seconds": 90,
                        "retry_policy": {
                            "max_retries": 3,
                            "backoff_multiplier": 2.0
                        }
                    }
                },
                # Government-specific model configuration
                "models": {
                    "offline": {
                        "primary": {
                            "name": "llama-3.3-70b-gov",
                            "path": "/secure/models/llama-3.3-70b-q4.gguf",
                            "context_length": 8192,
                            "gpu_layers": 35
                        }
                    },
                    "tactical": {
                        "primary": {
                            "provider": "azure-gov",
                            "model": "gpt-4-gov",
                            "temperature": 0.1,
                            "max_tokens": 4096
                        }
                    }
                },
                "security": {
                    "input_validation": {
                        "max_query_length": 20000,
                        "blocked_patterns": [
                            "classified",
                            "top secret",
                            "bypass security"
                        ]
                    },
                    "compliance": {
                        "fedramp": {
                            "enabled": True,
                            "level": "moderate"  # or "high" for some agencies
                        },
                        "fisma": {"enabled": True},
                        "itar": {"enabled": False}  # Only for defense-related
                    },
                    "audit_trail": {
                        "enabled": True,
                        "retention_days": 2555,  # 7 years
                        "tamper_proof": True
                    }
                },
                "knowledge_base": {
                    "offline": {
                        "storage_tier": "standard",
                        "domains": ["government", "policy", "regulatory", "general"],
                        "data_residency": "us-only"
                    }
                },
                "monitoring": {
                    "metrics": {
                        "enabled": True,
                        "export_interval_seconds": 60,
                        "retention_days": 2555
                    },
                    "logging": {
                        "level": "info",
                        "structured": True,
                        "destinations": ["gov-cloudwatch", "splunk-gov"],
                        "encryption": "fips-140-2"
                    }
                }
            },
            ui_config={
                "interface_mode": "government",
                "accessibility_compliance": "508",
                "features_exposed": [
                    "citizen_services",
                    "policy_analysis",
                    "report_generation",
                    "data_analysis",
                    "compliance_checking"
                ],
                "government_features": {
                    "case_management": True,
                    "foia_support": True,
                    "multi_language": True,
                    "accessibility_features": "wcag-2.1-aa"
                }
            },
            pricing_tier="government",
            default_models=["gpt-4-gov", "llama-gov"],
            hidden_features=["experimental_features"],
            compliance_requirements=["FedRAMP-Moderate", "FISMA", "Section-508"]
        )
        
        # Defense Configuration (keeping most original features)
        configs[MarketSegment.DEFENSE] = MarketConfig(
            segment=MarketSegment.DEFENSE,
            display_name="AIPEA Defense",
            tagline="Mission-Critical AI for National Security",
            base_config={
                # Use the original military-focused configuration
                # This is where all the current documentation fits perfectly
                "system": {
                    "deployment": {
                        "environment": "tactical",
                        "tier": "disconnected",
                        "region": "classified",
                        "classification": "SECRET"
                    }
                },
                # ... (rest of the original configuration)
            },
            ui_config={
                "interface_mode": "tactical",
                "classification_banners": True,
                "features_exposed": "all",
                "tactical_features": {
                    "offline_priority": True,
                    "field_mode": True,
                    "satellite_fallback": True,
                    "mesh_network": True
                }
            },
            pricing_tier="defense",
            default_models=["llama-3.3-70b", "secure-models"],
            hidden_features=[],
            compliance_requirements=["FedRAMP-High", "DISA-SRG", "ITAR", "Cross-Domain"]
        )
        
        return configs
    
    def get_config_for_segment(self, segment: MarketSegment) -> MarketConfig:
        """Get configuration for specific market segment"""
        return self.configs.get(segment)
    
    def generate_config_file(self, segment: MarketSegment, output_format: str = "yaml") -> str:
        """Generate configuration file for specific segment"""
        config = self.get_config_for_segment(segment)
        
        if output_format == "yaml":
            import yaml
            return yaml.dump(config.base_config, default_flow_style=False)
        elif output_format == "json":
            return json.dumps(config.base_config, indent=2)
        else:
            raise ValueError(f"Unsupported format: {output_format}")
    
    def get_pricing_table(self) -> Dict[str, Any]:
        """Generate pricing table for all segments"""
        return {
            "consumer": {
                "free": {
                    "name": "AIPEA Free",
                    "price": "$0",
                    "queries": "50/month",
                    "models": "Basic",
                    "support": "Community"
                },
                "personal": {
                    "name": "AIPEA Personal",
                    "price": "$9.99/month",
                    "queries": "1,000/month",
                    "models": "GPT-4-mini, Claude Haiku",
                    "support": "Email"
                }
            },
            "small_business": {
                "starter": {
                    "name": "Business Starter",
                    "price": "$49/month",
                    "queries": "5,000/month",
                    "models": "GPT-4, Claude Sonnet",
                    "support": "Priority Email",
                    "users": "Up to 5"
                },
                "growth": {
                    "name": "Business Growth",
                    "price": "$199/month",
                    "queries": "20,000/month",
                    "models": "All models",
                    "support": "Phone + Email",
                    "users": "Up to 20"
                }
            },
            "enterprise": {
                "name": "Enterprise",
                "price": "Custom",
                "queries": "Unlimited",
                "models": "All + Custom",
                "support": "Dedicated Success Manager",
                "features": ["SLA", "Custom Integration", "White Label"]
            },
            "government": {
                "name": "GovCloud",
                "price": "GSA Schedule",
                "queries": "Based on contract",
                "models": "FedRAMP Approved",
                "support": "24/7 US-Based",
                "compliance": "FedRAMP, FISMA"
            },
            "defense": {
                "name": "Defense",
                "price": "Contract Vehicle",
                "queries": "Mission-Based",
                "models": "Secure + Offline",
                "support": "On-Site Available",
                "compliance": "Full Classification Support"
            }
        }


# Example Usage
if __name__ == "__main__":
    manager = MarketConfigurationManager()
    
    # Generate consumer configuration
    consumer_config = manager.get_config_for_segment(MarketSegment.CONSUMER)
    print(f"Consumer Config: {consumer_config.display_name}")
    print(f"Tagline: {consumer_config.tagline}")
    print(f"Hidden Features: {consumer_config.hidden_features}")
    
    # Generate configuration file for small business
    smb_config_yaml = manager.generate_config_file(MarketSegment.SMALL_BUSINESS, "yaml")
    print("\nSmall Business Config (YAML):")
    print(smb_config_yaml[:500] + "...")  # First 500 chars
    
    # Get pricing table
    pricing = manager.get_pricing_table()
    print("\nPricing Summary:")
    for segment, tiers in pricing.items():
        print(f"\n{segment.upper()}:")
        if isinstance(tiers, dict) and 'name' not in tiers:
            for tier_name, tier_info in tiers.items():
                print(f"  - {tier_info['name']}: {tier_info['price']}")
        else:
            print(f"  - {tiers['name']}: {tiers['price']}")
