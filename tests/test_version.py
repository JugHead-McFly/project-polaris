from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_application_version_has_one_source_of_truth():
    response = TestClient(app).get("/")

    assert settings.VERSION == "1.4.0"
    assert app.version == settings.VERSION
    assert response.status_code == 200
    assert response.json()["version"] == settings.VERSION
    assert len(response.headers["x-request-id"]) == 12
