#!/usr/bin/env python3
"""Tests for aipea_offline_knowledge.py - Offline Knowledge Base.

Tests cover:
- KnowledgeDomain and StorageTier enums
- KnowledgeNode and KnowledgeSearchResult dataclasses
- OfflineKnowledgeBase CRUD operations
- Search functionality with domain filtering
- Storage statistics and pruning
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator
from datetime import UTC, datetime

import pytest

from aipea.knowledge import (
    KnowledgeDomain,
    KnowledgeNode,
    KnowledgeSearchResult,
    OfflineKnowledgeBase,
    StorageTier,
)

# =============================================================================
# ENUM TESTS
# =============================================================================


class TestKnowledgeDomain:
    """Tests for KnowledgeDomain enum."""

    def test_all_domains_exist(self) -> None:
        """Test that all expected domains are defined."""
        assert KnowledgeDomain.MILITARY.value == "military"
        assert KnowledgeDomain.TECHNICAL.value == "technical"
        assert KnowledgeDomain.MEDICAL.value == "medical"
        assert KnowledgeDomain.INTELLIGENCE.value == "intelligence"
        assert KnowledgeDomain.LOGISTICS.value == "logistics"
        assert KnowledgeDomain.COMMUNICATIONS.value == "communications"
        assert KnowledgeDomain.CYBERSECURITY.value == "cybersecurity"
        assert KnowledgeDomain.ENGINEERING.value == "engineering"
        assert KnowledgeDomain.GENERAL.value == "general"

    def test_domain_count(self) -> None:
        """Test that the expected number of domains exists."""
        assert len(KnowledgeDomain) == 9


class TestStorageTier:
    """Tests for StorageTier enum."""

    def test_ultra_compact_tier(self) -> None:
        """Test ultra compact tier properties."""
        tier = StorageTier.ULTRA_COMPACT
        assert tier.tier_name == "ultra_compact"
        assert tier.capacity_bytes == 1_000_000_000  # 1GB

    def test_compact_tier(self) -> None:
        """Test compact tier properties."""
        tier = StorageTier.COMPACT
        assert tier.tier_name == "compact"
        assert tier.capacity_bytes == 5_000_000_000  # 5GB

    def test_standard_tier(self) -> None:
        """Test standard tier properties."""
        tier = StorageTier.STANDARD
        assert tier.tier_name == "standard"
        assert tier.capacity_bytes == 20_000_000_000  # 20GB

    def test_extended_tier(self) -> None:
        """Test extended tier properties."""
        tier = StorageTier.EXTENDED
        assert tier.tier_name == "extended"
        assert tier.capacity_bytes == 100_000_000_000  # 100GB


# =============================================================================
# DATACLASS TESTS
# =============================================================================


class TestKnowledgeNode:
    """Tests for KnowledgeNode dataclass."""

    def test_creation(self) -> None:
        """Test creating a knowledge node."""
        now = datetime.now(UTC)
        node = KnowledgeNode(
            id="abc123",
            domain=KnowledgeDomain.MILITARY,
            content="Test content",
            relevance_score=0.8,
            security_classification="SECRET",
            created_at=now,
            access_count=5,
        )
        assert node.id == "abc123"
        assert node.domain == KnowledgeDomain.MILITARY
        assert node.content == "Test content"
        assert node.relevance_score == 0.8
        assert node.security_classification == "SECRET"
        assert node.access_count == 5

    def test_default_access_count(self) -> None:
        """Test that access_count defaults to 0."""
        node = KnowledgeNode(
            id="test",
            domain=KnowledgeDomain.GENERAL,
            content="Test",
            relevance_score=0.5,
            security_classification="UNCLASSIFIED",
            created_at=datetime.now(UTC),
        )
        assert node.access_count == 0


class TestKnowledgeSearchResult:
    """Tests for KnowledgeSearchResult dataclass."""

    def test_creation_with_defaults(self) -> None:
        """Test creating a search result with default values."""
        result = KnowledgeSearchResult(
            nodes=[],
            query="test query",
        )
        assert result.nodes == []
        assert result.query == "test query"
        assert result.domain_filter is None
        assert result.total_matches == 0

    def test_creation_with_all_fields(self) -> None:
        """Test creating a search result with all fields."""
        nodes = [
            KnowledgeNode(
                id="node1",
                domain=KnowledgeDomain.MEDICAL,
                content="Medical content",
                relevance_score=0.9,
                security_classification="UNCLASSIFIED",
                created_at=datetime.now(UTC),
            )
        ]
        result = KnowledgeSearchResult(
            nodes=nodes,
            query="medical help",
            domain_filter=KnowledgeDomain.MEDICAL,
            total_matches=10,
        )
        assert len(result.nodes) == 1
        assert result.domain_filter == KnowledgeDomain.MEDICAL
        assert result.total_matches == 10


# =============================================================================
# OFFLINE KNOWLEDGE BASE TESTS
# =============================================================================


class TestOfflineKnowledgeBase:
    """Tests for OfflineKnowledgeBase class."""

    @pytest.fixture
    def temp_db(self) -> Generator[str, None, None]:
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)

    @pytest.fixture
    def kb(self, temp_db: str) -> Generator[OfflineKnowledgeBase, None, None]:
        """Create a knowledge base with proper cleanup."""
        knowledge_base = OfflineKnowledgeBase(temp_db, StorageTier.COMPACT)
        yield knowledge_base
        knowledge_base.close()

    def test_initialization(self, temp_db: str) -> None:
        """Test knowledge base initialization."""
        with OfflineKnowledgeBase(temp_db, StorageTier.COMPACT) as kb:
            assert kb.db_path.name == os.path.basename(temp_db)
            assert kb.tier == StorageTier.COMPACT

    @pytest.mark.asyncio
    async def test_add_and_get_knowledge(self, kb: OfflineKnowledgeBase) -> None:
        """Test adding and retrieving knowledge."""
        node_id = await kb.add_knowledge(
            content="Test knowledge content for retrieval",
            domain=KnowledgeDomain.TECHNICAL,
            classification="UNCLASSIFIED",
            relevance_score=0.75,
        )

        assert len(node_id) == 16  # First 16 chars of SHA256

        # Retrieve by ID
        node = await kb.get_by_id(node_id)
        assert node is not None
        assert node.content == "Test knowledge content for retrieval"
        assert node.domain == KnowledgeDomain.TECHNICAL
        assert node.relevance_score == 0.75

    @pytest.mark.asyncio
    async def test_add_empty_content_raises(self, kb: OfflineKnowledgeBase) -> None:
        """Test that empty content raises ValueError."""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            await kb.add_knowledge(
                content="",
                domain=KnowledgeDomain.GENERAL,
            )

    @pytest.mark.asyncio
    async def test_add_invalid_relevance_raises(self, kb: OfflineKnowledgeBase) -> None:
        """Test that invalid relevance score raises ValueError."""
        with pytest.raises(ValueError, match="relevance_score must be between"):
            await kb.add_knowledge(
                content="Test",
                domain=KnowledgeDomain.GENERAL,
                relevance_score=1.5,
            )

    @pytest.mark.asyncio
    async def test_search_without_domain(self, kb: OfflineKnowledgeBase) -> None:
        """Test searching without domain filter."""
        await kb.add_knowledge("Content A", KnowledgeDomain.MILITARY, relevance_score=0.9)
        await kb.add_knowledge("Content B", KnowledgeDomain.MEDICAL, relevance_score=0.8)
        await kb.add_knowledge("Content C", KnowledgeDomain.TECHNICAL, relevance_score=0.7)

        results = await kb.search("test query", limit=10)
        assert len(results) == 3
        # Should be sorted by relevance
        assert results[0].relevance_score >= results[1].relevance_score

    @pytest.mark.asyncio
    async def test_search_with_domain_filter(self, kb: OfflineKnowledgeBase) -> None:
        """Test searching with domain filter."""
        await kb.add_knowledge("Military info", KnowledgeDomain.MILITARY, relevance_score=0.9)
        await kb.add_knowledge("Medical info", KnowledgeDomain.MEDICAL, relevance_score=0.8)

        results = await kb.search("query", domain=KnowledgeDomain.MILITARY)
        assert len(results) == 1
        assert results[0].domain == KnowledgeDomain.MILITARY

    @pytest.mark.asyncio
    async def test_get_nonexistent_node(self, kb: OfflineKnowledgeBase) -> None:
        """Test getting a node that doesn't exist."""
        node = await kb.get_by_id("nonexistent123")
        assert node is None

    @pytest.mark.asyncio
    async def test_update_relevance(self, kb: OfflineKnowledgeBase) -> None:
        """Test updating relevance score."""
        node_id = await kb.add_knowledge(
            "Test content",
            KnowledgeDomain.GENERAL,
            relevance_score=0.5,
        )

        success = await kb.update_relevance(node_id, 0.9)
        assert success is True

        node = await kb.get_by_id(node_id)
        assert node is not None
        assert node.relevance_score == 0.9

    @pytest.mark.asyncio
    async def test_update_relevance_invalid_score_raises(self, kb: OfflineKnowledgeBase) -> None:
        """Test that invalid new_score raises ValueError."""
        node_id = await kb.add_knowledge("Test", KnowledgeDomain.GENERAL)

        with pytest.raises(ValueError, match="new_score must be between"):
            await kb.update_relevance(node_id, -0.5)

    @pytest.mark.asyncio
    async def test_delete_node(self, kb: OfflineKnowledgeBase) -> None:
        """Test deleting a node."""
        node_id = await kb.add_knowledge("To delete", KnowledgeDomain.GENERAL)

        success = await kb.delete_node(node_id)
        assert success is True

        node = await kb.get_by_id(node_id)
        assert node is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_node(self, kb: OfflineKnowledgeBase) -> None:
        """Test deleting a nonexistent node returns False."""
        success = await kb.delete_node("nonexistent")
        assert success is False

    @pytest.mark.asyncio
    async def test_get_node_count(self, kb: OfflineKnowledgeBase) -> None:
        """Test getting node count."""
        assert await kb.get_node_count() == 0

        await kb.add_knowledge("Content 1", KnowledgeDomain.GENERAL)
        await kb.add_knowledge("Content 2", KnowledgeDomain.MILITARY)

        assert await kb.get_node_count() == 2

    @pytest.mark.asyncio
    async def test_get_storage_stats(self, kb: OfflineKnowledgeBase) -> None:
        """Test getting storage statistics."""
        await kb.add_knowledge("Test content", KnowledgeDomain.GENERAL)

        stats = await kb.get_storage_stats()
        assert stats["node_count"] == 1
        assert stats["db_size_bytes"] > 0
        assert stats["capacity_bytes"] == StorageTier.COMPACT.capacity_bytes
        assert 0 <= stats["utilization_percent"] <= 100

    @pytest.mark.asyncio
    async def test_get_domains_summary(self, kb: OfflineKnowledgeBase) -> None:
        """Test getting domains summary."""
        await kb.add_knowledge("Military 1", KnowledgeDomain.MILITARY)
        await kb.add_knowledge("Military 2", KnowledgeDomain.MILITARY)
        await kb.add_knowledge("Medical 1", KnowledgeDomain.MEDICAL)

        summary = await kb.get_domains_summary()
        assert summary.get("military") == 2
        assert summary.get("medical") == 1

    @pytest.mark.asyncio
    async def test_prune_low_relevance(self, kb: OfflineKnowledgeBase) -> None:
        """Test pruning low-relevance nodes."""
        await kb.add_knowledge("High relevance", KnowledgeDomain.GENERAL, relevance_score=0.9)
        await kb.add_knowledge("Low relevance", KnowledgeDomain.GENERAL, relevance_score=0.05)

        assert await kb.get_node_count() == 2

        deleted = await kb.prune_low_relevance(threshold=0.1)
        assert deleted == 1
        assert await kb.get_node_count() == 1

    @pytest.mark.asyncio
    async def test_prune_invalid_threshold_raises(self, kb: OfflineKnowledgeBase) -> None:
        """Test that invalid threshold raises ValueError."""
        with pytest.raises(ValueError, match="threshold must be between"):
            await kb.prune_low_relevance(threshold=1.5)

    @pytest.mark.asyncio
    async def test_access_count_increments_on_search(self, kb: OfflineKnowledgeBase) -> None:
        """Test that access count is incremented on search."""
        node_id = await kb.add_knowledge("Searchable", KnowledgeDomain.GENERAL, relevance_score=0.9)

        # Initial access count
        node = await kb.get_by_id(node_id)
        assert node is not None
        initial_count = node.access_count

        # Search should increment access count
        await kb.search("query")

        node = await kb.get_by_id(node_id)
        assert node is not None
        assert node.access_count > initial_count

    @pytest.mark.asyncio
    async def test_concurrent_add_and_search(self, kb: OfflineKnowledgeBase) -> None:
        """Test that concurrent operations are thread-safe.

        Bug fix: SQLite with check_same_thread=False needs locking.
        """
        import asyncio

        async def add_knowledge(index: int) -> str:
            """Add knowledge node."""
            return await kb.add_knowledge(
                f"Concurrent content {index}",
                KnowledgeDomain.TECHNICAL,
                relevance_score=0.5 + index * 0.01,
            )

        async def search_knowledge() -> list:
            """Search knowledge base."""
            return await kb.search("concurrent")

        # Run concurrent operations
        add_tasks = [add_knowledge(i) for i in range(10)]
        search_tasks = [search_knowledge() for _ in range(5)]

        # Execute all tasks concurrently - should not raise errors
        all_tasks = add_tasks + search_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)

        # Verify no exceptions occurred
        for result in results:
            assert not isinstance(result, Exception), f"Concurrent operation failed: {result}"

        # Verify all nodes were added
        count = await kb.get_node_count()
        assert count >= 10

    @pytest.mark.asyncio
    async def test_failed_decompression_skips_access_update(self, temp_db: str) -> None:
        """Test that failed decompressions don't increment access count.

        Bug fix: access_count should only update for successfully retrieved nodes.
        """
        import sqlite3

        # Create knowledge base and add a valid node
        kb = OfflineKnowledgeBase(temp_db, StorageTier.COMPACT)
        try:
            valid_id = await kb.add_knowledge(
                "Valid content", KnowledgeDomain.GENERAL, relevance_score=0.9
            )

            # Manually corrupt a node's compressed content
            corrupt_id = "corrupt_node123"
            conn = sqlite3.connect(temp_db)
            conn.execute(
                """
                INSERT INTO knowledge_nodes
                (id, domain, content_hash, compressed_content, relevance_score,
                 security_classification, access_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    corrupt_id,
                    "general",
                    "fake_hash",
                    b"not_valid_zlib_data",  # Invalid compressed data
                    0.95,  # High relevance to ensure it's included in search
                    "UNCLASSIFIED",
                    0,
                ),
            )
            conn.commit()
            conn.close()

            # Search should return the valid node but skip the corrupt one
            results = await kb.search("query", limit=10)

            # Valid node should be in results
            assert any(n.id == valid_id for n in results)
            # Corrupt node should NOT be in results
            assert not any(n.id == corrupt_id for n in results)

            # Check that corrupt node's access_count was NOT incremented
            conn = sqlite3.connect(temp_db)
            cursor = conn.execute(
                "SELECT access_count FROM knowledge_nodes WHERE id = ?",
                (corrupt_id,),
            )
            row = cursor.fetchone()
            conn.close()
            assert row is not None
            assert row[0] == 0, "Corrupt node's access_count should not be incremented"

        finally:
            kb.close()


# =============================================================================
# BUG-HUNT REGRESSION TESTS
# =============================================================================


class TestAddKnowledgePreservesAccessCount:
    """Regression: re-adding same content must not reset access_count to 0."""

    @pytest.mark.asyncio
    async def test_upsert_preserves_access_count(self) -> None:
        """Adding the same content twice should preserve access_count from first insert."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            kb = OfflineKnowledgeBase(db_path, StorageTier.COMPACT)

            # Add initial content
            node_id = await kb.add_knowledge(
                content="Test content for upsert",
                domain=KnowledgeDomain.GENERAL,
            )

            # Simulate access_count being incremented (manually set to 5)
            with kb._with_db_lock() as conn:
                conn.execute(
                    "UPDATE knowledge_nodes SET access_count = 5 WHERE id = ?",
                    (node_id,),
                )
                conn.commit()

            # Re-add the same content (same hash -> same id)
            node_id_2 = await kb.add_knowledge(
                content="Test content for upsert",
                domain=KnowledgeDomain.GENERAL,
            )

            assert node_id == node_id_2, "Same content should produce same node ID"

            # Verify access_count is preserved (not reset to 0)
            with kb._with_db_lock() as conn:
                cursor = conn.execute(
                    "SELECT access_count FROM knowledge_nodes WHERE id = ?",
                    (node_id,),
                )
                row = cursor.fetchone()

            assert row is not None
            assert row[0] == 5, f"access_count should be preserved (5), got {row[0]}"

            kb.close()
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
