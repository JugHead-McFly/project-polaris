from fastapi.testclient import TestClient

from app.main import app


def test_landing_page_explains_private_alpha_without_overpromising():
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-frame-options"] == "DENY"
    assert "/operator-assets/landing.css?v=" in response.text
    assert "Plan the night." in response.text
    assert "Keep the wonder." in response.text
    assert "Request private-alpha access" in response.text
    assert 'href="/operator"' in response.text
    assert "advisory only" in response.text
    assert "does not connect to, operate" in response.text
    assert "Project Polaris is a working name" in response.text
    assert "__ASSET_VERSION__" not in response.text
    assert "Content-Security-Policy" in response.headers
    assert "script-src 'none'" in response.headers["content-security-policy"]


def test_landing_page_blocks_scripts_and_uses_only_local_styles():
    response = TestClient(app).get("/")

    policy = response.headers["content-security-policy"]
    assert "script-src 'none'" in policy
    assert "style-src 'self'" in policy
