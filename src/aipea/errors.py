"""AIPEA custom exception hierarchy.

All exceptions raised by AIPEA (and ideally caught by consumers) descend from
:class:`AIPEAError`. This lets callers discriminate AIPEA failures from other
Python exceptions without resorting to broad ``except Exception:`` blocks.

Design notes:
    - Minimal surface area. Five concrete subclasses, one base. Add more only
      when a consumer needs to catch a specific class that isn't already
      expressible with stdlib exceptions.
    - No subclass carries domain-specific state by default. If a subclass
      needs an error code, context payload, or chained cause, add them on
      the specific subclass rather than on the base.
    - Backward-compatible addition. Adding this module does not change any
      existing behavior — no existing code path was raising a custom AIPEA
      exception before this module existed. Consumers that matched on
      specific stdlib exceptions (``httpx.HTTPError``, ``sqlite3.Error``,
      etc.) continue to work.

Hierarchy::

    AIPEAError
    ├── SecurityScanError        # security.py: scan/validation failures
    ├── EnhancementError         # enhancer.py: pipeline failures
    ├── KnowledgeStoreError      # knowledge.py: SQLite / storage failures
    ├── SearchProviderError      # search.py: HTTP provider failures
    └── ConfigError              # config.py: env/TOML resolution failures

Origin: ROADMAP §P5c (investor review 2026-04-11), commit per Wave C3 of the
consolidated response plan.
"""

from __future__ import annotations

__all__ = [
    "AIPEAError",
    "ConfigError",
    "EnhancementError",
    "KnowledgeStoreError",
    "SearchProviderError",
    "SecurityScanError",
]


class AIPEAError(Exception):
    """Base class for all AIPEA-specific errors.

    Catch this to handle any AIPEA-originated failure without masking
    unrelated exceptions from stdlib or third-party code.
    """


class SecurityScanError(AIPEAError):
    """Raised when a security scan cannot complete its work.

    This is a *scanner failure*, not a *detection finding*. A scan that
    successfully reports ``pii_detected:ssn`` is not an error — it returns
    a :class:`~aipea.security.ScanResult`. A scan that cannot compile a
    regex, run a check, or return a result is a ``SecurityScanError``.
    """


class EnhancementError(AIPEAError):
    """Raised when the prompt-enhancement pipeline fails.

    Covers failures in :class:`~aipea.enhancer.AIPEAEnhancer` that are not
    attributable to a specific downstream component (search, knowledge,
    engine). Component-specific failures should use the more specific
    subclass.
    """


class KnowledgeStoreError(AIPEAError):
    """Raised when the offline knowledge store cannot be read or written.

    Wraps ``sqlite3.Error`` / ``OSError`` at the knowledge-module boundary
    so consumers do not need to import ``sqlite3`` to catch AIPEA's KB
    failures.
    """


class SearchProviderError(AIPEAError):
    """Raised when a search provider (Exa, Firecrawl, Context7) fails.

    Wraps provider-specific HTTP, authentication, or parsing failures at
    the ``aipea.search`` boundary. Consumers catch this to fall back to
    offline-tier processing without having to catch ``httpx`` exceptions
    directly.
    """


class ConfigError(AIPEAError):
    """Raised when AIPEA configuration cannot be resolved.

    Covers invalid env var values, malformed TOML, unreadable ``.env``
    files with unexpected permission errors, and contradictions between
    the configured priority chain (env > dotenv > toml > default).
    """
