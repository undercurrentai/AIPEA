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

import asyncio
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

    def __init__(self, tier_name: str, capacity_bytes: int) -> None:  # pragma: no mutate
        """Initialize storage tier with name and capacity.

        Args:
            tier_name: Human-readable tier identifier
            capacity_bytes: Maximum storage capacity in bytes
        """
        self.tier_name = tier_name  # pragma: no mutate
        self.capacity_bytes = capacity_bytes  # pragma: no mutate


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


class _RowList:
    """Lightweight wrapper around a list of sqlite3.Row to mimic cursor.fetchall()."""

    def __init__(self, rows: list[sqlite3.Row]) -> None:
        self._rows = rows

    def fetchall(self) -> list[sqlite3.Row]:
        return self._rows


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
        with self._db_lock:
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

                # FTS5 virtual table for full-text search
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts
                    USING fts5(content, domain)
                """)

                conn.commit()

                # Rebuild FTS index from existing data if out of sync (migration)
                self._sync_fts_index(conn)

                logger.debug("Database schema initialized")
            except Exception:
                # Close failed connection and reset so _get_connection() creates fresh one
                conn.close()
                self._conn = None
                raise

    def _sync_fts_index(self, conn: sqlite3.Connection) -> None:
        """Ensure FTS index is in sync with knowledge_nodes table.

        Rebuilds the FTS index if the row counts diverge (e.g. after migration
        from a pre-FTS database).
        """
        try:
            fts_count = conn.execute("SELECT COUNT(*) FROM knowledge_fts").fetchone()[0]
            node_count = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
            if fts_count < node_count:
                logger.info(
                    "FTS index out of sync (%d vs %d rows), rebuilding", fts_count, node_count
                )
                self._rebuild_fts_index(conn)
        except sqlite3.OperationalError:
            # FTS table might not exist yet on very first init
            pass

    def _rebuild_fts_index(self, conn: sqlite3.Connection) -> None:
        """Rebuild the FTS index from all rows in knowledge_nodes."""
        conn.execute("DELETE FROM knowledge_fts")
        rows = conn.execute(
            "SELECT rowid, compressed_content, domain FROM knowledge_nodes"
        ).fetchall()
        for row in rows:
            try:
                content = zlib.decompress(row["compressed_content"]).decode("utf-8")
                conn.execute(
                    "INSERT INTO knowledge_fts(rowid, content, domain) VALUES (?, ?, ?)",
                    (row["rowid"], content, row["domain"]),
                )
            except (zlib.error, UnicodeDecodeError) as e:
                logger.warning("Skipping corrupt row %s during FTS rebuild: %s", row["rowid"], e)
        conn.commit()
        logger.info("FTS index rebuilt with %d rows", len(rows))

    async def search(
        self,
        query: str,
        domain: KnowledgeDomain | None = None,
        limit: int = 5,
    ) -> KnowledgeSearchResult:
        """Search the offline knowledge base.

        Retrieves knowledge nodes matching the query using FTS5 full-text
        search, falling back to relevance_score ordering if FTS returns no
        matches. Updates access counts and timestamps for retrieved nodes.

        Args:
            query: Search query (used for FTS matching and logging)
            domain: Optional domain filter to restrict results
            limit: Maximum number of results to return

        Returns:
            KnowledgeSearchResult with matching nodes and metadata
        """
        nodes = await asyncio.to_thread(self._search_sync, query, domain, limit)
        return KnowledgeSearchResult(
            nodes=nodes,
            query=query,
            domain_filter=domain,
            total_matches=len(nodes),
        )

    @staticmethod
    def _fts_escape(query: str) -> str:
        """Escape a user query for safe use in FTS5 MATCH expressions.

        Wraps each token in double-quotes so that special FTS5 characters
        (*, ^, OR, AND, NEAR, etc.) are treated as literals.  Embedded
        double-quotes inside tokens are doubled per FTS5 quoting rules.
        """
        tokens = query.split()
        if not tokens:
            return ""
        return " ".join(f'"{t.replace(chr(34), chr(34) + chr(34))}"' for t in tokens)

    def _fts_search(
        self,
        conn: sqlite3.Connection,
        query: str,
        domain: KnowledgeDomain | None,
        limit: int,
    ) -> sqlite3.Cursor | None:
        """Attempt an FTS5 search. Returns a cursor or None if no results."""
        if not query.strip():
            return None
        fts_query = self._fts_escape(query)
        if not fts_query:
            return None
        try:
            if domain is not None:
                cursor = conn.execute(
                    """
                    SELECT kn.id, kn.domain, kn.compressed_content, kn.relevance_score,
                           kn.security_classification, kn.created_at, kn.access_count
                    FROM knowledge_nodes kn
                    JOIN knowledge_fts fts ON kn.rowid = fts.rowid
                    WHERE knowledge_fts MATCH ? AND kn.domain = ?
                    ORDER BY fts.rank
                    LIMIT ?
                    """,
                    (fts_query, domain.value, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT kn.id, kn.domain, kn.compressed_content, kn.relevance_score,
                           kn.security_classification, kn.created_at, kn.access_count
                    FROM knowledge_nodes kn
                    JOIN knowledge_fts fts ON kn.rowid = fts.rowid
                    WHERE knowledge_fts MATCH ?
                    ORDER BY fts.rank
                    LIMIT ?
                    """,
                    (fts_query, limit),
                )
            # Peek at results — if empty, return None to trigger fallback
            rows = cursor.fetchall()
            if not rows:
                return None
            # Re-wrap rows in a lightweight object that exposes fetchall()
            # so the caller's loop works unchanged.
            return _RowList(rows)  # type: ignore[return-value]
        except sqlite3.OperationalError as e:
            logger.debug("FTS search failed, falling back: %s", e)
            return None

    def _fallback_search(
        self,
        conn: sqlite3.Connection,
        domain: KnowledgeDomain | None,
        limit: int,
    ) -> sqlite3.Cursor:
        """Fallback search ordered by relevance_score (no FTS)."""
        if domain is not None:
            return conn.execute(
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
        return conn.execute(
            """
            SELECT id, domain, compressed_content, relevance_score,
                   security_classification, created_at, access_count
            FROM knowledge_nodes
            ORDER BY relevance_score DESC
            LIMIT ?
            """,
            (limit,),
        )

    def _search_sync(
        self,
        query: str,
        domain: KnowledgeDomain | None,
        limit: int,
    ) -> list[KnowledgeNode]:
        """Synchronous implementation of search (runs in thread pool).

        Uses FTS5 full-text search when a query is provided. Falls back to
        relevance_score ordering if FTS returns no matches or is unavailable.
        """
        limit = max(1, limit)
        logger.debug(
            f"Searching knowledge base: query_len={len(query)}, domain={domain}, limit={limit}"
        )

        with self._with_db_lock() as conn:
            cursor = self._fts_search(conn, query, domain, limit)
            if cursor is None:
                cursor = self._fallback_search(conn, domain, limit)

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

        return await asyncio.to_thread(
            self._add_knowledge_sync, content, domain, classification, relevance_score
        )

    def _add_knowledge_sync(
        self,
        content: str,
        domain: KnowledgeDomain,
        classification: str,
        relevance_score: float,
    ) -> str:
        """Synchronous implementation of add_knowledge (runs in thread pool)."""
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

            # Update FTS index: delete old entry (if upsert) then insert plaintext
            try:
                rowid = conn.execute(
                    "SELECT rowid FROM knowledge_nodes WHERE id = ?", (node_id,)
                ).fetchone()
                if rowid:
                    conn.execute("DELETE FROM knowledge_fts WHERE rowid = ?", (rowid[0],))
                    conn.execute(
                        "INSERT INTO knowledge_fts(rowid, content, domain) VALUES (?, ?, ?)",
                        (rowid[0], content, domain.value),
                    )
                    conn.commit()
            except sqlite3.OperationalError as e:
                logger.debug("FTS update skipped: %s", e)

        logger.info(f"Added knowledge node: id={node_id}, domain={domain.value}")
        return node_id

    async def get_by_id(self, node_id: str) -> KnowledgeNode | None:
        """Retrieve a specific knowledge node by ID.

        Args:
            node_id: Unique node identifier

        Returns:
            KnowledgeNode if found, None otherwise
        """
        return await asyncio.to_thread(self._get_by_id_sync, node_id)

    def _get_by_id_sync(self, node_id: str) -> KnowledgeNode | None:
        """Synchronous implementation of get_by_id (runs in thread pool)."""
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

        return await asyncio.to_thread(self._update_relevance_sync, node_id, new_score)

    def _update_relevance_sync(self, node_id: str, new_score: float) -> bool:
        """Synchronous implementation of update_relevance (runs in thread pool)."""
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
        return await asyncio.to_thread(self._delete_node_sync, node_id)

    def _delete_node_sync(self, node_id: str) -> bool:
        """Synchronous implementation of delete_node (runs in thread pool)."""
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
        return await asyncio.to_thread(self._get_node_count_sync)

    def _get_node_count_sync(self) -> int:
        """Synchronous implementation of get_node_count (runs in thread pool)."""
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
        return await asyncio.to_thread(self._get_storage_stats_sync)

    def _get_storage_stats_sync(self) -> dict[str, int | float]:
        """Synchronous implementation of get_storage_stats (runs in thread pool)."""
        node_count = self._get_node_count_sync()
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
        return await asyncio.to_thread(self._get_domains_summary_sync)

    def _get_domains_summary_sync(self) -> dict[str, int]:
        """Synchronous implementation of get_domains_summary (runs in thread pool)."""
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

        return await asyncio.to_thread(self._prune_low_relevance_sync, threshold, max_delete)

    def _prune_low_relevance_sync(self, threshold: float, max_delete: int) -> int:
        """Synchronous implementation of prune_low_relevance (runs in thread pool)."""
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


# =============================================================================
# SEED KNOWLEDGE
# =============================================================================

# Curated knowledge entries for bootstrapping the offline KB.
# Each tuple: (content, domain, relevance_score)
SEED_KNOWLEDGE: list[tuple[str, KnowledgeDomain, float]] = [
    # TECHNICAL
    (
        "REST API security best practices: Always use HTTPS/TLS for all endpoints. "
        "Implement authentication via OAuth 2.0 or API keys. Apply rate limiting to "
        "prevent abuse. Validate and sanitize all input on the server side. Use CORS "
        "headers to restrict cross-origin access. Never expose stack traces or internal "
        "errors to clients. Implement proper logging and monitoring. Use short-lived "
        "tokens with refresh mechanisms. Apply the principle of least privilege to all "
        "API scopes and permissions.",
        KnowledgeDomain.TECHNICAL,
        0.90,
    ),
    (
        "Python async/await patterns: Use asyncio.gather() for concurrent I/O operations. "
        "Avoid blocking calls in async functions — use asyncio.to_thread() for CPU-bound "
        "or legacy synchronous code. Use async context managers (async with) for resource "
        "management. Prefer asyncio.TaskGroup (Python 3.11+) over gather() for structured "
        "concurrency with proper error propagation. Use asyncio.Lock for shared mutable "
        "state. Never mix sync and async without explicit bridging.",
        KnowledgeDomain.TECHNICAL,
        0.88,
    ),
    (
        "Database optimization strategies: Index columns used in WHERE, JOIN, and ORDER BY "
        "clauses. Use EXPLAIN ANALYZE to identify slow queries. Prefer batch operations over "
        "row-by-row processing. Implement connection pooling to reduce overhead. Use read "
        "replicas for read-heavy workloads. Partition large tables by date or category. "
        "Avoid SELECT *; specify only needed columns. Use prepared statements to prevent "
        "SQL injection and improve plan caching.",
        KnowledgeDomain.TECHNICAL,
        0.85,
    ),
    (
        "Container security hardening: Run containers as non-root users. Use minimal base "
        "images (distroless or Alpine). Scan images for vulnerabilities with Trivy or Grype. "
        "Set resource limits (CPU, memory) to prevent denial of service. Use read-only "
        "filesystems where possible. Never store secrets in images; use runtime injection "
        "via environment variables or secret managers. Implement network policies to restrict "
        "inter-container communication.",
        KnowledgeDomain.TECHNICAL,
        0.85,
    ),
    # CYBERSECURITY
    (
        "OWASP Top 10 (2025 edition) key mitigations: Broken Access Control — enforce "
        "server-side authorization checks. Cryptographic Failures — use TLS 1.3, AES-256, "
        "and avoid deprecated algorithms. Injection — use parameterized queries and input "
        "validation. Insecure Design — threat model during design phase. Security "
        "Misconfiguration — automate hardening with IaC. Vulnerable Components — maintain "
        "SBOM and patch regularly. Authentication Failures — implement MFA and credential "
        "stuffing protection. SSRF — validate and allowlist outbound URLs.",
        KnowledgeDomain.CYBERSECURITY,
        0.92,
    ),
    (
        "Zero Trust Architecture principles: Never trust, always verify. Authenticate and "
        "authorize every access request regardless of network location. Apply least-privilege "
        "access with just-in-time and just-enough-access (JIT/JEA). Assume breach — segment "
        "networks, encrypt data in transit and at rest, use microsegmentation. Continuously "
        "monitor and validate security posture. Use identity as the primary security "
        "perimeter instead of network boundaries.",
        KnowledgeDomain.CYBERSECURITY,
        0.88,
    ),
    # ENGINEERING
    (
        "CI/CD pipeline best practices: Keep builds fast (under 10 minutes for unit tests). "
        "Run tests in parallel where possible. Use caching for dependencies and build "
        "artifacts. Implement trunk-based development with short-lived feature branches. "
        "Require all tests to pass before merging. Automate security scanning (SAST, DAST, "
        "SCA) in the pipeline. Use environment promotion (dev → staging → production) with "
        "approval gates. Implement rollback mechanisms for every deployment.",
        KnowledgeDomain.ENGINEERING,
        0.87,
    ),
    (
        "Microservices communication patterns: Synchronous — REST/HTTP for simple request-"
        "response, gRPC for high-performance inter-service calls. Asynchronous — message "
        "queues (SQS, RabbitMQ) for decoupled processing, event streaming (Kafka) for "
        "real-time data pipelines. Use circuit breakers (e.g., resilience4j) to handle "
        "downstream failures gracefully. Implement retries with exponential backoff and "
        "jitter. Use service mesh (Istio, Linkerd) for observability and traffic management.",
        KnowledgeDomain.ENGINEERING,
        0.85,
    ),
    # GENERAL
    (
        "Effective prompt engineering techniques: Be specific and provide context about the "
        "desired output format. Use system prompts to set the model's role and constraints. "
        "Break complex tasks into smaller, focused prompts. Provide examples (few-shot "
        "learning) for consistent output formatting. Use chain-of-thought prompting for "
        "reasoning tasks. Specify the audience and technical level. Include negative "
        "constraints (what NOT to do). Iterate and refine based on output quality.",
        KnowledgeDomain.GENERAL,
        0.90,
    ),
    (
        "Technical writing best practices: Lead with the most important information. Use "
        "active voice and concrete language. Structure content with clear headings and "
        "logical hierarchy. Include code examples with comments explaining key decisions. "
        "Define technical terms on first use. Use lists for sequential steps or parallel "
        "items. Keep paragraphs focused on a single idea. Include diagrams for complex "
        "architectures. Version your documentation alongside the code it describes.",
        KnowledgeDomain.GENERAL,
        0.82,
    ),
    # MEDICAL
    (
        "HIPAA compliance essentials for software systems: Implement access controls with "
        "role-based permissions. Encrypt PHI at rest (AES-256) and in transit (TLS 1.2+). "
        "Maintain audit logs of all PHI access. Implement automatic session timeouts. "
        "Conduct regular risk assessments. Establish Business Associate Agreements (BAAs) "
        "with all vendors handling PHI. Implement breach notification procedures (72-hour "
        "reporting window). Apply minimum necessary standard — only access PHI needed for "
        "the task at hand.",
        KnowledgeDomain.MEDICAL,
        0.88,
    ),
    # MILITARY
    (
        "Operational security (OPSEC) fundamentals: Identify critical information that could "
        "compromise operations. Analyze potential adversary intelligence collection "
        "capabilities. Assess vulnerabilities in information handling processes. Apply "
        "countermeasures: need-to-know access, compartmentalization, secure communications. "
        "Use classification markings consistently. Conduct regular OPSEC assessments. "
        "Train personnel on social engineering awareness. Implement physical security "
        "controls for sensitive workspaces.",
        KnowledgeDomain.MILITARY,
        0.85,
    ),
    (
        "Military communications security (COMSEC): Use end-to-end encryption for all "
        "tactical communications. Implement frequency hopping and spread-spectrum techniques "
        "for radio communications. Enforce strict key management procedures — rotate "
        "encryption keys on schedule and after suspected compromise. Use TEMPEST-certified "
        "equipment in sensitive facilities to prevent electromagnetic emanation interception. "
        "Maintain communications silence discipline during operations. Use brevity codes and "
        "authentication challenges to verify identity. Ensure redundant communication paths "
        "for mission-critical messaging.",
        KnowledgeDomain.MILITARY,
        0.84,
    ),
    (
        "Tactical decision-making frameworks: OODA loop (Observe, Orient, Decide, Act) for "
        "rapid decision cycles in dynamic environments. MDMP (Military Decision Making "
        "Process) for deliberate planning: receipt of mission, mission analysis, COA "
        "development, COA analysis, COA comparison, COA approval, orders production. Apply "
        "commander's intent to enable decentralized execution. Use red-teaming to stress-test "
        "plans against adversary capabilities. Maintain decision logs for after-action review.",
        KnowledgeDomain.MILITARY,
        0.83,
    ),
    # LOGISTICS
    (
        "Supply chain risk management: Map the full supply chain to identify single points "
        "of failure. Diversify suppliers across geographies. Implement real-time tracking "
        "and visibility tools. Maintain safety stock for critical components. Develop "
        "contingency plans for supplier disruptions. Conduct regular supplier audits and "
        "assessments. Use predictive analytics for demand forecasting. Establish clear "
        "escalation procedures for supply chain incidents.",
        KnowledgeDomain.LOGISTICS,
        0.83,
    ),
    (
        "Field logistics and sustainment operations: Pre-position critical supplies at "
        "forward operating locations. Use push logistics for initial deployment, transition "
        "to pull logistics for sustained operations. Implement automated inventory tracking "
        "with barcode or RFID systems. Plan for fuel, ammunition, water, and medical supply "
        "distribution chains. Establish maintenance recovery points with standardized repair "
        "kits. Use containerization for rapid supply distribution. Coordinate airlift and "
        "ground transport assets for multi-modal delivery.",
        KnowledgeDomain.LOGISTICS,
        0.82,
    ),
    # COMMUNICATIONS
    (
        "Network architecture for resilient communications: Design networks with no single "
        "point of failure using mesh or ring topologies. Implement automatic failover between "
        "primary and backup links. Use software-defined networking (SDN) for dynamic traffic "
        "management. Deploy network segmentation to contain security incidents. Monitor "
        "bandwidth utilization and latency with real-time dashboards. Implement QoS policies "
        "to prioritize mission-critical traffic. Use satellite and HF radio as backup for "
        "terrestrial link failures. Test disaster recovery procedures quarterly.",
        KnowledgeDomain.COMMUNICATIONS,
        0.84,
    ),
    (
        "Secure messaging and collaboration: Use end-to-end encrypted messaging platforms "
        "with ephemeral message options. Implement identity verification through certificate-"
        "based authentication. Enforce message retention policies aligned with compliance "
        "requirements. Use air-gapped systems for classified discussions. Implement data "
        "loss prevention (DLP) controls on outbound communications. Train users on phishing "
        "recognition and social engineering tactics. Maintain audit logs of all message "
        "access for accountability.",
        KnowledgeDomain.COMMUNICATIONS,
        0.82,
    ),
    # MEDICAL (additional)
    (
        "Clinical decision support systems: Integrate evidence-based guidelines into EHR "
        "workflows for real-time alerts. Use severity scoring systems (APACHE, SOFA, qSOFA) "
        "for triage prioritization. Implement drug interaction checking at order entry. "
        "Support differential diagnosis generation from symptom clusters. Maintain audit "
        "trails for all clinical decisions. Ensure AI-assisted diagnostics include confidence "
        "scores and uncertainty quantification. Require human-in-the-loop validation for all "
        "treatment recommendations.",
        KnowledgeDomain.MEDICAL,
        0.86,
    ),
    # GENERAL (additional)
    (
        "Data privacy by design principles: Minimize data collection — only gather what is "
        "strictly necessary. Implement purpose limitation — data used only for stated purposes. "
        "Apply data retention limits with automatic deletion schedules. Use pseudonymization "
        "and anonymization techniques. Provide users with data export and deletion capabilities "
        "(right to be forgotten). Conduct Data Protection Impact Assessments (DPIA) for "
        "high-risk processing. Implement consent management with granular opt-in/opt-out.",
        KnowledgeDomain.GENERAL,
        0.85,
    ),
]


async def seed_knowledge_base(kb: OfflineKnowledgeBase) -> int:
    """Populate an OfflineKnowledgeBase with curated seed knowledge.

    Adds domain-specific knowledge entries covering technical, security,
    engineering, medical, military, and general topics. Existing entries
    with the same content hash are updated (upsert behavior).

    Args:
        kb: The knowledge base to populate

    Returns:
        Number of knowledge entries added/updated
    """
    count = 0
    for content, domain, relevance in SEED_KNOWLEDGE:
        await kb.add_knowledge(content, domain, relevance_score=relevance)
        count += 1
    logger.info("Seeded %d knowledge entries across %d domains", count, len(KnowledgeDomain))
    return count


__all__ = [
    "SEED_KNOWLEDGE",
    "KnowledgeDomain",
    "KnowledgeNode",
    "KnowledgeSearchResult",
    "OfflineKnowledgeBase",
    "StorageTier",
    "seed_knowledge_base",
]
