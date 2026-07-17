from fastapi.testclient import TestClient

from app.main import app


def test_operator_dashboard_is_read_only_and_loads_local_assets():
    client = TestClient(app)

    response = client.get("/operator")
    stylesheet = client.get("/operator-assets/operator.css")
    script = client.get("/operator-assets/operator.js")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-store"
    assert "Tonight's safety decision" in response.text
    assert "Read-only advisory" in response.text
    assert "Target progress" in response.text
    assert "Latest captures" in response.text
    assert "Recent sessions" in response.text
    assert "Capture freshness" in response.text
    assert "Weather service" in response.text
    assert "JPL ephemeris" in response.text
    assert "Planner V3 · advisory only · no equipment control" in response.text
    assert stylesheet.status_code == 200
    assert script.status_code == 200
    assert 'fetch("/tonight"' in script.text
    assert 'fetch("/system"' in script.text
    assert 'fetch("/dashboard"' in script.text

    methods = {
        method
        for route in app.routes
        if getattr(route, "path", None) == "/operator"
        for method in getattr(route, "methods", set())
    }
    assert methods == {"GET"}
