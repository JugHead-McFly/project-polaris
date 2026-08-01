from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_application_version_has_one_source_of_truth():
    client = TestClient(app)
    response = client.get("/system")
    landing = client.get("/")

    assert settings.VERSION == "1.6.0"
    assert app.version == settings.VERSION
    assert response.status_code == 200
    assert response.json()["version"] == settings.VERSION
    assert len(response.headers["x-request-id"]) == 12
    assert landing.status_code == 200
    assert landing.headers["content-type"].startswith("text/html")
