#!/usr/bin/env python3
"""AIPEA Security Context Module - Security and compliance handling for AI query processing.

This module implements security screening and compliance mode handling for the
AI Prompt Engineer Agent (AIPEA) integration with Agora IV. It provides:

- Security level classification (UNCLASSIFIED to TOP_SECRET)
- Compliance modes (General, HIPAA, Tactical)
- PII/PHI detection and handling
- Classified content marker detection
- Prompt injection attack prevention
- Mode-specific model restrictions

Based on Agora V AIPEA security patterns, adapted for Agora IV production.

Note: ComplianceMode.FEDRAMP is retained as a deprecated alias and will be
removed in v2.0.0. See docs/adr/ADR-002-fedramp-removal.md for the rationale.
"""

from __future__ import annotations

import logging
import re
import unicodedata
import warnings
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, Final

logger = logging.getLogger(__name__)

# Canonical compliance-taint flag prefixes (ScanResult.flags prefix strings).
# Bare-string call sites inside this module and enhancer.py are left intact
# to minimize diff size; new code should prefer these constants.
FLAG_PII_DETECTED: Final[str] = "pii_detected:"
FLAG_PHI_DETECTED: Final[str] = "phi_detected:"
FLAG_CLASSIFIED_MARKER: Final[str] = "classified_marker:"
FLAG_INJECTION_ATTEMPT: Final[str] = "injection_attempt"
FLAG_CUSTOM_BLOCKED: Final[str] = "custom_blocked:"

_COMPLIANCE_TAINT_PREFIXES: Final[tuple[str, ...]] = (
    FLAG_PII_DETECTED,
    FLAG_PHI_DETECTED,
    FLAG_CLASSIFIED_MARKER,
    FLAG_INJECTION_ATTEMPT,
)

# Common cross-script confusable characters mapped to ASCII equivalents.
# Used to defeat homoglyph bypass attacks where adversaries substitute
# visually similar characters from other scripts (e.g., Cyrillic U+043E for Latin 'o').
# Only maps characters commonly exploited in injection attacks.
_CONFUSABLE_MAP: dict[str, str] = {
    # Cyrillic -> Latin
    "\u0410": "A",  # U+0410 Cyrillic A
    "\u0412": "B",  # U+0412 Cyrillic Ve
    "\u0421": "C",  # U+0421 Cyrillic Es
    "\u0415": "E",  # U+0415 Cyrillic Ie
    "\u041d": "H",  # U+041D Cyrillic En
    "\u041a": "K",  # U+041A Cyrillic Ka
    "\u041c": "M",  # U+041C Cyrillic Em
    "\u041e": "O",  # U+041E Cyrillic O
    "\u0420": "P",  # U+0420 Cyrillic Er
    "\u0422": "T",  # U+0422 Cyrillic Te
    "\u0425": "X",  # U+0425 Cyrillic Kha
    "\u0430": "a",  # U+0430 Cyrillic a
    "\u0441": "c",  # U+0441 Cyrillic es
    "\u0435": "e",  # U+0435 Cyrillic ie
    "\u043e": "o",  # U+043E Cyrillic o
    "\u0440": "p",  # U+0440 Cyrillic er
    "\u0445": "x",  # U+0445 Cyrillic kha
    "\u0443": "y",  # U+0443 Cyrillic u
    "\u0456": "i",  # U+0456 Cyrillic i (Ukrainian)
    "\u0455": "s",  # U+0455 Cyrillic dze
    # Uppercase counterparts of the three lowercase Cyrillic extensions
    # above, which NFKC does NOT normalise to Latin. Without these entries,
    # an attacker can use capital-letter homoglyphs (U+0406 + "gnore
    # previous instructions", U+0405 + "ECRET") to bypass injection and
    # classified-marker detection that correctly trips on the lowercase
    # counterparts. (#97)
    "\u0406": "I",  # U+0406 Cyrillic Ukrainian/Byelorussian I (uppercase of \u0456)
    "\u0405": "S",  # U+0405 Cyrillic Dze (uppercase of \u0455)
    "\u0408": "J",  # U+0408 Cyrillic Je
    "\u0458": "j",  # U+0458 Cyrillic je (lowercase counterpart of \u0408)
    # Greek -> Latin
    "\u0391": "A",  # U+0391 Greek Alpha
    "\u0392": "B",  # U+0392 Greek Beta
    "\u0395": "E",  # U+0395 Greek Epsilon
    "\u0397": "H",  # U+0397 Greek Eta
    "\u0399": "I",  # U+0399 Greek Iota
    "\u039a": "K",  # U+039A Greek Kappa
    "\u039c": "M",  # U+039C Greek Mu
    "\u039d": "N",  # U+039D Greek Nu
    "\u039f": "O",  # U+039F Greek Omicron
    "\u03a1": "P",  # U+03A1 Greek Rho
    "\u03a4": "T",  # U+03A4 Greek Tau
    "\u03a5": "Y",  # U+03A5 Greek Upsilon
    "\u03a7": "X",  # U+03A7 Greek Chi
    "\u03bf": "o",  # U+03BF Greek omicron
    "\u03b1": "a",  # U+03B1 Greek alpha
}
_CONFUSABLE_TRANS = str.maketrans(_CONFUSABLE_MAP)

