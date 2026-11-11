"""Fixture-only history presentation: no raw files or application database."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.database.database import Base, get_db
from app.models import LegacyCapture, Profile
from app.models.capture_history import HostedCaptureSession, LibrarySyncCredential
from app.schemas.capture_history import CaptureManifest
from app.services.capture_history_service import (
    import_manifest, library_summary, progress_map, synced_history_for_target,
)
from import_plan_fixture import ALICE, BOB, manifest, workflow


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def add_owner(db):
    owner = uuid4()
    db.add(Profile(user_id=owner))
    db.commit()
    return owner


@pytest.mark.parametrize("target, alias", [("M39", "NGC7092"), ("M37", "NGC2099")])
def test_total_verified_integration_reconciles_aliases_without_queries(db, target, alias):
    alice, bob = add_owner(db), add_owner(db)
    first = manifest(2, "first", target)
    first["sessions"][0]["captured_at"] = "2026-10-01T01:58:21.523000Z"
    second = manifest(.25, "second", alias)
    second["sessions"][0]["captured_at"] = "2026-10-31T23:59:00Z"
    batch = CaptureManifest.model_validate({"sessions": first["sessions"] + second["sessions"]})
    assert import_manifest(db, alice, batch)["sessions_changed"] == 2
    assert import_manifest(db, alice, batch)["sessions_changed"] == 0
    # Same source key in a different account is independent evidence.
    import_manifest(db, bob, CaptureManifest.model_validate(manifest(10, "first", target)))
    # A longer designation must never match by substring.
    import_manifest(db, alice, CaptureManifest.model_validate(manifest(10, "unrelated", target + "0")))
    db.add(LibrarySyncCredential(user_id=alice, token_hash="a" * 64,
        expires_at=datetime(2027, 1, 1, tzinfo=timezone.utc),
        last_synced_at=datetime(2026, 11, 2, tzinfo=timezone.utc)))
    db.commit()

    statements = []
    def record_statement(_conn, _cursor, statement, _params, _context, _many):
        statements.append(statement)
    event.listen(db.bind, "before_cursor_execute", record_statement)
    try:
        summary = library_summary(db, alice)
        count = len(statements)
        for name in (target, alias):
            history = synced_history_for_target(name, progress_map(summary), summary["legacy"]["targets"])
            assert history == {"session_count": 2, "total_integration_seconds": 8100, "legacy_record_count": 0}
        assert len(statements) == count  # Presentation adds no database calls.
        assert count == 3  # One owned session read, credential read and legacy read.
        assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)
    finally:
        event.remove(db.bind, "before_cursor_execute", record_statement)
    assert not db.dirty and not db.new and not db.deleted
    rows = db.scalars(select(HostedCaptureSession).where(HostedCaptureSession.user_id == alice)).all()
    assert {row.target for row in rows} == {target, alias, target + "0"}
    assert {row.source_key for row in rows} == {row["source_key"] for row in batch.model_dump()["sessions"]} | {
        manifest(10, "unrelated", target + "0")["sessions"][0]["source_key"]}
    assert synced_history_for_target(target, progress_map(library_summary(db, bob)))["total_integration_seconds"] == 36000


def test_single_verified_session_returns_total_without_date_or_frame_plumbing(db):
    user = add_owner(db)
    data = CaptureManifest.model_validate(manifest(.5, target="M39"))
    import_manifest(db, user, data)
    summary = library_summary(db, user)
    history = synced_history_for_target("NGC7092", progress_map(summary))
    assert history == {"session_count": 1, "total_integration_seconds": 1800, "legacy_record_count": 0}
    assert "latest_session_at" not in summary["targets"][0]
    # Existing frame-based library/filter displays retain their original data.
    assert summary["targets"][0]["frames"] == 60
    assert summary["targets"][0]["filter_progress"][0]["captured_frames"] == 60


def test_legacy_only_never_credits_unverified_duration(db):
    alice, bob = add_owner(db), add_owner(db)
    for index, stamp in enumerate(("malformed", "2025-01-14 20:00:00", None)):
        db.add(LegacyCapture(user_id=alice, source_key=str(index) * 64, target="NGC7092",
            original_observation_time=stamp, reported_integration_seconds=999999,
            evidence_hash="a" * 64, review_flags=["timezone_unverified"]))
    db.commit()
    summary = library_summary(db, alice)
    history = synced_history_for_target("M39", progress_map(summary), summary["legacy"]["targets"])
    assert history == {"session_count": 0, "total_integration_seconds": None, "legacy_record_count": 3}
    other = library_summary(db, bob)
    assert synced_history_for_target("M39", progress_map(other), other["legacy"]["targets"])["legacy_record_count"] == 0
    # Overlapping older stacks never add verified time.
    import_manifest(db, alice, CaptureManifest.model_validate(manifest(1, target="M39")))
    summary = library_summary(db, alice)
    history = synced_history_for_target("M39", progress_map(summary), summary["legacy"]["targets"])
    assert history["total_integration_seconds"] == 3600
    assert history["legacy_record_count"] == 3


def test_unknown_values_do_not_become_zero_or_partial_totals():
    assert synced_history_for_target("M39", None) is None
    empty = synced_history_for_target("M39", {})
    assert empty["session_count"] == 0 and empty["total_integration_seconds"] is None
    history = synced_history_for_target("M39", {
        "M39": {"sessions": 1, "seconds": None, "frames": 30, "latest_session_at": None},
        "NGC7092": {"sessions": 1, "seconds": 900, "frames": 30, "latest_session_at": "2026-10-31T00:00:00+00:00"},
    })
    assert history["total_integration_seconds"] is None
    assert "frame_count" not in history and "latest_session_at" not in history
    assert synced_history_for_target("M39", {"M39": {"sessions": 1, "seconds": 0, "frames": 0}})["total_integration_seconds"] == 0


def test_hosted_api_serializes_history_and_plans_never_count_as_captures():
    with workflow() as flow, TestClient(flow.app) as client:
        empty = flow.plan(client)
        assert empty["schedule"]["blocks"]  # Planned exposure is not recorded exposure.
        assert empty["recommended_target"]["synced_capture_history"] == {
            "session_count": 0, "total_integration_seconds": None, "legacy_record_count": 0}
        data = manifest(.5)
        assert flow.sync(client, data).status_code == 200
        assert flow.sync(client, data).json()["sessions_changed"] == 0
        payload = flow.plan(client)
        target = payload["recommended_target"]
        assert target["object"] == "M27"
        assert target["synced_capture_history"] == {"session_count": 1,
            "total_integration_seconds": 1800, "legacy_record_count": 0}
        assert target["latest_capture"] is None  # Local-capture semantics remain separate.
        assert payload["backup_target"]["synced_capture_history"]["session_count"] == 0
        older = manifest(.25, "older-session", "NGC6853")
        older["sessions"][0]["captured_at"] = "2025-01-13T20:00:00Z"
        assert flow.sync(client, older).status_code == 200
        combined = flow.plan(client)["recommended_target"]["synced_capture_history"]
        assert combined == {"session_count": 2, "total_integration_seconds": 2700, "legacy_record_count": 0}
        assert flow.plan(client, BOB)["recommended_target"]["synced_capture_history"]["session_count"] == 0
        provider = flow.app.dependency_overrides[get_db]()
        db = next(provider)
        try:
            db.add(LegacyCapture(user_id=ALICE, source_key="f" * 64, target="M57",
                original_observation_time="malformed", reported_integration_seconds=999999,
                evidence_hash="a" * 64, review_flags=[]))
            db.commit()
        finally:
            provider.close()
        assert flow.plan(client)["backup_target"]["synced_capture_history"]["legacy_record_count"] == 1
