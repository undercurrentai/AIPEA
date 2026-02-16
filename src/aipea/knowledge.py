"""
AIPEA Offline Knowledge Base - Air-Gapped Knowledge Storage for Agora IV.

This module provides SQLite-based offline knowledge storage designed for
zero-connectivity (air-gapped) environments. It supports military-grade field
operations, submarines, classified environments, and no-signal areas.

Key features:
- Completely offline operation (no external API calls)
- zlib compression for efficient storage
- Domain-based knowledge organization
- Relevance-based retrieval with access tracking
- Configurable storage tiers for different device capabilities
- Security classification support

Design principles:
- Air-gapped: No network calls, SQLite is the only storage
- Compressed: zlib level 9 for maximum compression
- Indexed: Optimized for domain and relevance-based queries
- Auditable: Access counts and timestamps for tracking
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
import sqlite3
import threading
import zlib
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class KnowledgeDomain(Enum):
    """Knowledge domains for offline cache organization.

    Domains enable filtered retrieval for context-specific queries
    in different operational scenarios.
    """

    MILITARY = "military"
    TECHNICAL = "technical"
    MEDICAL = "medical"
    INTELLIGENCE = "intelligence"
    LOGISTICS = "logistics"
    COMMUNICATIONS = "communications"
    CYBERSECURITY = "cybersecurity"
    ENGINEERING = "engineering"
    GENERAL = "general"


class StorageTier(Enum):
    """Storage capacity tiers for different device capabilities.

    Each tier specifies a name and maximum storage capacity in bytes.
    Select based on target deployment environment.
    """

    ULTRA_COMPACT = ("ultra_compact", 1_000_000_000)  # 1GB - phones, IoT
    COMPACT = ("compact", 5_000_000_000)  # 5GB - tablets
    STANDARD = ("standard", 20_000_000_000)  # 20GB - laptops
    EXTENDED = ("extended", 100_000_000_000)  # 100GB - workstations

    def __init__(self, tier_name: str, capacity_bytes: int) -> None:
        """Initialize storage tier with name and capacity.

        Args:
            tier_name: Human-readable tier identifier
            capacity_bytes: Maximum storage capacity in bytes
        """
        self.tier_name = tier_name
        self.capacity_bytes = capacity_bytes


@dataclass
class KnowledgeNode:
    """A node in the offline knowledge base.

    Represents a single piece of knowledge with domain classification,
    security classification, and usage tracking.

    Attributes:
        id: Unique identifier (SHA256 hash prefix of content)
        domain: Knowledge domain for categorization
        content: Decompressed text content
        relevance_score: Score for ranking retrieval results (0.0-1.0)
        security_classification: Security level (e.g., UNCLASSIFIED, SECRET)
        created_at: Timestamp when knowledge was added
        access_count: Number of times this node has been retrieved
    """

    id: str
    domain: KnowledgeDomain
    content: str
    relevance_score: float
    security_classification: str
    created_at: datetime
    access_count: int = 0


@dataclass
class KnowledgeSearchResult:
    """Result from a knowledge base search.

    Wraps KnowledgeNode with search-specific metadata.

    Attributes:
        nodes: List of matching knowledge nodes
        query: Original search query
        domain_filter: Domain filter applied (if any)
        total_matches: Total number of matches before limit
    """

    nodes: list[KnowledgeNode]
    query: str
    domain_filter: KnowledgeDomain | None = None
    total_matches: int = 0


class OfflineKnowledgeBase:
    """SQLite-based offline knowledge storage for air-gapped operation.

    This class provides a completely offline knowledge base using SQLite
    for storage. All content is compressed using zlib for efficient
    storage on constrained devices.

    Key features:
    - No external dependencies or network calls
    - Automatic compression with zlib level 9
    - Domain-based indexing for fast filtered queries
    - Relevance scoring with automatic access tracking
    - Support for security classifications
    - Configurable storage tiers for different deployments

    Example:
        >>> kb = OfflineKnowledgeBase("knowledge.db", StorageTier.COMPACT)
        >>> node_id = await kb.add_knowledge(
        ...     "Field communication protocols: Use FHSS...",
        ...     KnowledgeDomain.MILITARY,
        ...     classification="SECRET"
        ... )
        >>> results = await kb.search("communication protocols")
    """

    def __init__(
        self,
        db_path: str = "aipea_knowledge.db",
        tier: StorageTier = StorageTier.STANDARD,
    ) -> None:
        """Initialize the offline knowledge base.

        Creates the SQLite database and required tables/indexes if they
        don't exist. The database is stored at the specified path.

        Args:
            db_path: Path to SQLite database file
            tier: Storage tier for capacity limits
        """
        self.db_path = Path(db_path)
        self.tier = tier
        self._conn: sqlite3.Connection | None = None
        self._db_lock = threading.RLock()  # Thread-safe database access
        self._init_db()
        logger.info(
            f"Initialized OfflineKnowledgeBase: db={self.db_path}, "
            f"tier={tier.tier_name}, capacity={tier.capacity_bytes / 1e9:.1f}GB"
        )

    def close(self) -> None:
        """Close the database connection if open.

        Should be called when the knowledge base is no longer needed,
        especially in test environments to avoid ResourceWarning.
        """
        if self._conn is not None:
            with contextlib.suppress(Exception):
                self._conn.close()
            self._conn = None
            logger.debug("Database connection closed")

    def __enter__(self) -> OfflineKnowledgeBase:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: object) -> None:
        """Context manager exit - closes database connection."""
        self.close()

    def __del__(self) -> None:
        """Destructor to ensure connection is closed.

        Safety net for cases where close() is not explicitly called
        and context manager is not used.
        """
        self.close()

    @contextmanager
    def _with_db_lock(self) -> Iterator[sqlite3.Connection]:
        """Context manager for thread-safe database access.

        Acquires the database lock and returns the connection.
        This ensures that only one thread accesses the database at a time,
        which is required when using check_same_thread=False.

        Yields:
            Active SQLite connection with row factory configured
        """
        with self._db_lock:
            yield self._get_connection()

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection.

        Reuses existing connection if available to reduce overhead.
        This provides connection pooling behavior for the single-connection case.

        Note: When using check_same_thread=False, callers must use _with_db_lock()
        to ensure thread-safe access. Direct use of _get_connection() should only
        be done when already holding the lock.

        Returns:
            Active SQLite connection with row factory configured
        """
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self) -> None:
        """Initialize database schema with tables and indexes.

        Creates:
        - knowledge_nodes table for storing compressed content
        - Indexes on domain and relevance_score for fast retrieval
        """
        with self._db_lock:
            conn = self._get_connection()
            try:
                # Create main knowledge storage table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_nodes (
                        id TEXT PRIMARY KEY,
                        domain TEXT NOT NULL,
                        content_hash TEXT NOT NULL,
                        compressed_content BLOB NOT NULL,
                        access_count INTEGER DEFAULT 0,
                        last_accessed TIMESTAMP,
                        relevance_score REAL DEFAULT 0.5,
                        security_classification TEXT DEFAULT 'UNCLASSIFIED',
                        version INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create indexes for efficient querying
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_knowledge_domain ON knowledge_nodes(domain)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_knowledge_relevance "
                    "ON knowledge_nodes(relevance_score DESC)"
                )

                # Create combined index for filtered relevance queries
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_knowledge_domain_relevance "
                    "ON knowledge_nodes(domain, relevance_score DESC)"
                )

                conn.commit()
                logger.debug("Database schema initialized")
            except Exception:
                # Close failed connection and reset so _get_connection() creates fresh one
                conn.close()
                self._conn = None
                raise

    async def search(
        self,
        query: str,
        domain: KnowledgeDomain | None = None,
        limit: int = 5,
    ) -> list[KnowledgeNode]:
        """Search the offline knowledge base.

        Retrieves knowledge nodes matching the optional domain filter,
        ordered by relevance score. Updates access counts and timestamps
        for retrieved nodes.

        Note: This is a simple relevance-based search. In production,
        a more sophisticated text search (FTS5) or embedding-based
        similarity search would be used.

        Args:
            query: Search query (currently used for logging only)
            domain: Optional domain filter to restrict results
            limit: Maximum number of results to return

        Returns:
            List of KnowledgeNode objects ordered by relevance
        """
        logger.debug(
            f"Searching knowledge base: query_len={len(query)}, domain={domain}, limit={limit}"
        )

        with self._with_db_lock() as conn:
            if domain is not None:
                cursor = conn.execute(
                    """
                    SELECT id, domain, compressed_content, relevance_score,
                           security_classification, created_at, access_count
                    FROM knowledge_nodes
                    WHERE domain = ?
                    ORDER BY relevance_score DESC
                    LIMIT ?
                    """,
                    (domain.value, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT id, domain, compressed_content, relevance_score,
                           security_classification, created_at, access_count
                    FROM knowledge_nodes
                    ORDER BY relevance_score DESC
                    LIMIT ?
                    """,
                    (limit,),
                )

            results: list[KnowledgeNode] = []
            node_ids: list[str] = []

            for row in cursor.fetchall():
                try:
                    # Decompress content
                    compressed_content = row["compressed_content"]
                    content = zlib.decompress(compressed_content).decode("utf-8")

                    # Parse created_at timestamp
                    created_at_str = row["created_at"]
                    if created_at_str:
                        try:
                            created_at = datetime.fromisoformat(created_at_str)
                        except ValueError:
                            created_at = datetime.now(UTC)
                    else:
                        created_at = datetime.now(UTC)

                    node = KnowledgeNode(
                        id=row["id"],
                        domain=KnowledgeDomain(row["domain"]),
                        content=content,
                        relevance_score=row["relevance_score"],
                        security_classification=row["security_classification"],
                        created_at=created_at,
                        access_count=row["access_count"],
                    )
                    results.append(node)
                    # Bug fix: Only track node_id for access count update
                    # AFTER successful decompression and node creation
                    node_ids.append(row["id"])

                except (zlib.error, UnicodeDecodeError, ValueError) as e:
                    logger.warning(f"Failed to reconstruct node {row['id']}: {e}")
                    continue

            # Update access counts and timestamps for retrieved nodes
            if node_ids:
                now = datetime.now(UTC).isoformat()
                # Update each node individually to avoid dynamic SQL construction
                # This is safe and avoids SQL injection warnings from static analysis
                for nid in node_ids:
                    conn.execute(
                        """
                        UPDATE knowledge_nodes
                        SET access_count = access_count + 1,
                            last_accessed = ?
                        WHERE id = ?
                        """,
                        (now, nid),
                    )
                conn.commit()

        logger.debug(f"Found {len(results)} knowledge nodes for query")
        return results

    async def add_knowledge(
        self,
        content: str,
        domain: KnowledgeDomain,
        classification: str = "UNCLASSIFIED",
        relevance_score: float = 0.5,
    ) -> str:
        """Add knowledge to the offline database.

        Compresses content using zlib level 9 for maximum compression
        and stores it with domain classification and security level.

        Args:
            content: Text content to store
            domain: Knowledge domain for categorization
            classification: Security classification level
            relevance_score: Initial relevance score (0.0-1.0)

        Returns:
            Node ID (first 16 chars of content SHA256 hash)

        Raises:
            ValueError: If content is empty or relevance_score is invalid
        """
        if not content:
            raise ValueError("Content cannot be empty")

        if not 0.0 <= relevance_score <= 1.0:
            raise ValueError("relevance_score must be between 0.0 and 1.0")

        # Generate content-based ID
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        node_id = content_hash[:16]

        # Compress content with maximum compression
        compressed = zlib.compress(content.encode("utf-8"), level=9)
        compression_ratio = len(content) / len(compressed) if compressed else 0

        logger.debug(
            f"Adding knowledge: id={node_id}, domain={domain.value}, "
            f"size={len(content)}, compressed={len(compressed)}, "
            f"ratio={compression_ratio:.2f}x"
        )

        now = datetime.now(UTC).isoformat()

        with self._with_db_lock() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_nodes
                (id, domain, content_hash, compressed_content, relevance_score,
                 security_classification, last_accessed, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    domain = excluded.domain,
                    content_hash = excluded.content_hash,
                    compressed_content = excluded.compressed_content,
                    relevance_score = excluded.relevance_score,
                    security_classification = excluded.security_classification
                """,
                (
                    node_id,
                    domain.value,
                    content_hash,
                    compressed,
                    relevance_score,
                    classification,
                    now,
                    now,
                ),
            )
            conn.commit()

        logger.info(f"Added knowledge node: id={node_id}, domain={domain.value}")
        return node_id

    async def get_by_id(self, node_id: str) -> KnowledgeNode | None:
        """Retrieve a specific knowledge node by ID.

        Args:
            node_id: Unique node identifier

        Returns:
            KnowledgeNode if found, None otherwise
        """
        with self._with_db_lock() as conn:
            cursor = conn.execute(
                """
                SELECT id, domain, compressed_content, relevance_score,
                       security_classification, created_at, access_count
                FROM knowledge_nodes
                WHERE id = ?
                """,
                (node_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            try:
                content = zlib.decompress(row["compressed_content"]).decode("utf-8")
                created_at_str = row["created_at"]
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str)
                    except ValueError:
                        created_at = datetime.now(UTC)
                else:
                    created_at = datetime.now(UTC)

                return KnowledgeNode(
                    id=row["id"],
                    domain=KnowledgeDomain(row["domain"]),
                    content=content,
                    relevance_score=row["relevance_score"],
                    security_classification=row["security_classification"],
                    created_at=created_at,
                    access_count=row["access_count"],
                )
            except (zlib.error, UnicodeDecodeError, ValueError) as e:
                logger.warning(f"Failed to reconstruct node {node_id}: {e}")
                return None

    async def update_relevance(self, node_id: str, new_score: float) -> bool:
        """Update the relevance score for a knowledge node.

        Args:
            node_id: Unique node identifier
            new_score: New relevance score (0.0-1.0)

        Returns:
            True if update succeeded, False if node not found
        """
        if not 0.0 <= new_score <= 1.0:
            raise ValueError("new_score must be between 0.0 and 1.0")

        with self._with_db_lock() as conn:
            cursor = conn.execute(
                "UPDATE knowledge_nodes SET relevance_score = ? WHERE id = ?",
                (new_score, node_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    async def delete_node(self, node_id: str) -> bool:
        """Delete a knowledge node by ID.

        Args:
            node_id: Unique node identifier

        Returns:
            True if deletion succeeded, False if node not found
        """
        with self._with_db_lock() as conn:
            cursor = conn.execute(
                "DELETE FROM knowledge_nodes WHERE id = ?",
                (node_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    async def get_node_count(self) -> int:
        """Get the total number of knowledge nodes.

        Returns:
            Total count of nodes in the database
        """
        with self._with_db_lock() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM knowledge_nodes")
            result = cursor.fetchone()
            return result[0] if result else 0

    async def get_storage_stats(self) -> dict[str, int | float]:
        """Get storage statistics for the knowledge base.

        Returns:
            Dictionary with storage statistics including:
            - node_count: Total number of nodes
            - db_size_bytes: Size of database file
            - capacity_bytes: Maximum capacity for tier
            - utilization_percent: Storage utilization percentage
        """
        node_count = await self.get_node_count()
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
        capacity = self.tier.capacity_bytes
        utilization = (db_size / capacity * 100) if capacity > 0 else 0

        return {
            "node_count": node_count,
            "db_size_bytes": db_size,
            "capacity_bytes": capacity,
            "utilization_percent": round(utilization, 2),
        }

    async def get_domains_summary(self) -> dict[str, int]:
        """Get count of nodes per domain.

        Returns:
            Dictionary mapping domain names to node counts
        """
        with self._with_db_lock() as conn:
            cursor = conn.execute("""
                SELECT domain, COUNT(*) as count
                FROM knowledge_nodes
                GROUP BY domain
                ORDER BY count DESC
                """)
            return {row[0]: row[1] for row in cursor.fetchall()}

    async def prune_low_relevance(
        self,
        threshold: float = 0.1,
        max_delete: int = 100,
    ) -> int:
        """Prune nodes with low relevance scores.

        Used to enforce storage limits by removing least relevant content.

        Args:
            threshold: Relevance score threshold (delete nodes below this)
            max_delete: Maximum number of nodes to delete in one operation

        Returns:
            Number of nodes deleted
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")
        if max_delete <= 0:
            raise ValueError("max_delete must be greater than 0")

        with self._with_db_lock() as conn:
            cursor = conn.execute(
                """
                DELETE FROM knowledge_nodes
                WHERE id IN (
                    SELECT id FROM knowledge_nodes
                    WHERE relevance_score < ?
                    ORDER BY relevance_score ASC, last_accessed ASC
                    LIMIT ?
                )
                """,
                (threshold, max_delete),
            )
            conn.commit()
            deleted = cursor.rowcount

        if deleted > 0:
            logger.info(f"Pruned {deleted} low-relevance knowledge nodes")

        return deleted


__all__ = [
    "KnowledgeDomain",
    "KnowledgeNode",
    "KnowledgeSearchResult",
    "OfflineKnowledgeBase",
    "StorageTier",
]
