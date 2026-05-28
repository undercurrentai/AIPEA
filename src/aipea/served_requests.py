"""ServedRequest authorization store — ALIG trust boundary (ADR-011, v1.9.0 B1).

Request-bound feedback ingestion. The server issues a single-use, TTL-limited
token for each served request and records the *resolved* context (query type,
chosen strategy, scanner flags, risk score) plus a keyed-HMAC of the source
identity. Untrusted end-user feedback is then accepted ONLY against a valid
token, which the store resolves back to trusted context — closing the
feedback-poisoning surface that a raw ``record_feedback(query_type, strategy,
...)`` call leaves open to a caller who controls those fields.

Security posture:
- Request IDs are unguessable (``secrets.token_urlsafe``), single-use (claimed
  atomically), and TTL-expiring.
- Source identities are stored only as a keyed HMAC-SHA256, never raw.
- The HMAC secret is **required** for source hashing — provided explicitly via
  the ``hmac_key`` argument or the ``AIPEA_LEARNING_HMAC_KEY`` env var. The store
  never silently generates or writes a secret to disk: an explicit-key posture is
  safer than silent generation, and auto-provisioning is intentionally out of
  scope.
- Compliance-gated like the learning engine (ADR-003): TACTICAL never persists;
  HIPAA persists only when explicitly allowed.

stdlib only (sqlite3, threading, hmac, hashlib, secrets, json, os) — no new
runtime deps. Mirrors the SQLite idioms of ``learning.py`` (WAL, RLock, additive
schema, graceful degradation).
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import logging
import os
import secrets
import sqlite3
import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from aipea._types import QueryType
from aipea.security import ComplianceMode

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "aipea_learning.db"
_ENV_DB_PATH = "AIPEA_LEARNING_DB_PATH"
_ENV_HMAC_KEY = "AIPEA_LEARNING_HMAC_KEY"
_DEFAULT_TTL_SECONDS = 7 * 24 * 3600
_REQUEST_ID_BYTES = 32
# Fixed-width, lexicographically-sortable timestamp format shared with the
# SQLite `datetime('now')` default (mirrors learning.py) so `expires_at`
# string comparisons order chronologically.
_TS_FORMAT = "%Y-%m-%d %H:%M:%S"


class ServedRequestError(RuntimeError):
    """Configuration error (e.g. source hashing attempted without an HMAC key)."""


@dataclass(frozen=True)
class ResolvedRequest:
    """Trusted context resolved from a consumed (valid, single-use) token."""

    request_id: str
    query_type: QueryType
    strategy: str
    scan_flags: tuple[str, ...]
    risk_score: float | None
    tenant_id: str
    source_hash: str | None
    compliance_mode: ComplianceMode


class ServedRequestStore:
    """SQLite-backed single-use authorization tokens for request-bound feedback.

    Thread-safe via ``threading.RLock``. Degrades gracefully (no-ops / ``None``)
    if the database is unavailable.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        hmac_key: bytes | str | None = None,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
        allow_hipaa: bool = False,
    ) -> None:
        if ttl_seconds < 1:
            msg = f"ttl_seconds must be >= 1 (got {ttl_seconds})"
            raise ValueError(msg)
        self._ttl = ttl_seconds
        self._allow_hipaa = allow_hipaa
        self._key = self._resolve_key(hmac_key)
        resolved = db_path or os.environ.get(_ENV_DB_PATH, _DEFAULT_DB_PATH)
        self._db_path = Path(resolved)
        self._db_lock = threading.RLock()
        self._conn: sqlite3.Connection | None = None
        try:
            self._conn = self._open_connection()
            self._init_schema()
        except sqlite3.Error:
            logger.warning(
                "Failed to initialise served-request DB at %s; store disabled",
                self._db_path,
                exc_info=True,
            )
            if self._conn is not None:
                with contextlib.suppress(sqlite3.Error):
                    self._conn.close()
            self._conn = None

    @staticmethod
    def _resolve_key(hmac_key: bytes | str | None) -> bytes | None:
        if hmac_key is not None:
            return hmac_key.encode() if isinstance(hmac_key, str) else hmac_key
        env = os.environ.get(_ENV_HMAC_KEY)
        return env.encode() if env else None

    # ------------------------------------------------------------------
    # Connection / schema (mirrors learning.py)
    # ------------------------------------------------------------------

    def _open_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
        except sqlite3.Error:
            with contextlib.suppress(sqlite3.Error):
                conn.close()
            raise
        return conn

    def _init_schema(self) -> None:
        assert self._conn is not None  # noqa: S101 — internal invariant
        with self._db_lock:
            self._conn.executescript(
                """\
                CREATE TABLE IF NOT EXISTS served_requests (
                    request_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    source_hash TEXT,
                    query_type TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    scan_flags TEXT,
                    risk_score REAL,
                    compliance_mode TEXT NOT NULL DEFAULT 'general',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    expires_at TEXT NOT NULL,
                    used INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_served_expires
                    ON served_requests(expires_at);
                """
            )

    @contextmanager
    def _with_db_lock(self) -> Iterator[sqlite3.Connection]:
        with self._db_lock:
            if self._conn is None:
                msg = "ServedRequest DB is not initialised"
                raise sqlite3.OperationalError(msg)
            yield self._conn

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _hash_source(self, tenant_id: str, source_id: str | None) -> str | None:
        if source_id is None:
            return None
        if self._key is None:
            msg = (
                "source hashing requires an HMAC key; set the AIPEA_LEARNING_HMAC_KEY "
                "env var or pass hmac_key=..."
            )
            raise ServedRequestError(msg)
        message = f"{tenant_id}\x00{source_id}".encode()
        return hmac.new(self._key, message, hashlib.sha256).hexdigest()

    def _gate(self, mode: ComplianceMode) -> bool:
        """ADR-003 persistence gate: TACTICAL never; HIPAA only when opted in."""
        if mode == ComplianceMode.TACTICAL:
            return False
        return not (mode == ComplianceMode.HIPAA and not self._allow_hipaa)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def issue(
        self,
        query_type: QueryType,
        strategy: str,
        *,
        tenant_id: str,
        source_id: str | None = None,
        scan_flags: Sequence[str] = (),
        risk_score: float | None = None,
        compliance_mode: ComplianceMode = ComplianceMode.GENERAL,
    ) -> str | None:
        """Issue a single-use token for a served request.

        Returns the opaque ``request_id`` to hand to the end user, or ``None`` if
        the compliance mode forbids persistence or the store is unavailable.
        """
        if not self._gate(compliance_mode):
            return None
        source_hash = self._hash_source(tenant_id, source_id)
        request_id = secrets.token_urlsafe(_REQUEST_ID_BYTES)
        now = datetime.now(UTC)
        created = now.strftime(_TS_FORMAT)
        expires = (now + timedelta(seconds=self._ttl)).strftime(_TS_FORMAT)
        flags_json = json.dumps(list(scan_flags)) if scan_flags else None
        try:
            with self._with_db_lock() as conn:
                conn.execute(
                    "INSERT INTO served_requests "
                    "(request_id, tenant_id, source_hash, query_type, strategy, "
                    "scan_flags, risk_score, compliance_mode, created_at, expires_at, used) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
                    (
                        request_id,
                        tenant_id,
                        source_hash,
                        query_type.value,
                        strategy,
                        flags_json,
                        risk_score,
                        compliance_mode.value,
                        created,
                        expires,
                    ),
                )
                conn.commit()
        except sqlite3.Error:
            logger.warning("Failed to issue served request", exc_info=True)
            return None
        return request_id

    def consume(self, request_id: str) -> ResolvedRequest | None:
        """Atomically claim a valid, unexpired, unused token and resolve its context.

        Returns ``None`` for an unknown, expired, or already-consumed token (the
        ``UPDATE ... WHERE used = 0`` claim guarantees single use even under
        concurrent callers).
        """
        now = datetime.now(UTC).strftime(_TS_FORMAT)
        try:
            with self._with_db_lock() as conn:
                claimed = conn.execute(
                    "UPDATE served_requests SET used = 1 "
                    "WHERE request_id = ? AND used = 0 AND expires_at >= ?",
                    (request_id, now),
                )
                if claimed.rowcount != 1:
                    conn.commit()
                    return None
                row = conn.execute(
                    "SELECT * FROM served_requests WHERE request_id = ?",
                    (request_id,),
                ).fetchone()
                conn.commit()
        except sqlite3.Error:
            logger.warning("Failed to consume served request", exc_info=True)
            return None
        if row is None:  # pragma: no cover — claimed implies the row exists
            return None
        raw_flags = row["scan_flags"]
        flags: tuple[str, ...] = tuple(json.loads(raw_flags)) if raw_flags else ()
        risk = row["risk_score"]
        return ResolvedRequest(
            request_id=request_id,
            query_type=QueryType(row["query_type"]),
            strategy=str(row["strategy"]),
            scan_flags=flags,
            risk_score=float(risk) if risk is not None else None,
            tenant_id=str(row["tenant_id"]),
            source_hash=row["source_hash"],
            compliance_mode=ComplianceMode(row["compliance_mode"]),
        )

    def purge_expired(self) -> int:
        """Delete expired tokens. Returns the number removed."""
        now = datetime.now(UTC).strftime(_TS_FORMAT)
        try:
            with self._with_db_lock() as conn:
                cur = conn.execute("DELETE FROM served_requests WHERE expires_at < ?", (now,))
                conn.commit()
                return cur.rowcount
        except sqlite3.Error:
            logger.warning("Failed to purge served requests", exc_info=True)
            return 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        with self._db_lock:
            if self._conn is not None:
                with contextlib.suppress(sqlite3.Error):
                    self._conn.close()
                self._conn = None

    def __enter__(self) -> ServedRequestStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()
