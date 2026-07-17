from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import log_request


def test_unhandled_request_failure_returns_traceable_safe_response():
    failing_app = FastAPI()
    failing_app.middleware("http")(log_request)

    @failing_app.get("/failure")
    def failure():
        raise RuntimeError("sensitive internal detail")

    response = TestClient(
        failing_app,
        raise_server_exceptions=False,
    ).get("/failure")

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error."
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert "sensitive internal detail" not in response.text
