#!/usr/bin/env python3
"""AIPEA Security Context Module - Security and compliance handling for AI query processing.

This module implements security screening and compliance mode handling for the
AI Prompt Engineer Agent (AIPEA) integration with Agora IV. It provides:

- Security level classification (UNCLASSIFIED to TOP_SECRET)
- Compliance modes (General, HIPAA, Tactical, FedRAMP)
- PII/PHI detection and handling
- Classified content marker detection
- Prompt injection attack prevention
- Mode-specific model restrictions

Based on Agora V AIPEA security patterns, adapted for Agora IV production.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

logger = logging.getLogger(__name__)

# Explicitly forbidden models (global policy)
FORBIDDEN_MODEL_SUBSTRINGS = ("gpt-4o", "gpt-4o-mini")


# =============================================================================
# ENUMS
# =============================================================================


class SecurityLevel(Enum):
    """Security classification levels.

    Determines the sensitivity of content and applicable handling rules.
    Higher levels require stricter controls and may force offline processing.
    """

    UNCLASSIFIED = 0  # Public/general information
    SENSITIVE = 1  # General business sensitive
    CUI = 2  # Controlled Unclassified Information
    SECRET = 3  # Classified - requires clearance
    TOP_SECRET = 4  # Highest classification


class ComplianceMode(Enum):
    """Compliance/regulatory modes for data handling.

    Each mode has specific requirements for:
    - Audit retention periods
    - Encryption requirements
    - Allowed AI models
    - Data handling procedures
    """

    GENERAL = "general"  # Standard use - minimal restrictions
    HIPAA = "hipaa"  # Medical/PHI handling - requires BAA-covered models
    TACTICAL = "tactical"  # Military/Defense - local models only, air-gapped
    FEDRAMP = "fedramp"  # Government cloud - future implementation


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class SecurityContext:
    """Security context for a request.

    Encapsulates all security-related settings for processing a query,
    including compliance mode, classification level, and operational constraints.

    Attributes:
        compliance_mode: Active compliance framework (GENERAL, HIPAA, TACTICAL, FEDRAMP)
        security_level: Classification level of the content being processed
        has_connectivity: Whether external network access is available/allowed
        audit_required: Whether detailed audit logging is required
        data_residency: Geographic restriction for data processing (e.g., "US", "EU")
        allowed_models: List of permitted AI models for this context
        blocked_patterns: Additional patterns to block beyond defaults
    """

    compliance_mode: ComplianceMode = ComplianceMode.GENERAL
    security_level: SecurityLevel = SecurityLevel.UNCLASSIFIED
    has_connectivity: bool = True
    audit_required: bool = False
    data_residency: str | None = None
    allowed_models: list[str] = field(default_factory=list)
    blocked_patterns: list[str] = field(default_factory=list)

    def is_classified(self) -> bool:
        """Check if content is classified (SECRET or above).

        Returns:
            True if security level is SECRET or TOP_SECRET
        """
        return self.security_level.value >= SecurityLevel.SECRET.value

    def requires_offline(self) -> bool:
        """Check if context requires offline/air-gapped processing.

        Returns:
            True if offline processing is required
        """
        return (
            not self.has_connectivity
            or self.is_classified()
            or self.compliance_mode == ComplianceMode.TACTICAL
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with all security context fields
        """
        return {
            "compliance_mode": self.compliance_mode.value,
            "security_level": self.security_level.name,
            "has_connectivity": self.has_connectivity,
            "audit_required": self.audit_required,
            "data_residency": self.data_residency,
            "allowed_models": self.allowed_models,
            "blocked_patterns": self.blocked_patterns,
        }


