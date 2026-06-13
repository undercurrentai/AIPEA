"""Tests for the ServedRequest authorization store (ALIG trust boundary, B1)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aipea._types import QueryType
from aipea.security import ComplianceMode
from aipea.served_requests import ResolvedRequest, ServedRequestError, ServedRequestStore

_KEY = "unit-test-hmac-key"
_TS = "%Y-%m-%d %H:%M:%S"


def _store(tmp_path: Path, **kw: object) -> ServedRequestStore:
    return ServedRequestStore(db_path=tmp_path / "sr.db", hmac_key=_KEY, **kw)  # type: ignore[arg-type]


def test_issue_consume_roundtrip(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        token = store.issue(
            QueryType.TECHNICAL,
            "alpha",
            tenant_id="t1",
            source_id="user-7",
            scan_flags=["pii_detected:email"],
            risk_score=0.25,
        )
        assert token is not None
        resolved = store.consume(token)
        assert isinstance(resolved, ResolvedRequest)
        assert resolved.query_type is QueryType.TECHNICAL
        assert resolved.strategy == "alpha"
        assert resolved.scan_flags == ("pii_detected:email",)
        assert resolved.risk_score == 0.25
        assert resolved.tenant_id == "t1"
        assert resolved.source_hash is not None  # keyed-HMAC, never the raw id
        assert "user-7" not in (resolved.source_hash or "")
        assert resolved.compliance_mode is ComplianceMode.GENERAL
    finally:
        store.close()


def test_single_use_replay_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        token = store.issue(QueryType.TECHNICAL, "alpha", tenant_id="t1")
        assert token is not None
        assert store.consume(token) is not None
        assert store.consume(token) is None  # already used
    finally:
        store.close()


def test_unknown_token_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        assert store.consume("not-a-real-token") is None
    finally:
        store.close()


def test_expired_token_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        token = store.issue(QueryType.TECHNICAL, "alpha", tenant_id="t1")
        assert token is not None
        # White-box: force the token into the past, then it must not consume.
        past = (datetime.now(UTC) - timedelta(hours=1)).strftime(_TS)
        assert store._conn is not None
        store._conn.execute(
            "UPDATE served_requests SET expires_at = ? WHERE request_id = ?",
            (past, token),
        )
        store._conn.commit()
        assert store.consume(token) is None
    finally:
        store.close()


def test_purge_expired(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        token = store.issue(QueryType.TECHNICAL, "alpha", tenant_id="t1")
        assert token is not None
        assert store.purge_expired() == 0  # not yet expired
        past = (datetime.now(UTC) - timedelta(hours=1)).strftime(_TS)
        assert store._conn is not None
        store._conn.execute("UPDATE served_requests SET expires_at = ?", (past,))
        store._conn.commit()
        assert store.purge_expired() == 1
    finally:
        store.close()


@pytest.mark.parametrize(
    "mode,allow_hipaa,expect_token",
    [
        (ComplianceMode.GENERAL, False, True),
        (ComplianceMode.TACTICAL, False, False),  # never persists
        (ComplianceMode.HIPAA, False, False),  # default-deny
        (ComplianceMode.HIPAA, True, True),  # explicit opt-in
    ],
    ids=["general", "tactical-blocked", "hipaa-default-deny", "hipaa-opt-in"],
)
def test_compliance_gating(
    tmp_path: Path, mode: ComplianceMode, allow_hipaa: bool, expect_token: bool
) -> None:
    store = _store(tmp_path, allow_hipaa=allow_hipaa)
    try:
        token = store.issue(QueryType.TECHNICAL, "alpha", tenant_id="t1", compliance_mode=mode)
        assert (token is not None) is expect_token
    finally:
        store.close()


def test_source_hash_keyed_and_deterministic(tmp_path: Path) -> None:
    store_a = ServedRequestStore(db_path=tmp_path / "a.db", hmac_key="key-A")
    store_a2 = ServedRequestStore(db_path=tmp_path / "a2.db", hmac_key="key-A")
    store_b = ServedRequestStore(db_path=tmp_path / "b.db", hmac_key="key-B")
    try:
        h_a = store_a._hash_source("t1", "user-7")
        h_a2 = store_a2._hash_source("t1", "user-7")
        h_b = store_b._hash_source("t1", "user-7")
        assert h_a == h_a2  # deterministic under the same key
        assert h_a != h_b  # keyed: different key -> different hash
        assert store_a._hash_source("t1", None) is None  # no source -> no hash
    finally:
        store_a.close()
        store_a2.close()
        store_b.close()


def test_source_hash_requires_key(tmp_path: Path) -> None:
    store = ServedRequestStore(db_path=tmp_path / "nokey.db")  # no key provided
    try:
        # No source_id needs no key.
        assert store.issue(QueryType.TECHNICAL, "alpha", tenant_id="t1") is not None
        # A source_id without a key is a configuration error.
        with pytest.raises(ServedRequestError):
            store.issue(QueryType.TECHNICAL, "alpha", tenant_id="t1", source_id="user-7")
    finally:
        store.close()


def test_invalid_ttl_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ServedRequestStore(db_path=tmp_path / "x.db", hmac_key=_KEY, ttl_seconds=0)


def test_graceful_degradation_on_corrupt_db(tmp_path: Path) -> None:
    bad = tmp_path / "bad.db"
    bad.write_text("not a sqlite database")
    store = ServedRequestStore(db_path=bad, hmac_key=_KEY)
    try:
        assert store._conn is None  # init degraded
        assert store.issue(QueryType.TECHNICAL, "alpha", tenant_id="t1") is None
        assert store.consume("anything") is None
        assert store.purge_expired() == 0
    finally:
        store.close()


def test_context_manager(tmp_path: Path) -> None:
    with ServedRequestStore(db_path=tmp_path / "cm.db", hmac_key=_KEY) as store:
        token = store.issue(QueryType.TECHNICAL, "alpha", tenant_id="t1")
        assert token is not None
        assert store.consume(token) is not None
