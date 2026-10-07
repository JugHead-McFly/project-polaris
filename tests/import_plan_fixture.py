"""Synthetic hosted workflow: no application database, NAS, or provider access."""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import socket
from uuid import UUID
from unittest.mock import patch

from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.capture_history import router as capture_router
from app.api.tonight import router as tonight_router
from app.core.auth import CurrentUser, get_current_user
from app.database.database import Base, get_db, get_tenant_db
from app.models import Profile, HostedObservatory
from app.models.capture_history import LibrarySyncCredential

ALICE = UUID("00000000-0000-4000-8000-000000000001")
BOB = UUID("00000000-0000-4000-8000-000000000002")
START = datetime(2025, 1, 15, 20, tzinfo=timezone.utc)
END = START + timedelta(hours=8)
TOKENS = {ALICE: "synthetic-alice-sync", BOB: "synthetic-bob-sync"}


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        fixed = START - timedelta(hours=2)
        return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)


def manifest(hours, key="first", target="M27"):
    return {"sessions": [{
        "source_key": hashlib.sha256(key.encode()).hexdigest(),
        "target": target, "session_name": "Synthetic " + key,
        "captured_at": "2025-01-14T20:00:00Z", "filter_name": "Duo-Band",
        "frame_count": int(hours * 120), "integration_seconds": hours * 3600,
        "evidence_hash": hashlib.sha256(f"{key}:{hours}".encode()).hexdigest(),
    }]}


class Workflow:
    def __init__(self, app):
        self.app = app

    def plan(self, client, user=ALICE):
        response = client.get("/tonight?equatorial_mode_enabled=true",
                              headers={"X-Test-User": str(user)})
        assert response.status_code == 200, response.text
        return response.json()

    def sync(self, client, payload, user=ALICE, token_owner=None):
        return client.post(f"/capture-sync/{user}", json=payload,
                           headers={"Authorization": "Bearer " + TOKENS[token_owner or user]})


@contextmanager
def workflow():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    app = FastAPI()
    app.include_router(capture_router)
    app.include_router(tonight_router)

    def database():
        with Session(engine) as session:
            yield session

    def user(x_test_user: str = Header(default=str(ALICE))):
        if x_test_user not in {str(ALICE), str(BOB)}:
            raise HTTPException(401)
        return CurrentUser(user_id=UUID(x_test_user), email=None, auth_mode="supabase")

    app.dependency_overrides.update({get_db: database, get_tenant_db: database,
                                     get_current_user: user})
    with Session(engine) as db:
        for owner in (ALICE, BOB):
            db.add(Profile(user_id=owner))
            db.add(HostedObservatory(user_id=owner, name="Synthetic observatory",
                latitude=0, longitude=0, timezone_name="UTC", rig_profile_key="dwarf-mini"))
            db.add(LibrarySyncCredential(user_id=owner,
                token_hash=hashlib.sha256(TOKENS[owner].encode()).hexdigest(),
                expires_at=datetime.now(timezone.utc) + timedelta(days=1)))
        db.commit()

    def visibility(object_name, **kwargs):
        altitude = 70 if object_name == "M27" else 50
        return {"known_position": True, "usable_dark_minutes": 480,
                "usable_dark_hours": 8, "maximum_dark_altitude": altitude,
                "average_dark_altitude": altitude,
                "recommended_start_datetime": START, "recommended_end_datetime": END,
                "target_geometry": None}

    weather = {"observing_rating": 5, "status": "Synthetic clear forecast",
               "cloud_cover_percent": 0, "humidity_percent": 30,
               "wind_speed_mph": 2, "temperature_f": 65, "cache_status": "fresh"}
    moon = {"illumination_percent": 5, "altitude_degrees": -20, "above_horizon": False}
    darkness = {"sunset": "2025-01-15 07:00 PM",
                "astronomical_darkness_start": "2025-01-15 08:00 PM",
                "astronomical_darkness_end": "2025-01-16 04:00 AM"}
    # Patch physical inputs only: import, progress, ranking, scheduler, response
    # validation and account filtering run unmodified.
    inputs = {
        "TARGETS": ("M27", "M57"),
        "get_weather_summary": lambda *a, **kw: deepcopy(weather),
        "get_moon_info": lambda **kw: deepcopy(moon),
        "get_darkness_info": lambda **kw: deepcopy(darkness),
        "get_darkness_window_datetimes": lambda **kw: (START - timedelta(hours=1), START, END),
        "get_dark_visibility": visibility,
        "get_altitude_at": lambda **kw: 60,
        "get_moon_separation_at": lambda **kw: 120,
        "get_moon_warning_at": lambda **kw: None,
        "get_transit_time": lambda *a, **kw: None,
    }
    try:
        with ExitStack() as stack:
            for name, value in inputs.items():
                stack.enter_context(patch("app.services.planner_service." + name, value))
            for module in ("planner_service", "scheduler_service"):
                stack.enter_context(patch(f"app.services.{module}.datetime", FixedDateTime))
            # Guard calls through socket.connect; this is not a network sandbox.
            # DNS, connect_ex, subprocesses and native clients are not covered.
            real_connect = socket.socket.connect
            def loopback_only(sock, address):
                if address[0] not in {"127.0.0.1", "::1"}:
                    raise AssertionError("Synthetic workflow must not contact providers")
                return real_connect(sock, address)
            stack.enter_context(patch("socket.socket.connect", loopback_only))
            yield Workflow(app)
    finally:
        engine.dispose()