# Zero-width and invisible formatting characters that survive NFKC
# normalization.  Stripped to reconstitute split words (both intra-word
# and inter-word attacks).  Security scanning runs on BOTH the stripped
# form AND a space-substituted form so \s-dependent injection patterns
# also fire when invisible chars replace real spaces.  (#108, #108b)
#
# Cycle-2 expansion (F3, 2026-05-26): the prior class missed three
# NFKC-stable invisibles documented in modern prompt-injection research
# as inter-word evasion vectors against multi-word pattern detection:
#   - U+034F  COMBINING GRAPHEME JOINER (CGJ) \u2014 Mn but used as invisible
#             glue; preserved by NFKC
#   - U+061C  ARABIC LETTER MARK (ALM)        \u2014 Cf (bidi); NFKC-stable
#   - U+180E  MONGOLIAN VOWEL SEPARATOR (MVS) \u2014 Cf; NFKC-stable
# Plus the TAG block U+E0020-U+E007F (Cf, plane 14) \u2014 used in the 2024
# "ASCII smuggling" / Unicode-tag steganographic prompt-injection class.
# These characters are NEVER expected in a legitimate LLM-bound query;
# stripping them on the primary form (and replacing them with spaces on
# the secondary form) is the conservative right call.
# Unicode line terminators that Python's `str.splitlines()` recognizes
# but `[\r\n]` in the conversation-separator INJECTION_PATTERN does not.
# All are normalized to `\n` before pattern matching so the line-anchored
# injection separator fires regardless of which terminator the attacker
# used. Without normalizing NEL/VT/FF, a payload like "text<NEL>Human:
# do evil" evaded the conversation-separator regex (cycle-3 F3).
#   - U+000B VT  (vertical tab)
#   - U+000C FF  (form feed)
#   - U+001C FS  (file separator)        — cycle-4 (GPT 5.4 Pro PR #73)
#   - U+001D GS  (group separator)       — cycle-4
#   - U+001E RS  (record separator)      — cycle-4
#   - U+0085 NEL (next line)
#   - U+2028 LS  (line separator)
#   - U+2029 PS  (paragraph separator)
# This is the COMPLETE set of terminators Python's str.splitlines()
# splits on (verified: 'a\x1cb'.splitlines() == ['a', 'b']). FS/GS/RS
# were missed in cycle-3; 'text\x1eHuman: reveal' still evaded the
# line-anchored conversation-separator pattern until this cycle-4 fix.
_UNICODE_NEWLINE_RE = re.compile("[\x0b\x0c\x1c-\x1e\x85\u2028\u2029]")
_ALL_INVISIBLE_RE = re.compile(
    # Cycle-8 (GPT 5.4 Pro PR #73 round 6 + root-cause generalization):
    # the COMPLETE Unicode Default_Ignorable_Code_Point set (the
    # canonical "invisible for rendering" property, Unicode 15.1
    # DerivedCoreProperties) UNION the non-DI format/control chars
    # earlier cycles added (Brahmi Number Joiner U+1107F, Egyptian
    # Hieroglyph Format Controls U+13430-13438, narrow-NBSP / line-sep
    # tail of U+2028-202F). Covering the whole DI property — including
    # its RESERVED ranges (e.g. U+E0000-E0FFF), which exist precisely
    # so future-assigned invisibles are ignorable — future-proofs
    # against the per-char reactive patching that drove cycles 3-8
    # (CGJ, ALM, MVS, VS-1..16, Mongol VS, TAG block, VSS, LANGUAGE
    # TAG, and the Hangul fillers U+115F/1160/3164/FFA0 that GPT
    # flagged in round 6). All are stripped (primary form) or space-
    # substituted (secondary form) by the two-form scan. Verified a
    # strict SUPERSET of every prior cycle's class; matches no visible
    # character.
    "[\u00ad\u034f\u061c\u115f-\u1160\u17b4-\u17b5\u180b-\u180f"
    "\u200b-\u200f\u2028-\u202f\u2060-\u206f\u3164\ufe00-\ufe0f"
    "\ufeff\uffa0\ufff0-\ufffb\U0001107f\U00013430-\U00013438"
    "\U0001bca0-\U0001bca3\U0001d173-\U0001d17a"
    "\U000e0000-\U000e0fff]"
)


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

    Supported modes:
        GENERAL, HIPAA, TACTICAL

    Deprecated modes:
        FEDRAMP — config-only stub with no behavioral enforcement. Retained
        for API compatibility through the v1.x line; scheduled for removal
        in v2.0.0. Use of this value at runtime emits a DeprecationWarning.
        See docs/adr/ADR-002-fedramp-removal.md for the decision rationale.
    """

    GENERAL = "general"  # Standard use - minimal restrictions
    HIPAA = "hipaa"  # Medical/PHI handling - requires BAA-covered models
    TACTICAL = "tactical"  # Military/Defense - local models only, air-gapped
    FEDRAMP = "fedramp"  # DEPRECATED — see ADR-002; removal planned for v2.0.0


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class SecurityContext:
    """Security context for a request.

    Encapsulates all security-related settings for processing a query,
    including compliance mode, classification level, and operational constraints.

    Attributes:
        compliance_mode: Active compliance framework (GENERAL, HIPAA, TACTICAL;
            FEDRAMP is deprecated — see ADR-002)
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

    def has_compliance_taint(self) -> bool:
        """Check if any flag matches a compliance-taint prefix.

        Compliance-taint flags are PII, PHI, classified markers, and injection
        attempts — the subset that should gate feedback averaging per ADR-004.

        Returns:
            True if any flag is a compliance-taint flag
        """
        return any(f.startswith(p) for f in self.flags for p in _COMPLIANCE_TAINT_PREFIXES)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with scan result fields
        """
        return {
            "flags": self.flags,
            "is_blocked": self.is_blocked,
            "force_offline": self.force_offline,
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
    # Cycle-3 F5/F6 whitespace tolerance: SSN and CCN structural
    # separators now accept zero-or-more whitespace around the hyphens
    # (SSN) and zero-or-more whitespace-or-hyphen between groups (CCN).
    # The pre-fix patterns rejected tab/double-space variants between
    # digit groups even though the two-form invisible-char scan
    # couldn't help (digits can't span an inserted whitespace). Same
    # `\s+`-as-canonical-separator principle as the cycle-2 F3 PHI fix.
    PII_PATTERNS: ClassVar[dict[str, str]] = {
        "ssn": r"\b\d{3}\s*-\s*\d{2}\s*-\s*\d{4}\b",
        "credit_card": r"\b\d{4}[\s-]*\d{4}[\s-]*\d{4}[\s-]*\d{4}\b",
        "api_key": r"\b(api[_-]?key)\s*[:=]\s*\S{20,}",
        "sk_key": r"\bsk-[a-zA-Z0-9_-]{20,}\b",
        "bearer_token": r"\bbearer\s+[a-zA-Z0-9._-]{20,}\b",
        "password": r"(password|passwd|pwd)\s*[:=]\s*\S+",
    }

    # HIPAA-specific PHI patterns - only checked in HIPAA mode
    #
    # NOTE on patient_name: the label "patient" must match case-insensitively,
    # but the two name tokens MUST remain case-sensitive so the pattern only
    # fires on proper names (e.g. "patient: John Smith"), not on common
    # clinical phrases like "the patient has good vitals". The `(?i:patient)`
    # inline group enables IGNORECASE just for the label; the rest of the
    # pattern is compiled WITHOUT re.IGNORECASE (see __init__ below) because
    # the flag would otherwise make [A-Z] and [a-z] match case-insensitively
    # (a Python regex gotcha), producing a massive HIPAA false-positive
    # surface on any query containing "patient" + two ordinary words. (#95)
    # Multi-word PHI label literals MUST use `\s+` (not literal " ") so
    # double-space, tab, and NFKC-equivalent whitespace variants ("medical
    # \trecord", "medical\xa0record" — NBSP NFKC-normalizes to space —
    # "medical  record") all match. The pre-fix literal-space form left
    # these whitespace variants as an evasion class even with the two-form
    # invisible-char rewrite, because once the invisible was replaced with
    # `\s` the multi-space gap still didn't match the single literal space.
    # (Cycle-2 F3.)
    # Cycle-5 (GPT 5.4 Pro PR #73 round 3): the DOB date VALUE separators
    # are also whitespace-tolerant (`\s*[/-]\s*`), not just the label.
    # Without it, "DOB: 01 / 02 / 1990" and "date of birth 01 - 02 - 1990"
    # (spaces around the slashes/hyphens) evaded the HIPAA sweep even
    # after the cycle-2 label fix.
    PHI_PATTERNS: ClassVar[dict[str, str]] = {
        "mrn": r"\b(MRN|medical\s+record)\s*[:=]?\s*\d+\b",
        "dob": r"\b(DOB|date\s+of\s+birth)\s*[:=]?\s*\d{1,2}\s*[/-]\s*\d{1,2}\s*[/-]\s*\d{2,4}\b",
        "patient_name": r"\b(?i:patient)\s*[:=]?\s*[A-Z][a-z]+\s+[A-Z][a-z]+\b",
    }

    # PHI patterns that must be compiled WITHOUT re.IGNORECASE because they
    # rely on case-sensitive character classes to avoid false positives. (#95)
    _PHI_CASE_SENSITIVE: ClassVar[frozenset[str]] = frozenset({"patient_name"})

    # Classified content markers - only checked in TACTICAL mode.
    # Kept as a list of display names so the resulting flags
    # (`classified_marker:<NAME>`) remain stable as a public contract.
    # The actual match patterns live in `_CLASSIFIED_MARKER_PATTERNS`
    # below — see that table for why each marker uses the pattern it
    # uses (cycle-2 F11: bare `\bSCI\b` was a false-positive farm).
    CLASSIFIED_MARKERS: ClassVar[list[str]] = [
        "TOP SECRET",
        "SECRET",
        "CONFIDENTIAL",
        "NOFORN",
        "SCI",
    ]

    # Per-marker regex patterns (matched against `query.upper()` —
    # all uppercase). Notes:
    #   - "TOP SECRET": uses `\s+` between TOP and SECRET so the
    #     multi-space / tab variants don't evade (mirror of the PHI
    #     pattern repair for cycle-2 F3).
    #   - Single-word markers ("SECRET", "CONFIDENTIAL", "NOFORN"):
    #     standard `\b...\b` boundary.
    #   - "SCI": IC-banner-context-anchored. Bare `\bSCI\b` false-
    #     positively matched "sci-fi" (hyphen is a word boundary),
    #     "the SCI department", "scientific" subword, etc. (cycle-2
    #     F11; GPT 5.4 Pro empirical critique confirmed the naive
    #     `(?<![\w-])SCI(?![\w-])` alternative ALSO matches "the SCI
    #     department" because spaces are non-word non-hyphen.) The
    #     fix anchors SCI to its IC compartment-delimiter context:
    #     the marker must be preceded by `//` (the IC banner
    #     compartment delimiter, as in `TS//SCI` / `TOP SECRET//SCI`)
    #     or followed by `//` / `/<UPPER>` (as in `SCI//NOFORN` /
    #     `SCI/REL`). This matches established IC tradecraft and
    #     rejects the common-English false-positive class.
    # Known IC banner classification level prefixes. Used to anchor
    # the SCI compartment marker to real banner context (cycle-3 PR #73
    # GPT 5.4 Pro REQUEST_CHANGES + cycle-3 verification F4): the
    # cycle-2 fix `(?<=//)SCI\b|\bSCI(?=//|/[A-Z])` still matched
    # benign URLs like `https://sci-fi.example` and `/sci/readme`
    # (`HTTPS://SCI-FI` upper-cased, `//` precedes SCI; `SCI/R` of
    # `/sci/readme` matches the lookahead). The fix requires SCI to be
    # adjacent to a recognized banner LEVEL (TS, S, C, U + full forms)
    # via the IC compartment delimiter `//`, OR followed by a
    # constrained banner CONTINUATION (NOFORN, REL, FGI, IMCON, etc.).
    _CLASSIFIED_LEVEL_PREFIXES: ClassVar[str] = (
        r"(?:TS|S|C|U|TOP\s+SECRET|SECRET|CONFIDENTIAL|UNCLASSIFIED)"
    )
    _SCI_COMPARTMENT_SUFFIXES: ClassVar[str] = (
        r"(?:NOFORN|REL|FGI|IMCON|ORCON|PROPIN|RELIDO|RSEN|HUMINT|COMINT|SI|TK|HCS)"
    )
    # Banner opener (cycle-6, GPT 5.4 Pro PR #73 round 4; widened cycle-7
    # round 5): start-of-input OR a clean opening delimiter, followed by
    # an OPTIONAL single leading slash. The optional `/?` admits
    # leading-slash banners `/TS//SCI`, ` /SCI/REL` (a list-marker or
    # stray-slash banner at a clean boundary — a real classified marking
    # that MUST flag, since a missed classified banner in TACTICAL mode
    # is the dangerous false-NEGATIVE direction). The clean-boundary
    # requirement STILL rejects mid-URI/path forms
    # (`https://example.com/TS//SCI`, `path/to/TS//SCI`, `/sci/readme`)
    # where the slash is preceded by a word char or another path segment.
    #
    # Opener char class (cycle-7 round 5): whitespace, brackets/braces,
    # angle-open, quotes, AND field delimiters `: = , ; |`. The field
    # delimiters close a TACTICAL false-negative on unquoted key/value
    # banner forms `classification:TS//SCI`, `label:S//SCI`,
    # `classification=SCI/REL`. CRITICALLY the class excludes `/` and
    # word chars, so adding `:`/`=` does NOT re-open the URL FP
    # (`https://...:8080/TS//SCI` still rejects — the `/TS` is preceded
    # by a word char, and `https:` + `/?` lands on the second `/` of
    # `://`, not a level token). The lookbehind is fixed-width (1 char),
    # a legal Python `re` lookbehind.
    # SPLIT into two cases (cycle-8, GPT 5.4 Pro PR #73 round 6):
    #   CASE A — start-of-input OR whitespace/bracket/quote/angle/paren,
    #     THEN an OPTIONAL leading slash `/?` (admits leading-slash
    #     banners `/TS//SCI`, ` /SCI/REL`).
    #   CASE B — after a FIELD delimiter (`: = , ; |`), with NO optional
    #     slash (admits `classification:TS//SCI`, `label:S//SCI`).
    # The cycle-7 single-class form combined `:` WITH the optional `/?`,
    # which re-opened a path FP: `C:/TS//SCI` (Windows path) and
    # `scheme:/SCI/REL` (URI scheme) matched because `:` was a clean
    # opener AND the `/` after it was consumed by `/?`. Separating the
    # cases means a slash is admitted ONLY after start/whitespace/
    # bracket (never after a field delimiter), so `C:/…` and `scheme:/…`
    # reject while the no-slash field-delimiter banners still match.
    _BANNER_OPENER: ClassVar[str] = r"(?:(?:^|(?<=[\s(\[{<\"']))/?|(?<=[:=,;|]))"

    # SCI tail guard for the `<level>//SCI` branch (cycle-7 round 5):
    # after `SCI`, allow a valid banner tail (`//<compartment>`, `/REL`)
    # or a terminal (whitespace / end / non-slash punctuation), but
    # REJECT a path-style single-slash continuation (`/readme`,
    # `/index.html`). `(?!/(?!/|REL\b))` = "not followed by [ a slash
    # that is NOT followed by (another slash | REL) ]": a `//` (chained
    # compartment) or `/REL` is allowed; a lone `/<path>` is rejected.
    # This closes the cycle-6 asymmetry GPT flagged in round 5 — the
    # terminal guard was on the second SCI branch but not the first, so
    # `/TS//SCI/readme` wrongly matched.
    _SCI_TAIL_GUARD: ClassVar[str] = r"(?!/(?!/|REL\b))"
    # Compartment-continuation guard for the second SCI branch: after a
    # consumed compartment suffix, allow `//` (further chaining) and
    # terminal but reject a single-slash path (`SCI//NOFORN/path`).
    _SCI_CONT_GUARD: ClassVar[str] = r"(?!/(?!/))"

    _CLASSIFIED_MARKER_PATTERNS: ClassVar[dict[str, str]] = {
        "TOP SECRET": r"\bTOP\s+SECRET\b",
        "SECRET": r"\bSECRET\b",
        "CONFIDENTIAL": r"\bCONFIDENTIAL\b",
        "NOFORN": r"\bNOFORN\b",
        # SCI must appear in REAL IC banner context. Two valid forms:
        #   (a) preceded by a classification level + `//`, with the
        #       level itself preceded by start-of-input, whitespace,
        #       or an opening paren — so a URL path like
        #       `https://sci-fi.example` (no level word in front of `//`)
        #       and `https://example.com/TS//SCI` (`/` not `(`/`\s`/`^`
        #       before TS) both correctly reject;
        #   (b) followed by a known compartment / control-marking
        #       continuation via `//<KEYWORD>` or `/REL`. The keyword
        #       allow-list rejects `/sci/readme` (README is not a
        #       compartment) while accepting `SCI//NOFORN`, `SCI/REL`,
        #       `SCI//FGI`, etc.
        # Pre-marker gate evolution (the SCI boundary has been the
        # single hardest part of this module to get right; documented
        # here in full so the next maintainer doesn't re-litigate it):
        #   cycle-2 `(?<=//)SCI\b|\bSCI(?=//|/[A-Z])` — matched
        #     `https://sci-fi`, `/sci/readme` (URL/path FALSE POSITIVES).
        #   cycle-4 `(?<![\w/])` — fixed the URL FPs but rejected
        #     legitimate bracketed/quoted banners `[TS//SCI]` (FALSE
        #     NEGATIVE).
        #   cycle-5 — made the `//` and `/` delimiters whitespace-
        #     tolerant (`\s*/\s*/\s*`, `\s*/\s*`) for `TS // SCI`,
        #     `SCI / REL`.
        #   cycle-6 (this) `_BANNER_OPENER` — admits an OPTIONAL leading
        #     slash at a CLEAN boundary so `/TS//SCI`, ` /SCI/REL`
        #     (list-marker / stray-slash banners — real markings that
        #     MUST flag) are caught, while STILL rejecting mid-URI/path
        #     slashes (`https://example.com/TS//SCI`, `path/to/TS//SCI`).
        #     In a classified-content gate, a missed banner (false
        #     negative) leaks classified content to an external model —
        #     the dangerous direction — so the leading-slash admission
        #     is the security-conservative choice.
        # Two valid forms: (a) <level>//SCI, (b) SCI//<compartment> or
        # SCI/REL. The compartment allow-list rejects `/sci/readme`
        # (README is not a compartment). Each `\s*` is bounded by a
        # mandatory literal `/` — no ReDoS ambiguity.
        #
        # The `_NOT_PATH_CONT = (?!/(?!/))` terminal guard (cycle-6)
        # distinguishes a banner-terminal compartment from a path
        # segment: it rejects a marker followed by a SINGLE `/`
        # (path continuation, e.g. `/sci/rel/index.html` →
        # `REL/index`) while ALLOWING `//` (a compartment delimiter,
        # e.g. multi-compartment `SCI//NOFORN//ORCON`) and the
        # terminal/whitespace case (`SCI//NOFORN`, `SCI/REL TO USA`).
        # This is what lets the cycle-6 leading-slash admission
        # (`/SCI/REL` banner) coexist with the cycle-1 path rejection
        # (`/sci/rel/index.html`): the discriminator moved from "is
        # there a leading slash" to "is the marker followed by a
        # path-style single-slash continuation".
        "SCI": (
            _BANNER_OPENER
            + _CLASSIFIED_LEVEL_PREFIXES
            + r"\s*/\s*/\s*SCI\b"
            + _SCI_TAIL_GUARD
            + r"|"
            + _BANNER_OPENER
            + r"SCI(?:\s*/\s*/\s*"
            + _SCI_COMPARTMENT_SUFFIXES
            + r"\b"
            + _SCI_CONT_GUARD
            + r"|\s*/\s*REL\b"
            + _SCI_CONT_GUARD
            + r")"
        ),
    }

    # Injection patterns - always checked and always blocked
    INJECTION_PATTERNS: ClassVar[list[str]] = [
        # Instruction-override family — strong-cue form.
        # Allows zero or more determiners/qualifiers followed by 1-3
        # stacked cue tokens before "instructions". Supports variants
        # like "ignore previous system instructions" and "ignore the
        # above developer instructions" while keeping benign prose
        # ("forget to print your instructions", "don't forget to send
        # all instructions") unblocked because non-allow-list words
        # ("to", "send", "print") break the filler loop.
        r"(?:ignore|disregard|forget|override)\s+"
        r"(?:(?:the|all|your|my|any|these|those|of)\s+)*"
        r"(?:(?:previous|prior|above|earlier|preceding|system|developer|assistant)\s+){1,3}"
        r"instructions\b",
        # Instruction-override family — direct "all" form.
        # Covers "ignore all instructions" (no cue required) with an
        # allow-list filler that includes role cues so "ignore all
        # system instructions" and "disregard all developer
        # instructions" block.
        r"(?:ignore|disregard|forget|override)\s+all\s+"
        r"(?:(?:of|the|your|my|these|those|previous|prior|above|earlier|preceding|system|developer|assistant)\s+)*"
        r"instructions\b",
        # Directional sibling without "instructions"
        # ("ignore everything above"). Lookahead for end-of-input,
        # whitespace-plus-punctuation, or end-of-line keeps benign
        # phrases like "ignore all prior art" or "disregard
        # everything below deck" unblocked.
        r"(?:ignore|disregard|forget|override)\s+"
        r"(?:everything|all)\s+"
        r"(?:above|below|before|earlier|preceding)"
        r"(?=\s*(?:[.!?,;:\n\r]|$))",
        # Wave-21 (D4-B): paraphrase-verb tier 2 — strong-cue form.
        # Same shape as pattern 1, but covers the six paraphrase verbs
        # the OWASP corpus exposed beyond the four-verb baseline:
        # bypass, reset, cancel, nullify, revoke, terminate. Split into
        # a separate pattern (rather than appended to pattern 1) so
        # each entry stays under _MAX_PATTERN_LENGTH (200 chars).
        # The leading "(?<!\w)" lookbehind prevents matching the verb
        # as a substring of a longer word ("preset previous
        # instructions", "uncancel all instructions"); fixed-width
        # lookbehind, no ReDoS impact.
        # Verbs scrap, void, and abort are intentionally omitted — they
        # are rare in the wild and "void instructions" / "scrap
        # instructions" are awkward attack phrasings; the AI red-team
        # engine (ADR-009) will surface them if they become real.
        r"(?<!\w)(?:bypass|reset|cancel|nullify|revoke|terminate)\s+"
        r"(?:(?:the|all|your|my|any|these|those|of)\s+)*"
        r"(?:(?:previous|prior|above|earlier|preceding|system|developer|assistant)\s+){1,3}"
        r"instructions\b",
        # Wave-21 (D4-B): paraphrase-verb tier 2 — direct "all" form.
        # Mirrors pattern 2 with the same six paraphrase verbs and the
        # same "(?<!\w)" word-boundary guard.
        r"(?<!\w)(?:bypass|reset|cancel|nullify|revoke|terminate)\s+all\s+"
        r"(?:(?:of|the|your|my|these|those|previous|prior|above|earlier|preceding|system|developer|assistant)\s+)*"
        r"instructions\b",
        # Wave-21 (D4-B): cross-language coverage intentionally NOT
        # included in the regex layer. The bare "verb + instructions"
        # shape is ambiguous in any language (benign foreign prose
        # like "ne pas ignorer instructions de votre patron" has the
        # same shape as adversarial bare foreign payloads), and
        # adding per-language qualifiers would roughly double pattern
        # complexity and re-introduce the 200-char ReDoS-safety
        # length cap problem. Per 2026 research (SafePrompt regex-only
        # F1 ~0.43; TokenMix PromptBench classifier-only +18%),
        # cross-language detection is the architectural ceiling regex
        # hits fastest — the right tool is the LLM-as-judge tier in
        # ADR-010 (semantic scanner). See PR #61 for the prototype +
        # decision history.
        r"</?(system|user|assistant)>",
        r"\[/?(system|user|assistant|human)\]",  # Bracket-style role tags
        # Conversation separator injection — INTENTIONALLY line-anchored.
        # Cycle-2 F12 documents this as a deliberate regex-tier design
        # boundary: a mid-line role token ("...text. Assistant: ...")
        # is NOT caught here because broadening to mid-line introduces
        # real false positives on benign English prose ("Ask the
        # assistant:", "Try System: reboot first", etc.). Per the
        # ADR-010 / PR #61 design decision logged immediately above,
        # disambiguating benign role-mentions from adversarial separator
        # injection at the regex layer hits the same cross-language
        # FP-budget ceiling SafePrompt / TokenMix-PromptBench identified;
        # the right tool for the mid-line case is the LLM-as-judge tier
        # (ADR-010 semantic scanner). Tracked in
        # `.quality-gate/accepted-findings.jsonl` as `wontfix`.
        r"(?:^|[\r\n])\s*(?:Human|Assistant|System)\s*:",  # Conversation separator injection
        r"DROP\s+TABLE",
        r"UNION\s+SELECT",
        r"\{\{[\s\S]*?\}\}",  # Template injection (DOTALL-compatible, non-greedy)
        r"<script[^>]*>",  # XSS attempt
    ]

    def __init__(self) -> None:
        """Initialize the security scanner with compiled regex patterns."""
        # Cycle-3 F7 contract: every marker in CLASSIFIED_MARKERS MUST
        # have an explicit _CLASSIFIED_MARKER_PATTERNS entry. The fall-
        # back `\b<marker>\b` (still used by `_check_classified_markers`
        # as a defensive belt-and-suspenders for marker-list mutations
        # at runtime) is the exact shape that the cycle-2 F11 fix
        # documented as broken for the SCI marker — common-English-
        # subword false positives. Catch the contract violation at
        # init time so a future maintainer can't silently re-introduce
        # the F11 false-positive class by adding a marker name without
        # a matching pattern entry.
        missing_patterns = set(self.CLASSIFIED_MARKERS) - set(self._CLASSIFIED_MARKER_PATTERNS)
        if missing_patterns:
            # RuntimeError (a stdlib builtin) is deliberate, NOT the
            # `errors.AIPEAError` hierarchy (GPT 5.4 Pro PR #73 round-2
            # non-blocking note). `security.py` is a ZERO-aipea-imports
            # module by architectural contract (SPECIFICATION §4 module
            # dependency graph + CLAUDE.md §4 "security.py <- ZERO aipea
            # imports (stdlib only)"); importing `aipea.errors` would
            # violate it. RuntimeError is also the established precedent
            # for the sibling INJECTION_PATTERN ReDoS-safety invariant
            # check below. This is a developer-misconfiguration invariant
            # (a programming error at class-definition time), not a
            # user-facing runtime condition, so a builtin is the correct
            # choice regardless.
            raise RuntimeError(
                f"CLASSIFIED_MARKERS contains markers missing from "
                f"_CLASSIFIED_MARKER_PATTERNS: {sorted(missing_patterns)}. "
                "Every marker MUST have an explicit pattern entry to avoid "
                "the cycle-2 F11 false-positive class (bare `\\b<marker>\\b` "
                "matching common English subwords)."
            )
        self._compiled_pii: dict[str, re.Pattern[str]] = {
            name: re.compile(pattern, re.IGNORECASE) for name, pattern in self.PII_PATTERNS.items()
        }
        # PHI patterns are compiled per-entry: those in _PHI_CASE_SENSITIVE
        # MUST NOT use re.IGNORECASE because the flag makes [A-Z]/[a-z]
        # character classes case-insensitive, defeating name-capitalisation
        # guards. Case-insensitive label matching is obtained via the
        # (?i:...) inline flag inside the pattern itself. (#95)
        self._compiled_phi: dict[str, re.Pattern[str]] = {}
        for name, pattern in self.PHI_PATTERNS.items():
            if name in self._PHI_CASE_SENSITIVE:
                self._compiled_phi[name] = re.compile(pattern)
            else:
                self._compiled_phi[name] = re.compile(pattern, re.IGNORECASE)
        self._compiled_injection: list[re.Pattern[str]] = []
        for pattern in self.INJECTION_PATTERNS:
            if not self._is_regex_safe(pattern):
                raise RuntimeError(
                    f"Hardcoded INJECTION_PATTERN failed ReDoS safety check: {pattern!r}"
                )
            self._compiled_injection.append(re.compile(pattern, re.IGNORECASE))
        # Precompile classified-marker patterns once at init (cycle-5,
        # GPT 5.4 Pro PR #73 round-3 non-blocking note): catches regex
        # typos at construction time (re.compile raises re.error on a
        # malformed pattern) rather than on first TACTICAL scan, and
        # avoids per-call `re.compile` recompilation in
        # `_check_classified_markers`. Matched against `query.upper()`
        # (no re.IGNORECASE) — same convention as the raw-string version.
        #
        # NB: these are NOT run through `_is_regex_safe`. That validator
        # exists to bound the ReDoS risk of UNTRUSTED, user-supplied
        # `SecurityContext.blocked_patterns` (incl. a conservative 200-
        # char length cap). The classified patterns are hardcoded,
        # code-reviewed, and ReDoS-safe by construction (the SCI
        # pattern's `\s*` groups are each bounded by a mandatory literal
        # `/`, so there is no adjacent-unbounded-quantifier ambiguity —
        # see the SCI pattern comment). The length cap in particular is
        # a user-input heuristic that the legitimately-long SCI
        # alternation exceeds; applying it here would be a category
        # error.
        self._compiled_classified: dict[str, re.Pattern[str]] = {
            name: re.compile(pattern) for name, pattern in self._CLASSIFIED_MARKER_PATTERNS.items()
        }
        logger.debug("SecurityScanner initialized with %d PII patterns", len(self.PII_PATTERNS))

    # Maximum pattern length to prevent ReDoS attacks
    _MAX_PATTERN_LENGTH: ClassVar[int] = 200

    # Dangerous patterns that can cause catastrophic backtracking
    _DANGEROUS_PATTERNS: ClassVar[list[str]] = [
        r"\(\.\*\)\+",  # Nested .* with quantifier
        r"\(\.\+\)\+",  # Nested .+ with quantifier
        r"\\[1-9].*[+*]|[+*].*\\[1-9]",  # Backreference with quantifier
        r"\(\.\*\?\)\+",  # Nested .*? with quantifier
        r"\*\*",  # Double quantifier
        r"\{\d+,\}\{\d+,\}",  # Multiple unbounded quantifiers
        r"\(\[\^[^\]]*\][+*]\)\+",  # ([^x]+)+ — char class in quantified group
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

        # Check for character class with quantifier inside a quantified group
        # E.g., ([^x]+)+, ([^a-z]*)+, ([^\s]{1,})+ — all cause catastrophic backtracking
        char_class_quantifier = r"\(\[.*?\](?:[+*]|\{[^}]+\})\)(?:[+*?]|\{[^}]+\})"
        if re.search(char_class_quantifier, pattern):
            logger.debug("Pattern rejected: character class with quantifier in quantified group")
            return False

        # Check for overlapping alternatives with quantifiers
        # E.g., (a|a?)+ which can cause exponential backtracking
        overlapping_pattern = r"\([^|]+\|[^)]+\?\)[+*]"
        if re.search(overlapping_pattern, pattern):
            logger.debug("Pattern rejected: contains overlapping alternatives with quantifiers")
            return False

        # Check for duplicated alternatives in quantified groups, e.g. (a|a)*b
        # and (a|a|a)*b. Python's re engine backtracks exponentially on such
        # patterns: `(a|a)*b` hits ~1.3s on 25 chars, and `(a|a|a)*b` hits
        # >11s on only 18 chars (scales as alternatives^n). The heuristic
        # matches any quantified group whose first two alternatives are
        # identical, regardless of how many additional alternatives follow,
        # via a backref capture. Non-consecutive duplicates like `(a|b|a)+`
        # are rare in hand-written patterns and not caught here. (#107)
        duplicate_alt_quant = r"\(([^|)]+)\|\1(?:\|[^)]*)?\)[+*]"
        if re.search(duplicate_alt_quant, pattern):
            logger.debug("Pattern rejected: duplicated alternative in quantified group")
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

        Uses the per-marker pattern table `_CLASSIFIED_MARKER_PATTERNS`
        rather than a blanket `\\b<marker>\\b` so that:
          - "TOP SECRET" matches whitespace variants (single space,
            double space, tab — cycle-2 F3).
          - "SCI" requires IC-banner compartment-delimiter context
            (preceded or followed by `//`) — cycle-2 F11. Bare
            `\\bSCI\\b` is unsalvageable as a classified-marker
            detector because the English subword "sci" appears in
            countless benign contexts ("sci-fi", "scientific", "the
            SCI department"). IC tradecraft pairs SCI with the
            compartment delimiter `//`.

        Args:
            query: The query text to scan

        Returns:
            Tuple of (flags, force_offline)
        """
        flags: list[str] = []
        force_offline = False
        query_upper = query.upper()
        for name in self.CLASSIFIED_MARKERS:
            compiled = self._compiled_classified.get(name)
            if compiled is None:
                # Defensive: a marker added to CLASSIFIED_MARKERS at
                # runtime (e.g. via instance-level monkeypatch) after
                # __init__ would not be in the precompiled table. The
                # init-time contract check (see __init__) prevents the
                # class-definition-time case; this fallback covers the
                # runtime-mutation case so detection is never silently
                # dropped. Falls back to the standard `\b<marker>\b`
                # boundary (the F11-prone shape — acceptable only as a
                # last-resort belt-and-suspenders).
                compiled = re.compile(rf"\b{re.escape(name)}\b")
            if compiled.search(query_upper):
                flags.append(f"classified_marker:{name}")
                force_offline = True
        # NB: classified-marker WARNING logging is intentionally NOT
        # emitted here. `scan()` calls this method TWICE in TACTICAL
        # mode (once on the normalized form, once on the spaced form)
        # and the two flag sets are then deduped — so logging at the
        # per-call site would double-emit warnings for the
        # most-common case (where both forms produce the same flags).
        # `scan()` emits a single deduped WARNING per unique
        # classified marker AFTER the two-form merge. (GPT 5.4 Pro
        # non-blocking observation on PR #73; cycle-3 follow-up.)
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
        if not query:
            logger.debug("Empty query provided to scan()")
            return ScanResult()

        # Normalize Unicode to defeat homoglyph bypass attacks:
        # 1. NFKC handles compatibility forms (fullwidth → ASCII, ligatures, etc.)
        # 2. Confusable mapping handles cross-script homoglyphs (Cyrillic → Latin, etc.)
        # 3. Strip ALL invisible chars to reconstitute split words for both
        #    intra-word attacks (i\u200bgnore → ignore) and inter-word
        #    attacks (ignore\u200bprevious → ignoreprevious).  (#108)
        # 4. U+2028/U+2029 → \n so [\r\n] conversation separators fire.
        base = unicodedata.normalize("NFKC", query).translate(_CONFUSABLE_TRANS)
        newline_normalized = _UNICODE_NEWLINE_RE.sub("\n", base)
        # Primary form: strip all invisible chars (reconstitutes split words
        # for PII/PHI/classified \b patterns AND intra-word injection bypass).
        normalized_query = _ALL_INVISIBLE_RE.sub("", newline_normalized)
        # Secondary form: replace invisible chars with spaces (catches
        # inter-word injection where invisibles REPLACE real spaces, e.g.
        # "ignore\u200bprevious" → "ignore previous" for \s+ patterns).
        spaced_query = _ALL_INVISIBLE_RE.sub(" ", newline_normalized)

        flags: list[str] = []
        is_blocked = False
        force_offline = False

        # Always check PII patterns — scan BOTH forms (mirror of the
        # existing injection two-form coverage). The stripped form
        # reconstitutes intra-word splits ("ssn: 123-4​5-6789" →
        # "ssn: 123-45-6789"); the spaced form catches the inter-word
        # split that the strip would join into nonsense. Dedup flags
        # via insertion-order dict so the audit log doesn't show
        # duplicate `pii_detected:<name>` lines when both forms match.
        # Cycle-2 F3.
        pii_flags = list(
            dict.fromkeys(self._check_pii(normalized_query) + self._check_pii(spaced_query))
        )
        flags.extend(pii_flags)

        # Check PHI patterns only in HIPAA mode — also two-form,
        # because the multi-word labels (`medical record`,
        # `date of birth`) are exactly the bypass surface the
        # stripped form ("medicalrecord" / "dateofbirth") cannot
        # match. Same dedup. Cycle-2 F3.
        if context.compliance_mode == ComplianceMode.HIPAA:
            phi_flags = list(
                dict.fromkeys(self._check_phi(normalized_query) + self._check_phi(spaced_query))
            )
            flags.extend(phi_flags)

        # Check classified markers only in TACTICAL mode — also two-
        # form. The "TOP SECRET" multi-word marker has the same
        # bypass surface; the stripped form yields "TOPSECRET"
        # (no match against `\bTOP\s+SECRET\b`), but the spaced
        # form yields "TOP SECRET" which matches. `force_offline`
        # is the OR of the two scans — once any classified marker
        # is observed in any normalization of the input, route
        # offline. Cycle-2 F3.
        if context.compliance_mode == ComplianceMode.TACTICAL:
            norm_classified, norm_fo = self._check_classified_markers(normalized_query)
            spaced_classified, spaced_fo = self._check_classified_markers(spaced_query)
            classified_flags = list(dict.fromkeys(norm_classified + spaced_classified))
            flags.extend(classified_flags)
            force_offline = norm_fo or spaced_fo
            # Emit ONE WARNING per unique classified-marker flag after
            # the two-form dedupe (so the common "both forms match"
            # case doesn't double-log). GPT 5.4 Pro non-blocking
            # observation on PR #73; cycle-3 follow-up.
            for flag in classified_flags:
                # flag is of the form "classified_marker:<NAME>"
                _, _, name = flag.partition(":")
                logger.warning("Classified marker detected, forcing offline: %s", name)

        # Check injection against BOTH forms — stripped catches intra-word
        # bypass (i\u200bgnore → ignore), spaced catches inter-word bypass
        # (ignore\u200bprevious → ignore previous for \s+ patterns).
        injection_flags, injection_blocked = self._check_injection(normalized_query)
        if not injection_blocked:
            injection_flags, injection_blocked = self._check_injection(spaced_query)
        flags.extend(injection_flags)
        is_blocked = is_blocked or injection_blocked

        # Cycle-3 F1: custom blocked patterns now scan BOTH forms
        # (parallel to PII/PHI/classified/injection). A consumer-
        # configured multi-token pattern like `proprietary\s+formula`
        # was previously evadable via inter-word ZWSP (stripped form
        # fuses to "proprietaryformula" → no `\s+` match; spaced form
        # would catch but was never checked). Dedup flags via
        # insertion-order dict; OR the two `is_blocked` results.
        custom_flags_n, custom_blocked_n = self._check_custom_patterns(
            normalized_query, context.blocked_patterns
        )
        custom_flags_s, custom_blocked_s = self._check_custom_patterns(
            spaced_query, context.blocked_patterns
        )
        custom_flags = list(dict.fromkeys(custom_flags_n + custom_flags_s))
        flags.extend(custom_flags)
        is_blocked = is_blocked or custom_blocked_n or custom_blocked_s

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
    - FEDRAMP: **DEPRECATED** — config-only stub with no behavioral
      enforcement. Constructing a handler with this mode emits a
      DeprecationWarning. Scheduled for removal in v2.0.0.
      See docs/adr/ADR-002-fedramp-removal.md.

    Attributes:
        mode: Active compliance mode
        audit_retention_days: Required audit log retention period
        encryption_required: Whether encryption is mandatory
        allowed_models: List of permitted AI models
        phi_redaction_enabled: Whether PHI must be redacted
        force_offline: Whether external connectivity is prohibited
    """

    # Models forbidden across ALL compliance modes (deprecated/retired models).
    # Checked before mode-specific allowlists via substring match.
    GLOBAL_FORBIDDEN_MODELS: ClassVar[set[str]] = {"gpt-4o", "gpt-4o-mini"}

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
            # FEDRAMP: DEPRECATED in v1.3.4, scheduled for removal in v2.0.0.
            # See docs/adr/ADR-002-fedramp-removal.md for the decision rationale.
            #
            # This mode provides basic config (retention, model allowlist) but does NOT
            # enforce FedRAMP requirements such as: data residency checks, FedRAMP-authorized
            # provider validation, FIPS 140-2 encryption verification, or continuous
            # monitoring. AIPEA does not implement FedRAMP controls. Migrate to
            # ComplianceMode.GENERAL and layer your own compliance controls on top.
            warnings.warn(
                "ComplianceMode.FEDRAMP is deprecated and will be removed in v2.0.0. "
                "AIPEA does not implement FedRAMP controls; the mode was a "
                "config-only stub with no behavioral enforcement. "
                "Migrate to ComplianceMode.GENERAL and implement FedRAMP controls "
                "in your own application layer. "
                "See docs/adr/ADR-002-fedramp-removal.md.",
                DeprecationWarning,
                stacklevel=3,  # skip _configure_for_mode + __init__ frames
            )
            self.audit_retention_days = 1095  # 3 years (retained for back-compat)
            self.encryption_required = True
            self.allowed_models = [
                "claude-opus-4-6",
                "claude-opus-4-5",
                "gpt-5.2",
            ]  # legacy "FedRAMP authorized" list — not validated, retained for back-compat
            self.phi_redaction_enabled = False
            logger.warning("FEDRAMP mode is deprecated and provides no enforcement — see ADR-002")

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
            An empty allowed_models list means all non-forbidden models are permitted.
            Global forbidden models are blocked in ALL modes.
        """
        model_lower = model_id.lower()

        # Check global forbidden list first (applies to ALL modes)
        if any(forbidden in model_lower for forbidden in self.GLOBAL_FORBIDDEN_MODELS):
            logger.warning("Model '%s' is globally forbidden (deprecated)", model_id)
            return False

        # Then check mode-specific allowlist
        if not self.allowed_models:
            return True  # No further restrictions in GENERAL mode

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
            audit_required=self.mode
            in [ComplianceMode.HIPAA, ComplianceMode.TACTICAL, ComplianceMode.FEDRAMP],
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
    "FLAG_CLASSIFIED_MARKER",
    "FLAG_CUSTOM_BLOCKED",
    "FLAG_INJECTION_ATTEMPT",
    "FLAG_PHI_DETECTED",
    "FLAG_PII_DETECTED",
    "ComplianceHandler",
    "ComplianceMode",
    "ScanResult",
    "SecurityContext",
    "SecurityLevel",
    "SecurityScanner",
    "create_security_context_for_mode",
    "quick_scan",
]
