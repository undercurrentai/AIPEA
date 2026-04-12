"""Tests for aipea.errors — custom exception hierarchy.

Wave C3 (ROADMAP §P5c) introduced a minimal exception hierarchy so consumers
can discriminate AIPEA failures without resorting to broad ``except
Exception:``. This test file verifies the hierarchy is wired correctly and
that the expected symbols are re-exported from the package root.
"""

from __future__ import annotations

import pytest

from aipea.errors import (
    AIPEAError,
    ConfigError,
    EnhancementError,
    KnowledgeStoreError,
    SearchProviderError,
    SecurityScanError,
)


class TestExceptionHierarchy:
    def test_base_descends_from_exception(self) -> None:
        assert issubclass(AIPEAError, Exception)

    @pytest.mark.parametrize(
        "subclass",
        [
            SecurityScanError,
            EnhancementError,
            KnowledgeStoreError,
            SearchProviderError,
            ConfigError,
        ],
    )
    def test_subclass_descends_from_base(self, subclass: type[AIPEAError]) -> None:
        """Every concrete subclass must be catchable via AIPEAError."""
        assert issubclass(subclass, AIPEAError)
        assert issubclass(subclass, Exception)

    def test_subclasses_are_distinct(self) -> None:
        """Sibling subclasses must not be substitutable for each other."""
        siblings = [
            SecurityScanError,
            EnhancementError,
            KnowledgeStoreError,
            SearchProviderError,
            ConfigError,
        ]
        for a in siblings:
            for b in siblings:
                if a is b:
                    continue
                assert not issubclass(a, b), f"{a.__name__} should not subclass {b.__name__}"

    def test_aipea_error_catches_all_subclasses(self) -> None:
        """Consumers matching `except AIPEAError:` should catch every concrete type."""
        for exc_type in [
            SecurityScanError,
            EnhancementError,
            KnowledgeStoreError,
            SearchProviderError,
            ConfigError,
        ]:
            with pytest.raises(AIPEAError):
                raise exc_type("test")

    def test_subclasses_are_instantiable_with_message(self) -> None:
        err = SecurityScanError("scan failed: pattern too long")
        assert str(err) == "scan failed: pattern too long"

    def test_subclasses_can_chain_causes(self) -> None:
        """raise X from e should preserve the original exception as __cause__."""
        original = ValueError("underlying problem")
        try:
            try:
                raise original
            except ValueError as e:
                raise ConfigError("wrapped failure") from e
        except ConfigError as wrapped:
            assert wrapped.__cause__ is original


class TestPackageReExports:
    """The 6 exception names must be re-exported from `aipea` directly."""

    def test_aipea_error_reexported(self) -> None:
        import aipea

        assert aipea.AIPEAError is AIPEAError

    def test_all_subclasses_reexported(self) -> None:
        import aipea

        assert aipea.SecurityScanError is SecurityScanError
        assert aipea.EnhancementError is EnhancementError
        assert aipea.KnowledgeStoreError is KnowledgeStoreError
        assert aipea.SearchProviderError is SearchProviderError
        assert aipea.ConfigError is ConfigError

    def test_exports_in_all(self) -> None:
        import aipea

        for name in [
            "AIPEAError",
            "SecurityScanError",
            "EnhancementError",
            "KnowledgeStoreError",
            "SearchProviderError",
            "ConfigError",
        ]:
            assert name in aipea.__all__, f"{name} not in aipea.__all__"
