from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import log_request


@patch("app.main.capture_request_exception")
def test_unhandled_request_failure_returns_traceable_safe_response(
    capture_exception,
):
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
    capture_exception.assert_called_once()
    _, keyword_arguments = capture_exception.call_args
    assert keyword_arguments["request_id"] == response.json()["request_id"]
    assert keyword_arguments["method"] == "GET"
    assert keyword_arguments["path"] == "/failure"


def test_successful_response_receives_browser_security_headers():
    secured_app = FastAPI()
    secured_app.middleware("http")(log_request)

    @secured_app.get("/healthy")
    def healthy():
        return {"status": "ok"}

    response = TestClient(secured_app).get("/healthy")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == (
        "camera=(), geolocation=(self), microphone=()"
    )
