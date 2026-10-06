import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.capture_history import router
from app.database.database import Base, get_db
from app.models import Profile
from app.models.capture_history import LibrarySyncCredential
from app.schemas.capture_history import CaptureManifest
from app.services.capture_history_service import import_manifest, library_summary, progress_map, history_advice
from scripts.sync_nas_capture_history import build_manifest
from app.services.planner_service import build_target_plan


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def manifest(seconds=33000, digest="a"):
    return CaptureManifest.model_validate({"sessions": [{"source_key": "1"*64, "target": "NGC 7000",
        "session_name": "raw session", "captured_at": "2026-09-30T03:00:00Z", "filter_name": "Duo-Band",
        "frame_count": 1100, "integration_seconds": seconds, "evidence_hash": digest*64}]})


def owner(db):
    user = uuid4()
    db.add(Profile(user_id=user))
    db.commit()
    return user


def test_idempotent_owned_history_updates_without_adding_twice(db):
    alice, bob = owner(db), owner(db)
    assert import_manifest(db, alice, manifest())["sessions_changed"] == 1
    assert import_manifest(db, alice, manifest())["sessions_changed"] == 0
    assert library_summary(db, bob)["session_count"] == 0
    assert library_summary(db, alice)["targets"][0]["object"] == "C 20"
    import_manifest(db, alice, manifest(36000, "b"))
    assert library_summary(db, alice)["targets"][0]["seconds"] == 36000
    import_manifest(db, bob, manifest(100, "c"))
    assert library_summary(db, alice)["targets"][0]["seconds"] == 36000
    with pytest.raises(ValueError):
        import_manifest(db, alice, manifest(9999, "b"))


def test_duplicate_manifest_rejected(db):
    user = owner(db)
    data = manifest()
    data.sessions.append(data.sessions[0])
    with pytest.raises(ValueError):
        import_manifest(db, user, data)
    assert library_summary(db, user)["session_count"] == 0


def test_completed_c20_advice_uses_recorded_hours_without_quality_claim(db):
    user = owner(db)
    import_manifest(db, user, manifest())
    advice = history_advice("C 20", progress_map(library_summary(db, user)))
    assert advice["remaining_seconds"] == 0
    assert advice["current_integration_seconds"] == 33000
    assert advice["goal_hours"] == 8
    assert advice["recommendation_source"] == "catalog_fallback"
    assert history_advice("C 20", {})["remaining_seconds"] == 28800


def test_sync_token_cannot_cross_accounts_or_be_reused_after_expiry(db):
    user, other = owner(db), owner(db)
    token = "private-test-token"
    credential = LibrarySyncCredential(user_id=user, token_hash=hashlib.sha256(token.encode()).hexdigest(),
                                       expires_at=datetime.now(timezone.utc)+timedelta(days=1))
    db.add(credential); db.commit()
    app = FastAPI(); app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)
    payload = manifest().model_dump(mode="json")
    headers = {"Authorization": "Bearer " + token}
    assert client.post(f"/capture-sync/{other}", json=payload, headers=headers).status_code == 401
    assert client.post(f"/capture-sync/{user}", json=payload).status_code == 401
    assert client.post(f"/capture-sync/{user}", json=payload, headers=headers).status_code == 200
    assert client.post(f"/capture-sync/{user}", json=payload, headers=headers).json()["sessions_changed"] == 0
    assert library_summary(db, other)["session_count"] == 0
    credential.expires_at=datetime.now(timezone.utc)-timedelta(seconds=1); db.commit()
    assert client.post(f"/capture-sync/{user}", json=payload, headers=headers).status_code == 401


def test_manifest_counts_only_original_successful_raw_exposures():
    session = "DWARF_RAW_TELE_C 20_EXP_30_GAIN_60_2026-09-30-18-58-21-523"
    frame = "C 20_30s60_Duo-Band_20260930-185932199_28C.fits"
    def proof(relative, digest):
        return {"Relative": relative, "Hash": digest*64}
    original = proof("Astronomy\\"+session+"\\"+frame, "a")
    result = build_manifest([original, original,
        proof("Astronomy\\"+session+"\\failed_"+frame, "b"),
        proof("Astronomy\\"+session+"\\stacked-16_"+frame, "c"),
        proof("Astronomy\\RESTACKED\\"+session+"\\"+frame, "d"),
        proof("Astronomy\\CALI_FRAME\\dark.fits", "e")])
    assert len(result["sessions"]) == 1
    assert result["sessions"][0]["frame_count"] == 1
    assert result["sessions"][0]["integration_seconds"] == 30
    assert result["sessions"][0]["captured_at"] == "2026-10-01T01:58:21.523000+00:00"


def test_recorded_goal_applies_completed_target_penalty():
    start = datetime(2026, 10, 6, 3, tzinfo=timezone.utc)
    end = start + timedelta(hours=5)
    visibility = {"known_position": True, "usable_dark_minutes": 300, "usable_dark_hours": 5,
                  "maximum_dark_altitude": 65, "average_dark_altitude": 50,
                  "recommended_start_datetime": start, "recommended_end_datetime": end, "target_geometry": None}
    with (patch("app.services.planner_service.get_dark_visibility", return_value=visibility),
          patch("app.services.planner_service.get_altitude_at", return_value=50),
          patch("app.services.planner_service.get_moon_separation_at", return_value=90),
          patch("app.services.planner_service.get_moon_warning_at", return_value=None),
          patch("app.services.planner_service.get_transit_time", return_value=None)):
        empty = build_target_plan(object(), "C 20", start, end, use_capture_history=False)
        complete = build_target_plan(object(), "C 20", start, end, use_capture_history=False,
                                     capture_progress={"C 20": {"seconds": 33000}})
    assert empty["planner_score"] - complete["planner_score"] == 75
    assert "reached" in complete["selection_reason"]
