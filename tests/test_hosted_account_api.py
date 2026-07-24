from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import AuthenticationError
from app.core.auth import CurrentUser
from app.core.auth import get_auth_service
from app.database.database import Base
from app.database.database import get_tenant_db
from app.main import app


ALICE_ID = UUID("d5fe97a5-dfc1-4a78-96b9-719dec266ca7")
BOB_ID = UUID("697d7fc2-a433-4cf7-a92f-5f917f93b899")


class TwoUserAuthService:
    def authenticate(self, token):
        identities = {
            "alice-token": CurrentUser(
                user_id=ALICE_ID,
                email="alice@example.com",
                auth_mode="supabase",
            ),
            "bob-token": CurrentUser(
                user_id=BOB_ID,
                email="bob@example.com",
                auth_mode="supabase",
            ),
        }
        try:
            return identities[token]
        except (KeyError, TypeError) as error:
            raise AuthenticationError("invalid") from error


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def observatory_payload(name="Alice's Observatory"):
    return {
        "name": name,
        "latitude": 33.25,
        "longitude": -111.75,
        "coordinates_are_approximate": True,
        "elevation_m": 390,
        "timezone_name": "America/Phoenix",
        "bortle_class": 6,
    }


def test_alice_and_bob_cannot_cross_observatory_boundary():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    database_factory = sessionmaker(bind=engine)

    def database_override():
        database = database_factory()
        try:
            yield database
        finally:
            database.close()

    app.dependency_overrides[get_auth_service] = (
        lambda: TwoUserAuthService()
    )
    app.dependency_overrides[get_tenant_db] = database_override
    client = TestClient(app)
    try:
        alice_profile = client.put(
            "/profile",
            headers=auth_header("alice-token"),
            json={
                "display_name": "Alice",
                "onboarding_state": "location",
            },
        )
        bob_profile = client.put(
            "/profile",
            headers=auth_header("bob-token"),
            json={
                "display_name": "Bob",
                "onboarding_state": "location",
            },
        )
        created = client.post(
            "/observatories",
            headers=auth_header("alice-token"),
            json=observatory_payload(),
        )
        observatory_id = created.json()["id"]

        alice_list = client.get(
            "/observatories",
            headers=auth_header("alice-token"),
        )
        bob_list = client.get(
            "/observatories",
            headers=auth_header("bob-token"),
        )
        bob_direct_read = client.get(
            f"/observatories/{observatory_id}",
            headers=auth_header("bob-token"),
        )
        bob_update = client.patch(
            f"/observatories/{observatory_id}",
            headers=auth_header("bob-token"),
            json={"name": "Stolen Observatory"},
        )
        bob_delete = client.delete(
            f"/observatories/{observatory_id}",
            headers=auth_header("bob-token"),
        )
        forged_owner = client.post(
            "/observatories",
            headers=auth_header("bob-token"),
            json={
                **observatory_payload("Forged Observatory"),
                "user_id": str(ALICE_ID),
            },
        )
        alice_still_owns = client.get(
            f"/observatories/{observatory_id}",
            headers=auth_header("alice-token"),
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert alice_profile.status_code == 200
    assert alice_profile.json()["user_id"] == str(ALICE_ID)
    assert bob_profile.status_code == 200
    assert bob_profile.json()["user_id"] == str(BOB_ID)
    assert created.status_code == 201
    assert alice_list.status_code == 200
    assert [item["id"] for item in alice_list.json()] == [
        observatory_id
    ]
    assert bob_list.status_code == 200
    assert bob_list.json() == []
    assert bob_direct_read.status_code == 404
    assert bob_update.status_code == 404
    assert bob_delete.status_code == 404
    assert forged_owner.status_code == 422
    assert alice_still_owns.status_code == 200
    assert alice_still_owns.json()["name"] == "Alice's Observatory"


def test_observatory_requires_profile_and_valid_timezone():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    database_factory = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    def database_override():
        database = database_factory()
        try:
            yield database
        finally:
            database.close()

    app.dependency_overrides[get_auth_service] = (
        lambda: TwoUserAuthService()
    )
    app.dependency_overrides[get_tenant_db] = database_override
    client = TestClient(app)
    try:
        missing_profile = client.post(
            "/observatories",
            headers=auth_header("alice-token"),
            json=observatory_payload(),
        )
        invalid_timezone = client.post(
            "/observatories",
            headers=auth_header("alice-token"),
            json={
                **observatory_payload(),
                "timezone_name": "Arizona/Imaginary",
            },
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert missing_profile.status_code == 409
    assert invalid_timezone.status_code == 422