@dataclass
class ScanResult:
    """Result of security scan.

    Contains flags for detected security concerns and whether
    the query should be blocked from processing.

    Attributes:
        flags: List of security flags detected (e.g., "pii_detected:ssn")
        is_blocked: Whether the query should be blocked from processing
    """

    flags: list[str] = field(default_factory=list)
    is_blocked: bool = False
    force_offline: bool = False  # Signal that processing should be offline

    def has_flags(self) -> bool:
        """Check if any flags were raised.

        Returns:
            True if any security flags were detected
        """
        return len(self.flags) > 0

    def has_pii(self) -> bool:
        """Check if PII was detected.

        Returns:
            True if any PII flags were raised
        """
        return any(f.startswith("pii_detected:") for f in self.flags)

    def has_phi(self) -> bool:
        """Check if PHI was detected.

        Returns:
            True if any PHI flags were raised
        """
        return any(f.startswith("phi_detected:") for f in self.flags)

    def has_classified_content(self) -> bool:
        """Check if classified content markers were detected.

        Returns:
            True if any classified markers were found
        """
        return any(f.startswith("classified_marker:") for f in self.flags)

    def has_injection_attempt(self) -> bool:
        """Check if injection attempts were detected.

        Returns:
            True if injection attempts were found
        """
        return "injection_attempt" in self.flags

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with scan result fields
        """
        return {
            "flags": self.flags,
            "is_blocked": self.is_blocked,
            "has_pii": self.has_pii(),
            "has_phi": self.has_phi(),
            "has_classified": self.has_classified_content(),
            "has_injection": self.has_injection_attempt(),
        }


# =============================================================================
# SECURITY SCANNER
# =============================================================================


class SecurityScanner:
    """Pre-screening for PII, classified content, and injection attacks.

    Scans queries for security-sensitive content based on the active
    compliance mode. Different modes enable different pattern sets:

    - GENERAL: PII patterns + injection patterns
    - HIPAA: PII + PHI patterns + injection patterns
    - TACTICAL: PII + classified markers + injection patterns (forces offline)

    Injection attempts are always blocked regardless of mode.
    """

    # PII patterns - always checked
    PII_PATTERNS: ClassVar[dict[str, str]] = {
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
        "api_key": r"\b(sk-|api[_-]?key|bearer\s+)[a-zA-Z0-9]{20,}\b",
        "password": r"(password|passwd|pwd)\s*[:=]\s*\S+",
    }

    # HIPAA-specific PHI patterns - only checked in HIPAA mode
    PHI_PATTERNS: ClassVar[dict[str, str]] = {
        "mrn": r"\b(MRN|medical record)\s*[:=]?\s*\d+\b",
        "dob": r"\b(DOB|date of birth)\s*[:=]?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        "patient_name": r"\bpatient\s*[:=]?\s*[A-Z][a-z]+\s+[A-Z][a-z]+\b",
    }

    # Classified content markers - only checked in TACTICAL mode
    CLASSIFIED_MARKERS: ClassVar[list[str]] = [
        "TOP SECRET",
        "SECRET",
        "CONFIDENTIAL",
        "NOFORN",
        "SCI",
    ]

    # Injection patterns - always checked and always blocked
    INJECTION_PATTERNS: ClassVar[list[str]] = [
        r"ignore\s+(previous|all)\s+instructions",
        r"</?(system|user|assistant)>",
        r"\[/?(system|user|assistant|human)\]",  # Bracket-style role tags
        r"\n(?:Human|Assistant|System)\s*:",  # Conversation separator injection
        r"DROP\s+TABLE",
        r"UNION\s+SELECT",
        r"\{\{.*\}\}",  # Template injection
        r"<script[^>]*>",  # XSS attempt
    ]

    def __init__(self) -> None:
        """Initialize the security scanner with compiled regex patterns."""
        self._compiled_pii: dict[str, re.Pattern[str]] = {
            name: re.compile(pattern, re.IGNORECASE) for name, pattern in self.PII_PATTERNS.items()
        }
        self._compiled_phi: dict[str, re.Pattern[str]] = {
            name: re.compile(pattern, re.IGNORECASE) for name, pattern in self.PHI_PATTERNS.items()
        }
        self._compiled_injection: list[re.Pattern[str]] = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.INJECTION_PATTERNS
        ]
        logger.debug("SecurityScanner initialized with %d PII patterns", len(self.PII_PATTERNS))

    # Maximum pattern length to prevent ReDoS attacks
    _MAX_PATTERN_LENGTH: ClassVar[int] = 200

    # Dangerous patterns that can cause catastrophic backtracking
    _DANGEROUS_PATTERNS: ClassVar[list[str]] = [
        r"\(\.\*\)\+",  # Nested .* with quantifier
        r"\(\.\+\)\+",  # Nested .+ with quantifier
        r"\\[1-9].*[+*]|[+*].*\\[1-9]",  # Backreference with quantifier
        r"\(\.\*\?\)\+",  # Nested .*? with quantifier
        r"\+\+",  # Possessive-like patterns that cause issues
        r"\*\*",  # Double quantifier
        r"\{\d+,\}\{\d+,\}",  # Multiple unbounded quantifiers
    ]

    def _is_regex_safe(self, pattern: str) -> bool:
        """Check if a regex pattern is safe from ReDoS attacks.

        Validates patterns to prevent Regular Expression Denial of Service (ReDoS)
        attacks that can cause catastrophic backtracking.

        Args:
            pattern: The regex pattern to validate

        Returns:
            True if the pattern is considered safe, False otherwise
        """
        # Check pattern length
        if len(pattern) > self._MAX_PATTERN_LENGTH:
            logger.debug(
                "Pattern rejected: exceeds max length (%d > %d)",
                len(pattern),
                self._MAX_PATTERN_LENGTH,
            )
            return False

        # Check for dangerous patterns that can cause catastrophic backtracking
        for dangerous in self._DANGEROUS_PATTERNS:
            try:
                if re.search(dangerous, pattern):
                    logger.debug("Pattern rejected: contains dangerous construct '%s'", dangerous)
                    return False
            except re.error:
                # If we can't even check for the dangerous pattern, skip
                pass

        # Check for nested quantifiers like (a+)+ or (a*)*
        # These are common causes of ReDoS
        nested_quantifier_pattern = r"\([^)]*[+*?][^)]*\)[+*?]|\([^)]*[+*?][^)]*\)\{[^}]+\}"
        if re.search(nested_quantifier_pattern, pattern):
            logger.debug("Pattern rejected: contains nested quantifiers")
            return False

        # Check for overlapping alternatives with quantifiers
        # E.g., (a|a?)+ which can cause exponential backtracking
        overlapping_pattern = r"\([^|]+\|[^)]+\?\)[+*]"
        if re.search(overlapping_pattern, pattern):
            logger.debug("Pattern rejected: contains overlapping alternatives with quantifiers")
            return False

        # Try to compile the pattern to catch syntax errors
        try:
            re.compile(pattern)
        except re.error as e:
            logger.debug("Pattern rejected: compilation failed: %s", e)
            return False

        return True

    def _check_pii(self, query: str) -> list[str]:
        """Check for PII patterns. Always runs.

        Args:
            query: The query text to scan

        Returns:
            List of PII flags detected
        """
        flags: list[str] = []
        for name, pattern in self._compiled_pii.items():
            if pattern.search(query):
                flags.append(f"pii_detected:{name}")
                logger.warning("PII detected in query: %s", name)
        return flags

    def _check_phi(self, query: str) -> list[str]:
        """Check PHI patterns (HIPAA mode only).

        Args:
            query: The query text to scan

        Returns:
            List of PHI flags detected
        """
        flags: list[str] = []
        for name, pattern in self._compiled_phi.items():
            if pattern.search(query):
                flags.append(f"phi_detected:{name}")
                logger.warning("PHI detected in HIPAA mode: %s", name)
        return flags

    def _check_classified_markers(self, query: str) -> tuple[list[str], bool]:
        """Check classified markers (TACTICAL mode).

        Args:
            query: The query text to scan

        Returns:
            Tuple of (flags, force_offline)
        """
        flags: list[str] = []
        force_offline = False
        query_upper = query.upper()
        for marker in self.CLASSIFIED_MARKERS:
            if re.search(rf"\b{re.escape(marker)}\b", query_upper):
                flags.append(f"classified_marker:{marker}")
                force_offline = True
                logger.warning("Classified marker detected, forcing offline: %s", marker)
        return flags, force_offline

    def _check_injection(self, query: str) -> tuple[list[str], bool]:
        """Check injection patterns. Always runs.

        Args:
            query: The query text to scan

        Returns:
            Tuple of (flags, is_blocked)
        """
        for pattern in self._compiled_injection:
            if pattern.search(query):
                logger.error("Injection attempt detected and blocked")
                return ["injection_attempt"], True
        return [], False

    def _check_custom_patterns(
        self, query: str, blocked_patterns: list[str]
    ) -> tuple[list[str], bool]:
        """Check custom blocked patterns.

        Args:
            query: The query text to scan
            blocked_patterns: List of custom regex patterns to check

        Returns:
            Tuple of (flags, is_blocked)
        """
        flags: list[str] = []
        is_blocked = False
        for custom_pattern in blocked_patterns:
            if not self._is_regex_safe(custom_pattern):
                logger.warning(
                    "Rejected potentially unsafe custom pattern: %s", custom_pattern[:20]
                )
                continue
            try:
                if re.search(custom_pattern, query, re.IGNORECASE):
                    flags.append(f"custom_blocked:{custom_pattern[:20]}")
                    is_blocked = True
                    logger.warning("Custom blocked pattern matched: %s", custom_pattern[:20])
            except re.error as e:
                logger.error("Invalid custom pattern '%s': %s", custom_pattern[:20], e)
        return flags, is_blocked

    def scan(self, query: str, context: SecurityContext) -> ScanResult:
        """Scan query for security issues based on compliance mode.

        Args:
            query: The query text to scan
            context: Security context determining which patterns to check

        Returns:
            ScanResult with detected flags and blocking decision
        """
        flags: list[str] = []
        is_blocked = False
        force_offline = False

        # Always check PII patterns
        flags.extend(self._check_pii(query))

        # Check PHI patterns only in HIPAA mode
        if context.compliance_mode == ComplianceMode.HIPAA:
            flags.extend(self._check_phi(query))

        # Check classified markers only in TACTICAL mode
        if context.compliance_mode == ComplianceMode.TACTICAL:
            classified_flags, force_offline = self._check_classified_markers(query)
            flags.extend(classified_flags)

        # Always check injection patterns - these are always blocked
        injection_flags, injection_blocked = self._check_injection(query)
        flags.extend(injection_flags)
        is_blocked = is_blocked or injection_blocked

        # Check custom blocked patterns from context
        custom_flags, custom_blocked = self._check_custom_patterns(query, context.blocked_patterns)
        flags.extend(custom_flags)
        is_blocked = is_blocked or custom_blocked

        result = ScanResult(flags=flags, is_blocked=is_blocked, force_offline=force_offline)

        if result.has_flags():
            logger.info("Security scan complete: %d flags, blocked=%s", len(flags), is_blocked)

        return result


# =============================================================================
# COMPLIANCE HANDLER
# =============================================================================


class ComplianceHandler:
    """Handles compliance-specific requirements for different regulatory modes.

    Configures operational parameters based on compliance mode:

    - GENERAL: Minimal restrictions, 90-day audit retention
    - HIPAA: 6-year retention, PHI redaction, BAA-covered models only
    - TACTICAL: 7-year retention, local models only, forced offline
    - FEDRAMP: (Future) Government cloud requirements

    Attributes:
        mode: Active compliance mode
        audit_retention_days: Required audit log retention period
        encryption_required: Whether encryption is mandatory
        allowed_models: List of permitted AI models
        phi_redaction_enabled: Whether PHI must be redacted
        force_offline: Whether external connectivity is prohibited
    """

    def __init__(self, mode: ComplianceMode) -> None:
        """Initialize compliance handler for the specified mode.

        Args:
            mode: Compliance mode to configure for
        """
        self.mode = mode
        self.audit_retention_days: int = 90
        self.encryption_required: bool = False
        self.allowed_models: list[str] = []
        self.phi_redaction_enabled: bool = False
        self.force_offline: bool = False

        self._configure_for_mode()
        logger.info("ComplianceHandler initialized for mode: %s", mode.value)

    def _configure_for_mode(self) -> None:
        """Configure handler parameters based on compliance mode."""
        if self.mode == ComplianceMode.HIPAA:
            # HIPAA: 6-year retention (2190 days), PHI protection, BAA-covered models
            self.audit_retention_days = 2190  # 6 years per HIPAA requirements
            self.encryption_required = True
            self.allowed_models = [
                "claude-opus-4-6",
                "claude-opus-4-5",
                "gpt-5.2",
            ]  # BAA-covered model families (prefix match via substring)
            self.phi_redaction_enabled = True
            logger.debug("Configured for HIPAA: 6yr retention, PHI redaction enabled")

        elif self.mode == ComplianceMode.TACTICAL:
            # TACTICAL: 7-year retention, local models only, air-gapped
            self.audit_retention_days = 2555  # 7 years per DoD requirements
            self.encryption_required = True
            self.allowed_models = ["llama-3.3-70b"]  # Local SLM only
            self.phi_redaction_enabled = False
            self.force_offline = True
            logger.debug("Configured for TACTICAL: 7yr retention, offline forced")

        elif self.mode == ComplianceMode.FEDRAMP:
            # FEDRAMP: Government cloud requirements (future implementation)
            self.audit_retention_days = 1095  # 3 years minimum for FedRAMP
            self.encryption_required = True
            self.allowed_models = [
                "claude-opus-4-6",
                "claude-opus-4-5",
                "gpt-5.2",
            ]  # FedRAMP authorized model families (prefix match via substring)
            self.phi_redaction_enabled = False
            logger.debug("Configured for FEDRAMP: 3yr retention, encryption required")

        else:  # GENERAL
            # GENERAL: Standard use with minimal restrictions
            self.audit_retention_days = 90
            self.encryption_required = False
            self.allowed_models = []  # Empty means all allowed
            self.phi_redaction_enabled = False
            logger.debug("Configured for GENERAL: 90-day retention, no restrictions")

    def validate_model(self, model_id: str) -> bool:
        """Check if a model is allowed for this compliance mode.

        Args:
            model_id: The model identifier to validate (e.g., "claude-3-opus-20240229")

        Returns:
            True if the model is allowed, False otherwise

        Note:
            An empty allowed_models list means all models are permitted.
        """
        model_lower = model_id.lower()
        for forbidden in FORBIDDEN_MODEL_SUBSTRINGS:
            if forbidden in model_lower:
                logger.warning("Model '%s' is forbidden by policy", model_id)
                return False

        if not self.allowed_models:
            return True  # No restrictions in GENERAL mode

        # Check if any allowed model is a substring of the model_id (case-insensitive)
        allowed_models = [allowed.lower() for allowed in self.allowed_models]
        is_allowed = any(allowed in model_lower for allowed in allowed_models)

        if not is_allowed:
            logger.warning(
                "Model '%s' not allowed in %s mode. Allowed: %s",
                model_id,
                self.mode.value,
                self.allowed_models,
            )

        return is_allowed

    def create_security_context(
        self,
        has_connectivity: bool = True,
        data_residency: str | None = None,
    ) -> SecurityContext:
        """Create a SecurityContext configured for this compliance mode.

        Args:
            has_connectivity: Whether external network access is available
            data_residency: Geographic restriction for data processing

        Returns:
            SecurityContext configured with mode-appropriate settings
        """
        return SecurityContext(
            compliance_mode=self.mode,
            security_level=SecurityLevel.UNCLASSIFIED,
            has_connectivity=has_connectivity and not self.force_offline,
            audit_required=self.mode in [ComplianceMode.HIPAA, ComplianceMode.TACTICAL],
            data_residency=data_residency,
            allowed_models=self.allowed_models.copy(),
            blocked_patterns=[],
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert handler configuration to dictionary.

        Returns:
            Dictionary with all configuration parameters
        """
        return {
            "mode": self.mode.value,
            "audit_retention_days": self.audit_retention_days,
            "encryption_required": self.encryption_required,
            "allowed_models": self.allowed_models,
            "phi_redaction_enabled": self.phi_redaction_enabled,
            "force_offline": self.force_offline,
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def create_security_context_for_mode(
    mode: ComplianceMode,
    has_connectivity: bool = True,
    data_residency: str | None = None,
) -> SecurityContext:
    """Create a SecurityContext for a specific compliance mode.

    Convenience function that creates a ComplianceHandler and uses it
    to generate an appropriately configured SecurityContext.

    Args:
        mode: Compliance mode to configure for
        has_connectivity: Whether external network access is available
        data_residency: Geographic restriction for data processing

    Returns:
        SecurityContext configured for the specified mode
    """
    handler = ComplianceHandler(mode)
    return handler.create_security_context(
        has_connectivity=has_connectivity,
        data_residency=data_residency,
    )


def quick_scan(query: str, mode: ComplianceMode = ComplianceMode.GENERAL) -> ScanResult:
    """Perform a quick security scan with default settings.

    Convenience function for simple scanning without full context setup.

    Args:
        query: The query text to scan
        mode: Compliance mode to use (affects which patterns are checked)

    Returns:
        ScanResult with detected flags and blocking decision
    """
    scanner = SecurityScanner()
    context = create_security_context_for_mode(mode)
    return scanner.scan(query, context)


# =============================================================================
# EXPORTS
# =============================================================================


__all__ = [
    "ComplianceHandler",
    "ComplianceMode",
    "ScanResult",
    "SecurityContext",
    "SecurityLevel",
    "SecurityScanner",
    "create_security_context_for_mode",
    "quick_scan",
]
