from fastapi.testclient import TestClient
from types import SimpleNamespace

from app.main import app
from app.api import operator as operator_api


def test_operator_dashboard_is_read_only_and_loads_local_assets():
    client = TestClient(app)

    response = client.get("/operator")
    stylesheet = client.get("/operator-assets/operator.css")
    script = client.get("/operator-assets/operator.js")
    leaflet_stylesheet = client.get("/operator-assets/leaflet.css")
    leaflet_script = client.get("/operator-assets/leaflet.js")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-store"
    assert "/operator-assets/operator.css?v=" in response.text
    assert "/operator-assets/operator.js?v=" in response.text
    assert "__ASSET_VERSION__" not in response.text
    assert "Tonight's imaging recommendation" in response.text
    assert 'id="observatory-name">Local observatory</small>' in response.text
    assert "Read-only advisory" in response.text
    assert "Polaris advises. The operator makes the final decision." not in response.text
    assert (
        '<article class="summary-card" id="scheduled-summary">\n'
        '          <p class="eyebrow">Scheduled imaging</p>'
    ) in response.text
    assert 'href="/operator" data-view-link="tonight"' in response.text
    assert 'href="/operator/portfolio" data-view-link="portfolio"' in response.text
    assert 'href="/operator/quality" data-view-link="quality"' in response.text
    assert 'href="/operator/history" data-view-link="history"' in response.text
    assert 'href="/operator/locations" data-view-link="locations"' in response.text
    assert 'href="/operator/data" data-view-link="data"' in response.text
    assert 'id="simulation-banner"' in response.text
    assert "Target progress" in response.text
    assert "Quality by target" in response.text
    assert "Target quality summaries" in response.text
    assert "Scores are not\n            used to rank unrelated objects" in response.text
    assert "Latest captures" in response.text
    assert "Observing log" not in response.text
    assert "Latest capture" in response.text
    assert "History updated" in response.text
    assert "Usable target window" in response.text
    assert "Sub-exposure" in response.text
    assert "Capture library" in response.text
    assert "Capture files linked" in response.text
    assert 'id="moon-visual"' in response.text
    assert 'id="image-dialog"' in response.text
    assert "Weather service" not in response.text
    assert "JPL ephemeris" not in response.text
    assert "Planner V3 · advisory only · no equipment control" in response.text
    assert stylesheet.status_code == 200
    assert script.status_code == 200
    assert leaflet_stylesheet.status_code == 200
    assert leaflet_script.status_code == 200
    assert 'fetch("/tonight"' in script.text
    assert 'fetch("/system"' in script.text
    assert 'fetch(`/dashboard?include_all_history=${historyExpanded}`' in script.text
    assert "capture.polaris_id" not in script.text
    assert "Capture quality" in script.text
    assert "Average capture quality" not in script.text
    assert "activity-preview" not in script.text
    assert "appendImageButton" in script.text
    assert "openImageViewer" in script.text
    assert "portfolio-preview-button" in script.text
    assert "displayMeasuredNumber" in script.text
    assert "friendlyFilterLabel" in script.text
    assert "Imaging aim:" in script.text
    assert "Aim guide:" in script.text
    assert "Colors and science of ${objectName}" in script.text
    assert "Displayed image quality:" in script.text
    assert "Stars detected in this image" in script.text
    assert '"Captured at"' in script.text
    assert "bortleLabel" in script.text
    assert "toggleHistory" in script.text
    assert "include_all_history" in script.text
    assert "renderCaptureLocations" in script.text
    assert "tile.openstreetmap.org" in script.text
    assert "scrollWheelZoom" in script.text
    assert "lightpollutionmap.app" in response.text
    assert "DarkSky International" in response.text
    assert 'id="candidate-light-pollution-link"' in response.text
    assert "updateCandidateResearchLinks" in script.text
    assert ".toFixed(1)" in script.text
    assert 'id="bortle-map-key"' in response.text
    assert 'id="tracked-location-summary"' in response.text
    assert "Bortle not recorded" in script.text
    assert "list.hidden = decision === \"Proceed\"" in script.text
    assert 'id="capture-location-map"' in response.text
    assert 'id="candidate-site-map-key"' in response.text
    assert 'id="candidate-site-sort"' in response.text
    assert "Darkest sky, then closest" in response.text
    assert "renderCandidateSiteMapKey" in script.text
    assert "sortedCandidateSites" in script.text
    assert 'id="candidate-site-comparison"' in response.text
    assert "Compare sites" in response.text
    assert "toggleCandidateSiteComparison" in script.text
    assert 'id="visited-site-list"' in response.text
    assert "Visited sites" in response.text
    assert "renderSavedSiteLists" in script.text
    assert "candidateDirectionsUrl" in script.text
    assert "appendDirectionsIcon" in script.text
    assert "Get directions" in script.text
    assert "candidate-site-actions" in script.text
    assert "Mark visited" in script.text
    assert "Update site details" in script.text
    assert "4x4 required" in script.text
    assert "Public property" in script.text
    assert "Site readiness" in response.text
    assert "Site readiness:" in script.text
    assert "applyImmaculateDemo" in script.text
    assert 'demoMode === "immaculate"' in script.text
    assert 'demoMode === "map-overlap"' in script.text
    assert 'id="location-map-demo"' in response.text
    assert "/operator-assets/leaflet.js" in response.text
    assert ").slice(0, 3)" in script.text
    assert "setupMinutes = 5" in script.text
    assert "schedule-reason" in script.text
    assert "quality-component-grid" in script.text
    assert "appendObjectProfile" in script.text
    assert "Why it’s remarkable" in script.text
    assert "renderQualityByTarget" in script.text
    assert "right.average_quality - left.average_quality" not in script.text
    assert "scored_capture_count" in script.text
    assert "target.scored_capture_count < target.capture_count" in script.text
    assert "average as a baseline" not in script.text
    assert "${pointsLabel(points)} / ${maxPoints} pts" in script.text
    assert "qualityComponentInfo" in script.text
    assert '"stars"' in script.text
    assert "quality-info-dialog" in response.text
    assert "Individual image analysis" in response.text
    assert "renderMoonVisual" in script.text
    assert 'setText("observatory-name", data.observatory?.name' in script.text

    section_paths = {
        "/operator",
        "/operator/portfolio",
        "/operator/quality",
        "/operator/history",
        "/operator/locations",
        "/operator/data",
    }
    for path in section_paths:
        section_response = client.get(path)
        assert section_response.status_code == 200
        assert section_response.headers["cache-control"] == "no-store"
        methods = {
            method
            for route in app.routes
            if getattr(route, "path", None) == path
            for method in getattr(route, "methods", set())
        }
        assert methods == {"GET"}


def test_operator_preview_is_limited_to_a_capture_preview(tmp_path, monkeypatch):
    preview = tmp_path / "M57" / "jpg" / "POL-TEST.jpg"
    preview.parent.mkdir(parents=True)
    preview.write_bytes(b"preview")
    monkeypatch.setattr(operator_api, "TARGETS_ROOT", tmp_path)

    capture = SimpleNamespace(
        object_name="M57",
        polaris_id="POL-TEST",
    )

    assert operator_api._find_preview_path(capture) == preview
    assert operator_api._find_preview_path(
        SimpleNamespace(
            object_name="../outside",
            polaris_id="POL-TEST",
        )
    ) is None
    assert operator_api._find_preview_path(
        SimpleNamespace(
            object_name="M57",
            polaris_id="../../POL-TEST",
        )
    ) is None
