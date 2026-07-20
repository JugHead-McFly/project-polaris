from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.main import app


def test_candidate_sites_can_be_saved_listed_and_removed():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    database = sessionmaker(bind=engine)()
    client = TestClient(app)

    with patch("app.api.candidate_sites.SessionLocal", return_value=database):
        created = client.post(
            "/candidate-sites",
            json={
                "name": "Desert overlook",
                "latitude": 34.54,
                "longitude": -112.4685,
                "bortle_class": 4,
                "access_hours": "Dawn to 10 PM",
                "vehicle_requirement": "four_wheel_drive",
                "property_access": "public_property",
                "parking_setup_confirmed": True,
                "horizon_confirmed": True,
                "notes": "Potential weekend site.",
                "source_url": "https://example.com/site",
            },
        )
        listed = client.get("/candidate-sites")
        updated = client.patch(
            f"/candidate-sites/{created.json()['id']}",
            json={
                "visited": True,
                "star_rating": 4,
                "access_hours": "Open all night for star parties",
                "vehicle_requirement": "high_clearance",
                "property_access": "private_permission",
                "access_confirmed": True,
                "amenities_confirmed": True,
                "notes": "Wide western horizon.",
            },
        )
        removed = client.delete(f"/candidate-sites/{created.json()['id']}")

    assert created.status_code == 201
    assert created.json()["name"] == "Desert overlook"
    assert listed.status_code == 200
    assert listed.json()[0]["bortle_class"] == 4
    assert listed.json()[0]["vehicle_requirement"] == "four_wheel_drive"
    assert listed.json()[0]["property_access"] == "public_property"
    assert listed.json()[0]["parking_setup_confirmed"] is True
    assert listed.json()[0]["horizon_confirmed"] is True
    assert updated.status_code == 200
    assert updated.json()["visited_at"] is not None
    assert updated.json()["star_rating"] == 4
    assert updated.json()["access_hours"] == "Open all night for star parties"
    assert updated.json()["vehicle_requirement"] == "high_clearance"
    assert updated.json()["property_access"] == "private_permission"
    assert updated.json()["access_confirmed"] is True
    assert updated.json()["amenities_confirmed"] is True
    assert updated.json()["notes"] == "Wide western horizon."
    assert removed.status_code == 204


def test_candidate_site_coordinates_are_validated():
    client = TestClient(app)

    response = client.post(
        "/candidate-sites",
        json={"name": "Invalid", "latitude": 91, "longitude": 0},
    )

    assert response.status_code == 422


def test_candidate_sites_can_only_be_rated_after_a_visit():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    database = sessionmaker(bind=engine)()
    client = TestClient(app)

    with patch("app.api.candidate_sites.SessionLocal", return_value=database):
        created = client.post(
            "/candidate-sites",
            json={"name": "Unvisited site", "latitude": 34.54, "longitude": -112.46},
        )
        rating = client.patch(
            f"/candidate-sites/{created.json()['id']}",
            json={"star_rating": 5},
        )

    assert rating.status_code == 422
