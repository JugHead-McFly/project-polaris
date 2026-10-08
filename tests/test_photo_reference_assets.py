from fastapi.testclient import TestClient
from app.main import app


def test_standalone_reference_workspace_and_assets_are_served_locally():
    client = TestClient(app)
    html = client.get('/operator-assets/photo-reference.html')
    assert html.status_code == 200
    assert "connect-src 'none'" in html.text
    assert 'Mark true north (0°)' in html.text
    assert 'Mark measured elevation' in html.text
    assert 'Absolute sensor accuracy and aiming error remain unknown' in html.text
    assert 'Not calibrated' in html.text
    assert 'Export references (no image)' in html.text
    for asset in ['photo-reference.js', 'photo-reference.css']:
        assert client.get('/operator-assets/' + asset).status_code == 200
    editor = client.get('/operator-assets/obstruction-editor.js')
    assert '/operator-assets/photo-reference.html' in editor.text
    assert 'rel="noopener"' in editor.text

    sky = client.get('/operator-assets/sky-view.js')
    assert sky.status_code == 200
    assert '/operator-assets/photo-reference.html' in sky.text
    assert 'Photo markers are not angular skyline points' in sky.text
    assert 'Photo-reference JSON belongs only in the photo workspace' in sky.text
    assert 'Switch back to that browser tab' in html.text
    assert 'href="/operator" target="_blank" rel="noopener"' in html.text
