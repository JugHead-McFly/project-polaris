from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.database.database import Base, get_tenant_db
from app.main import app


def test_application_version_has_one_source_of_truth(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def test_database():
        with Session(engine) as database:
            yield database

    monkeypatch.setitem(app.dependency_overrides, get_tenant_db, test_database)
    client = TestClient(app)
    try:
        response = client.get("/system")
        landing = client.get("/")
    finally:
        engine.dispose()

    assert settings.VERSION == "1.6.0"
    assert app.version == settings.VERSION
    assert response.status_code == 200
    assert response.json()["version"] == settings.VERSION
    assert len(response.headers["x-request-id"]) == 12
    assert landing.status_code == 200
    assert landing.headers["content-type"].startswith("text/html")
