from fastapi.testclient import TestClient
from types import SimpleNamespace

from app.main import app
from app.api import operator as operator_api


def test_operator_dashboard_is_read_only_and_loads_local_assets():
    client = TestClient(app)

    assert app.docs_url == "/docs"
    assert app.redoc_url == "/redoc"
    assert app.openapi_url == "/openapi.json"

    response = client.get("/operator")
    stylesheet = client.get("/operator-assets/operator.css")
    script = client.get("/operator-assets/operator.js")
    leaflet_stylesheet = client.get("/operator-assets/leaflet.css")
    leaflet_script = client.get("/operator-assets/leaflet.js")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-store"
    assert ".hosted-recommendation.status-loading #hosted-opportunity-score" in stylesheet.text
    assert "font-size: clamp(52px, 5vw, 64px);" in stylesheet.text
    assert (
        ".hosted-command-board {\n"
        "  grid-area: command;\n"
        "  display: flex;\n"
        "  flex-direction: column;\n"
        "  align-self: stretch;"
    ) in stylesheet.text
    assert (
        ".hosted-session-plan {\n"
        "  display: grid;\n"
        "  gap: 12px;\n"
        "  margin-top: auto;"
    ) in stylesheet.text
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
    assert 'id="portfolio-search"' in response.text
    assert 'id="portfolio-filter"' in response.text
    assert 'id="quality-search"' in response.text
    assert 'id="quality-filter"' in response.text
    assert 'class="history-panel-actions"' in response.text
    assert "View all captures" in response.text
    assert "Scores are not\n            used to rank unrelated objects" in response.text
    assert "Latest captures" in response.text
    assert "Observing log" not in response.text
    assert "Latest capture" in response.text
    assert "History updated" in response.text
    assert "Usable target window" in response.text
    assert 'id="target-forecast"' in response.text
    assert "Sub-exposure" in response.text
    assert 'data-term-info="sub-exposure"' in response.text
    assert 'data-term-info="gain"' in response.text
    assert 'data-term-info="filter"' in response.text
    assert 'data-term-info="bortle"' in response.text
    assert 'id="hosted-rig-profile"' in response.text
    assert "Smart telescope profile" in response.text
    assert "termDetails" in script.text
    assert "The part of the night when the Sun is far enough below the horizon" in script.text
    assert "A 1 to 9 estimate of sky brightness" in script.text
    assert "How long each individual camera frame should collect light" in script.text
    assert "Capture library" in response.text
    assert "Capture files linked" in response.text
    assert 'id="moon-visual"' in response.text
    assert 'id="image-dialog"' in response.text
    assert "Weather service" not in response.text
    assert "JPL ephemeris" not in response.text
    assert "Planner V3 · advisory only · no equipment control" not in response.text
    assert stylesheet.status_code == 200
    assert script.status_code == 200
    assert leaflet_stylesheet.status_code == 200
    assert leaflet_script.status_code == 200
    assert "equatorial_mode_enabled=${eqEnabled}" in script.text
    assert "Allow EQ-mode exposures" in response.text
    assert 'class="tracking-mode-options"' in response.text
    assert "Alt-Az" in response.text
    assert "Leave unchecked for Alt-Az-safe exposures" in response.text
    assert 'const EQ_MODE_PREFERENCE_KEY = "polaris.eqModeEnabled";' in script.text
    assert "window.localStorage.getItem(EQ_MODE_PREFERENCE_KEY)" in script.text
    assert "window.localStorage.setItem(EQ_MODE_PREFERENCE_KEY, String(enabled))" in script.text
    assert 'window.history.replaceState({}, "", "/operator")' in script.text
    assert 'skipLink.href = "#hosted-tonight-panel"' in script.text
    assert 'document.title = "Project Polaris — Night Operations"' in script.text
    assert 'byId("eq-mode-checkbox").addEventListener("change", rememberEqModePreference)' in script.text
    assert 'byId("hosted-eq-mode-checkbox").addEventListener("change", rememberEqModePreference)' in script.text
    assert 'apiFetch("/system"' in script.text
    assert 'apiFetch("/rig-profiles"' in script.text
    assert "has_equatorial_tracking === false" in script.text
    assert "does not list EQ tracking in its official profile" in script.text
    assert 'byId("hosted-rig-profile").addEventListener("change", updateHostedEqModeAvailability)' in script.text
    assert 'rig_profile_key: byId("hosted-rig-profile").value || null' in script.text
    assert 'byId("hosted-rig-profile").value = observatory?.rig_profile_key || ""' in script.text
    assert 'apiFetch(`/dashboard?include_all_history=${historyExpanded}`' in script.text
    assert "capture.polaris_id" not in script.text
    assert "Capture quality" in script.text
    assert "Average capture quality" not in script.text
    assert "activity-preview" not in script.text
    assert "appendImageButton" in script.text
    assert "openImageViewer" in script.text
    assert "portfolio-preview-button" in script.text
    assert "displayMeasuredNumber" in script.text
    assert "friendlyFilterLabel" in script.text
    assert "renderFilterValue" in script.text
    assert "appendFilterInfoButton" in script.text
    assert "Imaging filter" in script.text
    assert "Forecast at planned start:" in script.text
    assert "Imaging aim:" in script.text
    assert "Aim guide:" in script.text
    assert "Colors and science of ${objectName}" in script.text
    assert "Displayed image quality:" in script.text
    assert "Stars detected in this image" in script.text
    assert '"Captured at"' in script.text
    assert "bortleLabel" in script.text
    assert "toggleHistory" in script.text
    assert "Show fewer captures" in script.text
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
    assert "list.hidden = visibleNotes.length === 0" in script.text
    assert 'id="capture-location-map"' in response.text
    assert 'id="candidate-site-map-key"' in response.text
    assert 'id="candidate-site-sort"' in response.text
    assert "Most ready" in response.text
    assert "Darkest sky, then closest" in response.text
    assert "renderCandidateSiteMapKey" in script.text
    assert "sortedCandidateSites" in script.text
    assert "candidateReadinessSortScore" in script.text
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
    assert "Needs research" in script.text
    assert "Partly checked" in script.text
    assert "Ready to visit" in script.text
    assert "candidateReadinessClass" in script.text
    assert "candidate-site-ready" in stylesheet.text
    assert "missingCandidateReadinessLabels" in script.text
    assert "Still check:" in script.text
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
    assert "targetMatchesSearch" in script.text
    assert "targetNeedsSpecializedScoring" in script.text
    assert "targetMatchesGroup" in script.text
    assert "Messier catalog" in response.text
    assert "Planets and solar-system objects" in response.text
    assert "planetary nebula" not in script.text
    assert "right.average_quality - left.average_quality" not in script.text
    assert "scored_capture_count" in script.text
    assert "target.scored_capture_count < target.capture_count" in script.text
    assert "planetary/lunar target" in script.text
    assert "Planetary/lunar scoring is not available yet" in script.text
    assert "average as a baseline" not in script.text
    assert "${pointsLabel(points)} / ${maxPoints} pts" in script.text
    assert "qualityComponentInfo" in script.text
    assert '"stars"' in script.text
    assert "Quality v2" in script.text
    assert "Sharpness (FWHM)" in script.text
    assert "diagnostic only" in script.text
    assert "quality-info-dialog" in response.text
    assert "Was this plan useful?" in response.text
    assert "unclear, untrustworthy, or less useful" in response.text
    assert "target choice, timing, weather, Moon, local sky" in response.text
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


def test_hosted_dashboard_includes_only_browser_safe_auth_config(monkeypatch):
    monkeypatch.setattr(
        operator_api,
        "settings",
        SimpleNamespace(
            AUTH_MODE="supabase",
            SUPABASE_URL="https://project-ref.supabase.co",
            SUPABASE_PUBLISHABLE_KEY="sb_publishable_test",
        ),
    )

    html = operator_api._dashboard_html(script_nonce="safe-test-nonce")

    assert '"mode": "supabase"' in html
    assert '"supabaseUrl": "https://project-ref.supabase.co"' in html
    assert '"supabasePublishableKey": "sb_publishable_test"' in html
    assert "supabase-js@2" in html
    assert "Private alpha access" in html
    assert "Set password and continue" in html
    assert "Forgot password?" in html
    assert "First time here? Open the private invitation link from Doug first." in html
    assert "Use password reset only after you have already chosen a Polaris" in html
    assert "The first private-alpha load may take a moment." in html
    assert "Where do you observe from?" in html
    assert "What Polaris does" in html
    assert "What to do here" in html
    assert "plain-English plan for your night" in html
    assert "Fill this in for me" in html
    assert "Approximate latitude" in html
    assert "Approximate longitude" in html
    assert "You're ready for tonight." in html
    assert "Show tonight's plan" in html
    assert "Review setup" in html
    assert "Loading your observatory" in html
    assert 'id="hosted-account-retry"' in html
    assert "Your imaging plan" in html
    assert "Opportunity score" in html
    assert 'id="hosted-opportunity-score"' in html
    assert '<small>/100</small>' not in html
    assert 'id="hosted-opportunity-drivers"' in html
    assert 'id="hosted-opportunity-glance"' not in html
    assert 'class="hosted-score-breakdown-card"' not in html
    assert "How tonight earns points" not in html
    assert "Continuous inputs scale proportionally" not in html
    assert 'id="hosted-darkness-window"' not in html
    assert 'id="hosted-moon-summary"' not in html
    assert 'id="hosted-moon-context"' not in html
    assert 'id="hosted-command-window"' in html
    assert 'id="hosted-command-window-label"' in html
    assert 'id="hosted-command-target"' in html
    assert 'id="hosted-command-target-illustration"' in html
    assert 'id="hosted-command-fallback"' in html
    assert 'id="hosted-command-fallback-illustration"' in html
    assert 'id="hosted-decision-blockers"' in html
    assert 'id="hosted-decision-recovery"' in html
    assert "Why not tonight" in html
    assert "What would need to change" in html
    assert 'id="hosted-action-summary"' not in html
    assert 'aria-label="Refresh tonight\'s plan"' in html
    assert '<span class="header-refresh-label">Refresh plan</span>' in html
    assert '<span class="header-refresh-label">Refresh</span>' in html
    assert 'id="mobile-refresh-button"' in html
    assert 'id="mobile-account-menu-button"' in html
    assert 'aria-controls="account-control"' in html
    assert "Edit home" in html
    assert 'id="hosted-target-illustration"' in html
    assert 'id="hosted-target-rig"' in html
    assert "Rig profile" in html
    assert 'id="hosted-target-fit"' in html
    assert "Target fit" in html
    assert 'id="hosted-target-rig-match"' in html
    assert "Why this rig matches" in html
    assert 'id="hosted-target-project"' in html
    assert "Project progress" in html
    assert "Remaining goal" in html
    assert "Capture quality" in html
    assert 'id="hosted-target-geometry"' in html
    assert 'id="hosted-target-altitude-chart"' in html
    assert 'id="hosted-target-peak-altitude"' in html
    assert 'id="hosted-target-peak-time"' in html
    assert 'id="hosted-weather-diagnostic"' not in html
    assert "Sign out" in html
    assert (
        html.index('id="hosted-plan-message"')
        < html.index('id="data-updated"')
        < html.index('id="hosted-feedback-panel"')
    )
    assert 'class="hosted-footer-metadata"' in html
    assert (
        html.index('class="hosted-footer-metadata"')
        < html.index('id="hosted-plan-message"')
        < html.index('id="data-updated"')
    )
    assert '<span id="data-updated">Weather pull time unavailable</span>' in html
    assert (
        html.index('id="hosted-refresh-button"')
        < html.index('id="account-email"')
        < html.index('id="sign-out-button"')
    )
    assert "secret" not in html.lower()
    assert 'nonce="safe-test-nonce"' in html

    script = (operator_api.WEB_DIRECTORY / "operator.js").read_text()
    assert 'setText("hosted-target-fit", "No target selected")' in script
    assert "loadHostedTonight" in script
    assert "showHostedAccountLoading" in script
    assert "renderHostedTonight" in script
    assert "renderOpportunityScore" in script
    assert "renderOpportunityGlance" not in script
    assert 'row.style.setProperty("--score-fill"' in script
    assert "(component.points / component.max) * 100" in script
    assert "hosted-opportunity-total-bar" not in html
    assert "hosted-opportunity-total-bar" not in script
    assert "hosted-total-score-bar" not in html
    assert "Number(opportunityScore).toFixed(1)" in script
    assert "scoreBreakdown.label || opportunityScoreLabel(opportunityScore)" in script
    assert "scoreBreakdown.guidance" in script
    assert "data.opportunity_score" in script
    assert "`Weather pulled ${displayDateTime(weather.fetched_at)}`" in script
    assert "Weather pull time unavailable" in script
    assert "latitude and longitude are rounded to 0.1°" in html
    assert "sent to 7Timer.info" in html
    assert (
        "weather.planned_temperature_at || weather.observed_at || weather.fetched_at"
        not in script
    )
    assert "opportunityComponentScore" in script
    assert "expandedOpportunityComponents" in script
    assert "Cloud cover" in script
    assert "Humidity" in script
    assert "Wind" in script
    assert "renderDecisionSupport" in script
    assert "opportunityScoreLabel" in script
    assert "Challenging" in script
    assert "Wait for better conditions" in script
    assert "hosted-score-factor-icon" in script
    assert "opportunityFactorIconPaths" in script
    assert "appendOpportunityFactorIcon" in script
    assert "hosted-score-factor-info" in script
    assert "More about ${component.label}" in script
    assert "component.key" in script
    assert "hosted-score-factor-description" in script
    assert 'component.source !== "Proportional"' in script
    assert 'renderFilterValue("hosted-target-filter", settings.filter_name, false)' in script
    assert '? "EQ"' in script
    assert ': "Alt-Az"' in script
    assert "displayedDecisionMessage" in script
    assert "softenAdvisoryNote" in script
    assert "Best move tonight" not in script
    assert "renderHostedSchedule" in script
    assert "resetHostedPlanDetails" in script
    assert 'setText("hosted-target-exposure", "—")' in script
    assert 'setText("hosted-target-rig", "—")' in script
    assert 'setText("hosted-target-fit", "—")' in script
    assert "targetRigMatchLabel(target)" in script
    assert "renderTargetGeometry(target)" in script
    assert "renderTargetGeometry(null)" in script
    assert "renderTargetProjectContext(target)" in script
    assert "Math.round((currentHours / goalHours) * 100)" in script
    assert "displayHours(remainingHours)" in script
    assert "Goal reached" in script
    assert "No scored captures yet" in script
    assert "knownTargetMetadata(target.constellation)" in script
    assert "knownTargetMetadata(target.target_type)" in script
    assert "target.target_geometry" in script
    assert "Altitude path unavailable for this target." in script
    assert 'role: "img"' in script
    assert "targetIllustrationKind" in script
    assert "mappedTargetIllustrationAsset" in script
    assert "SAFE_TARGET_ART_URL" in script
    assert "/operator-assets/target-art/fallbacks" in script
    assert "target?.artwork?.asset_url" in script
    assert "buildTargetIllustrationSvg" in script
    assert 'document.createElement("img")' in script
    assert 'image.dataset.visualTreatment = target?.artwork?.match_kind || "category"' in script
    assert "genericTargetIllustrationAsset" in script
    assert "parseCachedTargetIllustration" in script
    assert 'svg.querySelector("script, foreignObject, image, use, a, text, title, desc")' in script
    assert "artwork_svg" in script
    assert "renderReferenceAttribution" not in script
    assert "NASA source" not in script
    assert "Polaris artwork" not in script
    assert "TARGET_REFERENCE_IMAGE_FALLBACKS" not in script
    assert 'id="hosted-reference-image"' not in html
    assert 'id="target-reference-image"' not in html
    assert "informed by cached NASA reference metadata" not in script
    assert 'return "galaxy"' in script
    assert 'return "nebula"' in script
    assert 'return "cluster"' in script
    assert 'return "deep-sky"' in script
    assert 'renderTargetIllustration("hosted-command-target-illustration"' in script
    assert 'renderTargetIllustration("hosted-command-fallback-illustration"' in script
    assert 'renderTargetIllustration("hosted-target-illustration"' in script
    assert "if (!target)" in script
    assert "container.replaceChildren();" in script
    assert "container.hidden = true;" in script
    assert 'classList.toggle("has-target-illustration", Boolean(target))' in script
    assert "if (targetVisuals) targetVisuals.hidden = !target;" in script
    css = (operator_api.WEB_DIRECTORY / "operator.css").read_text()
    m31_asset = (
        operator_api.WEB_DIRECTORY
        / "target-art"
        / "library"
        / "assets"
        / "m31-andromeda.svg"
    ).read_text()
    assert '<rect width="400" height="300" fill="#102a2c"/>' not in m31_asset
    assert 'id="m31-andromeda-ambient-edge-fade"' in m31_asset
    assert 'mask="url(#m31-andromeda-ambient-vignette-mask)"' in m31_asset
    assert "M87.9 132.1 A124 42 0 0 1 316.5 135.6" in m31_asset
    assert "M66.3 128.5 A137 98" not in m31_asset
    assert "M282.5 219.6 A128 91" not in m31_asset
    assert "M113.9 208 A119 84" not in m31_asset
    assert "<title" in m31_asset
    assert "<desc" in m31_asset
    assert "m31-andromeda.svg" in {asset.name for asset in operator_api.ASSET_FILES}
    assert ".hosted-footer-metadata" in css
    assert ".hosted-score-component::before" in css
    assert "font-size: clamp(16px, 1.45vw, 22px)" in css
    assert "flex: 0 0 clamp(42px, 3.7vw, 54px)" in css
    assert ".hosted-command-target-illustration img" in css
    assert ".hosted-target-illustration img" in css
    assert ".hosted-command-target-card.has-target-illustration" in css
    assert ".hosted-command-fallback-card.has-target-illustration" in css
    assert ".hosted-target-heading:not(.has-target-illustration)" in css
    assert ".hosted-target-geometry" in css
    assert ".hosted-target-project" in css
    assert ".target-altitude-line" in css
    assert ".target-altitude-peak" in css
    assert ".hosted-reference-image" not in css
    assert ".target-reference-image" not in css
    assert "setMobileHeaderMenu" in script
    assert "setHostedRefreshState" in script
    assert 'byId("mobile-refresh-button").addEventListener("click", loadHostedTonight)' in script
    assert "rigProfileLabel(data.observatory)" in script
    assert "targetFitLabel(target)" in script
    assert "profile?.label || observatory.telescope_model || observatory.rig_profile_key" in script
    assert 'setText("hosted-weather-summary", "—")' not in script
    assert 'notes.replaceChildren()' in script
    assert "Building tonight's schedule…" in script
    assert "displayedTargetSettings" in script
    assert "showHostedReadyHandoff" in script
    assert "retryHostedAccountLoad" in script
    assert 'byId("hosted-account-retry").addEventListener("click", retryHostedAccountLoad)' in script
    assert "This private invitation lets you create your Polaris password for the first time." in script
    assert "If this is your first visit, use Doug's original invitation link instead." in script
    assert "const isFirstObservingHome = !hostedObservatory" in script
    assert 'byId("hosted-ready-continue").addEventListener("click", loadHostedTonight)' in script
    assert "firstScheduledBlock.recommended_sub_exposure_seconds" in script
    assert "renderSkyQuality" not in script
    assert "hosted-weather-diagnostic" not in script
    assert "hostedPlanFailureMessage" in script
    assert "send Doug request ID" in script
    assert "This is a planning refresh problem, not a telescope-control action." in script
    assert "Tonight's schedule could not be refreshed yet. Try again in a moment." in script
    assert "Conditions are usable, but one or more factors need attention" in script
    assert 'startsWith("use caution:")' in script
    assert "<p class=\"eyebrow\">Sky quality</p>" in html
    assert "No sky-quality deductions" in script
    assert "equatorial_mode_enabled=${eqEnabled}" in script
    assert '`${value}T12:00:00`' in script
    assert "Personalized nightly recommendations are the next hosted Polaris milestone." not in script


def test_command_cards_separate_empty_best_target_from_real_fallback_art():
    html = (operator_api.WEB_DIRECTORY / "operator.html").read_text()
    script = (operator_api.WEB_DIRECTORY / "operator.js").read_text()
    css = (operator_api.WEB_DIRECTORY / "operator.css").read_text()

    # Each command card owns exactly one mount; renderTargetIllustration is
    # responsible for leaving a null mount empty or adding one approved local
    # SVG image for a real target.
    assert html.count('id="hosted-command-target-illustration"') == 1
    assert html.count('id="hosted-command-fallback-illustration"') == 1
    assert (
        '"hosted-command-target-illustration",\n'
        "      data.recommended_target || null,"
    ) in script
    assert (
        '"hosted-command-fallback-illustration",\n'
        "    fallbackTarget,"
    ) in script
    assert "if (!target) {\n    container.replaceChildren();\n    container.hidden = true;" in script
    assert "cachedIllustration || buildTargetIllustrationSvg(target, compact)" in script
    assert "const approvedAsset = mappedTargetIllustrationAsset(target);" in script
    assert "target?.artwork?.match_kind" in script
    assert (
        ".hosted-command-fallback-card.has-target-illustration"
        " {\n  padding-right: 78px !important;"
    ) in css

    assert 'id="hosted-reference-image"' not in html
    assert 'id="target-reference-image"' not in html
    assert "renderReferenceAttribution" not in script


def test_dew_guidance_is_part_of_recommended_setup():
    html = (operator_api.WEB_DIRECTORY / "operator.html").read_text()
    script = (operator_api.WEB_DIRECTORY / "operator.js").read_text()

    setup_start = html.index('id="hosted-setup-card"')
    caution_start = html.index('class="hosted-setup-cautions"')
    notes_start = html.index('id="hosted-plan-notes"')
    setup_end = html.index("</div>", notes_start)
    assert setup_start < caution_start < notes_start < setup_end
    assert 'class="hosted-cautions-card"' not in html
    assert "data.dew_risk" in script
    assert "dewAdvisoryNotes" in script
    assert "dewRisk.label" in script
    assert "dewRisk.action" in script
    assert "Dew guidance:" not in script
    assert "dewRisk.summary" not in script
    assert "? [`Dew: ${dewRisk.label}. ${dewRisk.action}`]" in script
    assert "notes.hidden = visibleNotes.length === 0" in script
    assert "renderNotes(data.schedule.notes, data.dew_risk)" in script


def test_conditions_trend_is_a_small_cue_beside_the_imaging_window():
    html = (operator_api.WEB_DIRECTORY / "operator.html").read_text()
    script = (operator_api.WEB_DIRECTORY / "operator.js").read_text()
    css = (operator_api.WEB_DIRECTORY / "operator.css").read_text()

    hosted_window = html.index('id="hosted-command-window"')
    hosted_trend = html.index('id="hosted-window-trend"')
    hosted_target = html.index('class="hosted-command-target-card"')
    assert hosted_window < hosted_trend < hosted_target
    assert 'class="hosted-command-weather"' not in html
    assert 'id="target-window-trend"' in html
    assert 'aria-live="polite"' in html
    assert "renderConditionsTrend" in script
    assert 'renderConditionsTrend("hosted-window-trend", data.conditions_trend)' in script
    assert 'renderConditionsTrend("target-window-trend", data.conditions_trend)' in script
    assert ".conditions-trend" in css
    assert ".conditions-trend.trend-improving" in css
    assert ".conditions-trend.trend-worsening" in css


def test_condition_alerts_are_opt_in_conservative_and_page_open_only():
    html = (operator_api.WEB_DIRECTORY / "operator.html").read_text()
    script = (operator_api.WEB_DIRECTORY / "operator.js").read_text()
    css = (operator_api.WEB_DIRECTORY / "operator.css").read_text()

    heading = html.index('class="hosted-tonight-heading"')
    alerts = html.index('id="hosted-condition-alerts"')
    recommendation = html.index('id="hosted-recommendation"')
    assert heading < alerts < recommendation
    assert 'id="hosted-condition-alerts-button"' in html
    assert 'id="hosted-condition-alerts-status" role="status" aria-live="polite"' in html
    assert "Notify me if tonight improves" in html
    assert "Alerts work only while this page remains open." in html

    assert 'const CONDITION_ALERT_PREFERENCE_KEY = "polaris.conditionAlertsEnabled";' in script
    assert 'const CONDITION_ALERT_HISTORY_KEY = "polaris.conditionAlertHistory";' in script
    assert "const CONDITION_ALERT_POLL_INTERVAL_MS = 15 * 60 * 1000" in script
    assert "const CONDITION_ALERT_COOLDOWN_MS = 2 * 60 * 60 * 1000" in script
    assert "window.Notification.requestPermission()" in script
    assert 'byId("hosted-condition-alerts-button").addEventListener("click", toggleConditionAlerts)' in script
    assert 'window.localStorage.setItem(CONDITION_ALERT_PREFERENCE_KEY, String(enabled))' in script
    assert 'window.localStorage.setItem(CONDITION_ALERT_HISTORY_KEY, JSON.stringify(history))' in script
    assert 'button.textContent = hostedConditionAlertsEnabled\n    ? "Turn off alerts"' in script
    assert 'permission === "denied"' in script
    assert "Browser alerts are not supported here." in script
    assert "Alerts are blocked in this browser's site settings." in script

    # Monitoring reads a fresh plan without POSTing a recommendation run.
    check_start = script.index("const checkConditionAlerts = async () =>")
    check_end = script.index("const startConditionAlertMonitoring", check_start)
    check_source = script[check_start:check_end]
    assert '`/tonight?equatorial_mode_enabled=${eqEnabled}`' in check_source
    assert '{ cache: "no-store" }' in check_source
    assert 'method: "POST"' not in check_source
    assert "if (!hostedConditionAlertsEnabled || !hostedSession || !hostedObservatory) return" in check_source

    # Trigger boundaries require a real target/window and a meaningful change.
    trigger_start = script.index("const conditionAlertTrigger = (previous, current) =>")
    trigger_end = script.index("const conditionAlertSignature", trigger_start)
    trigger_source = script[trigger_start:trigger_end]
    assert "!current.hasUsablePlan" in trigger_source
    assert 'previous.decision === "Do Not Image"' in trigger_source
    assert '["Use Caution", "Proceed"].includes(current.decision)' in trigger_source
    assert "current.score >= 55" in trigger_source
    assert 'previous.decision === "Use Caution"' in trigger_source
    assert 'current.decision === "Proceed"' in trigger_source
    assert "current.score >= 65" in trigger_source
    assert "current.score - previous.score >= 15" in trigger_source

    assert "conditionAlertWasRecentlySent(current)" in script
    assert "sameSignature || withinCooldown" in script
    assert 'new window.Notification("Polaris: tonight improved"' in script
    assert 'tag: `polaris-conditions-${state.date}`' in script
    assert "stopConditionAlertMonitoring()" in script
    assert ".hosted-condition-alerts" in css
    assert ".hosted-condition-alerts.has-alert" in css
    assert ".hosted-condition-alerts.is-blocked" in css
    assert ".hosted-condition-alerts .account-button" in css


def test_session_checklist_stays_inside_the_existing_command_card():
    html = (operator_api.WEB_DIRECTORY / "operator.html").read_text()
    script = (operator_api.WEB_DIRECTORY / "operator.js").read_text()
    css = (operator_api.WEB_DIRECTORY / "operator.css").read_text()

    command_start = html.index('class="hosted-command-board"')
    checklist_start = html.index('id="hosted-session-plan"')
    target_start = html.index('id="hosted-target-card"')
    assert command_start < checklist_start < target_start
    assert 'aria-labelledby="hosted-session-plan-title"' in html
    assert 'aria-live="polite"' in html
    assert 'id="hosted-session-steps"' in html
    assert 'id="hosted-session-actions"' not in html
    assert 'id="hosted-session-timeline-link"' in html
    assert 'aria-controls="hosted-schedule-panel"' in html
    assert "A session is possible, but recheck live conditions before starting." not in html
    assert 'id="hosted-session-plan-summary"' not in html
    assert 'const renderSessionChecklist = (checklist, decision = "Conditions Unknown") =>' in script
    assert "(checklist?.steps || []).slice(0, 3)" in script
    assert "(checklist?.actions || []).slice(0, 2)" not in script
    assert "renderSessionChecklist(data.session_checklist, decision)" in script
    assert 'renderSessionChecklist(null, "Conditions Unknown")' in script
    assert 'step.key === "reassess"' in script
    assert 'hardStop ? "Next action" : "Session plan"' in script
    assert 'step.instruction || "Timing unavailable."' not in script
    assert "const openHostedSchedule = () =>" in script
    assert 'byId("hosted-session-timeline-link").addEventListener("click", openHostedSchedule)' in script
    assert 'summary.focus({ preventScroll: true })' in script
    assert ".hosted-session-plan" in css
    assert ".hosted-session-timeline-link" in css
    assert ".hosted-session-steps" in css
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in css


def test_advisory_timeline_collapses_only_when_no_blocks_exist():
    html = (operator_api.WEB_DIRECTORY / "operator.html").read_text()
    script = (operator_api.WEB_DIRECTORY / "operator.js").read_text()
    css = (operator_api.WEB_DIRECTORY / "operator.css").read_text()

    assert '<details\n          class="panel hosted-schedule-panel"' in html
    assert 'id="hosted-schedule-panel"' in html
    assert 'id="hosted-schedule-summary"' in html
    assert 'id="hosted-schedule-count"' in html
    assert 'id="hosted-schedule-list"' in html
    assert 'class="eyebrow hosted-schedule-label"' in html
    assert 'const timeline = byId("hosted-schedule-panel")' in script
    assert "timeline.open = blocks.length > 0" in script
    assert 'byId("hosted-schedule-panel").open = true' in script
    assert ".hosted-schedule-panel:not([open]) > .hosted-schedule-summary" in css
    assert ".hosted-schedule-panel[open] .hosted-schedule-toggle::before" in css
    assert '.hosted-schedule-label::before' in css
    assert 'content: "05";' in css
    assert 'font-size: 24px;' in css
    assert 'appendTextElement(body, "p", "", block.reason)' not in script


def test_target_art_preview_is_isolated_and_uses_transparent_library_assets():
    client = TestClient(app)
    html = (operator_api.WEB_DIRECTORY / "operator.html").read_text()
    script = (operator_api.WEB_DIRECTORY / "operator.js").read_text()
    css = (operator_api.WEB_DIRECTORY / "operator.css").read_text()
    preview_assets = {
        "double-cluster.svg": "double-cluster-ambient-vignette-mask",
        "orion-nebula-m42.svg": "orion-nebula-m42-ambient-vignette-mask",
        "ring-nebula-m57.svg": "ring-nebula-m57-ambient-vignette-mask",
        "m78-reflection-nebula.svg": "m78-reflection-nebula-ambient-vignette-mask",
    }

    assert 'id="target-art-preview"' in html
    assert html.count('class="hosted-target target-art-preview-card"') == 6
    assert "Compare six target-card treatments" in html
    assert "Artwork preview only." in html
    assert "not tonight's recommendations" in html
    assert 'href="/operator">Return to tonight\'s plan</a>' in html
    assert "Double Cluster" in html
    assert "Andromeda Galaxy" in html
    assert "Orion Nebula" in html
    assert "Ring Nebula" in html
    assert "Casper the Friendly Ghost Nebula" in html
    assert "Safe generic fallback" in html
    assert "never substitutes a different named object" in html
    assert "Night-path geometry is intentionally absent here" in html
    assert "NASA source" not in html
    assert "Polaris artwork" not in html

    assert (
        'const targetArtPreviewMode = invitationQuery.get("target-art-preview") === "1";'
        in script
    )
    assert "const showTargetArtPreview = () =>" in script
    assert "const showStandaloneTargetArtPreview = () =>" in script
    assert script.count(
        "if (targetArtPreviewMode) {\n    showTargetArtPreview();\n    return;\n  }"
    ) == 1
    assert (
        "if (targetArtPreviewMode) {\n"
        "    showStandaloneTargetArtPreview();\n"
        "    return;\n"
        "  }\n"
        "  if (usesHostedAuth)"
    ) in script
    assert "body.target-art-preview-mode .hosted-footer-metadata" in css
    assert ".target-art-preview-grid" in css
    assert ".target-art-preview-geometry-note" in css
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in css

    bundled_asset_names = {asset.name for asset in operator_api.ASSET_FILES}
    for filename, mask_id in preview_assets.items():
        assert filename in bundled_asset_names
        asset_path = (
            operator_api.WEB_DIRECTORY
            / "target-art"
            / "library"
            / "assets"
            / filename
        )
        markup = asset_path.read_text()
        assert mask_id in markup
        assert '<rect width="400" height="300" fill="#102a2c"/>' not in markup
        assert "<title" in markup
        assert "<desc" in markup
        response = client.get(
            f"/operator-assets/target-art/library/assets/{filename}"
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/svg+xml")


def test_operator_dashboard_sets_restrictive_content_policy():
    client = TestClient(app)
    response = client.get("/operator")

    assert response.status_code == 200
    policy = response.headers["content-security-policy"]
    assert "default-src 'self'" in policy
    assert "object-src 'none'" in policy
    assert "frame-ancestors 'none'" in policy
    assert "https://cdn.esahubble.org" not in policy
    assert "https://cdn.jsdelivr.net" not in policy
    nonce = response.text.split('nonce="', 1)[1].split('"', 1)[0]
    assert f"'nonce-{nonce}'" in policy


def test_hosted_weather_summary_shows_honest_forecast_history_state():
    html = (operator_api.WEB_DIRECTORY / "operator.html").read_text()
    script = (operator_api.WEB_DIRECTORY / "operator.js").read_text()
    css = (operator_api.WEB_DIRECTORY / "operator.css").read_text()

    assert 'id="hosted-forecast-confidence"' not in html
    assert 'id="forecast-accuracy-history-title"' in html
    assert 'href="#forecast-accuracy-history"' in html
    assert 'id="forecast-accuracy-link-count"' in html
    assert 'id="forecast-accuracy-recent-list"' in html
    assert "Recent verified checks" in html
    assert 'id="forecast-accuracy-chart"' in html
    assert 'id="forecast-accuracy-metrics" hidden' in html
    assert 'role="status"' in html
    assert "Forecast confidence is still building." not in html
    assert "data.forecast_accuracy || {}" in script
    assert "renderForecastAccuracyHistory" in script
    assert "average_cloud_error_percent" in script
    assert "forecast_cloud_cover_percent" in script
    assert "matched_samples" in script
    assert "minimum_samples" in script
    assert "matchedSamples < minimumSamples" in script
    assert "verified comparison" in script
    assert 'formatForecastMetric(check.cloud_error_percent, "-point miss")' in script
    assert ".hosted-forecast-confidence" not in css
    assert ".hosted-forecast-history-link" in css
    assert ".forecast-accuracy-recent" in css
    assert ".forecast-accuracy-history" in css
    assert ".forecast-accuracy-bar.forecast::before" in css


def test_hard_stop_mode_is_decisive_and_keeps_secondary_planning_optional():
    html = (operator_api.WEB_DIRECTORY / "operator.html").read_text()
    script = (operator_api.WEB_DIRECTORY / "operator.js").read_text()
    css = (operator_api.WEB_DIRECTORY / "operator.css").read_text()

    assert "Tonight's recommendation" in html
    assert 'id="hosted-secondary-toggle"' in html
    assert "Show planning details if conditions improve" in html
    assert 'id="hosted-score-breakdown-card"' not in html
    assert 'id="hosted-target-card"' in html
    assert 'id="hosted-setup-card"' in html
    assert 'id="hosted-cautions-card"' not in html
    assert 'hardStopScore ? "STOP"' in script
    assert 'hardStopScore ? "100%"' in script
    assert 'source: parts.cloud >= 100 ? "Not scored after cloud stop"' in script
    assert "const setHardStopDetailsVisibility" in script
    assert 'classList.toggle("has-secondary-toggle", hardStop)' in script
    assert 'support.hidden = decision !== "Do Not Image"' in script
    assert "return blockers.slice(0, 1);" in script
    assert '"hosted-target-card",\n  "hosted-setup-card",' in script
    assert 'timeline.hidden = schedule?.decision === "Do Not Image"' in script
    assert 'byId("hosted-secondary-toggle").addEventListener("click", toggleHardStopDetails)' in script
    assert ".hosted-secondary-toggle" in css
    assert ".hosted-recommendation.has-secondary-toggle" in css
    assert ".hosted-opportunity-reading.is-hard-stop #hosted-opportunity-score" in css
    assert ".hosted-recommendation.status-do-not-image .hosted-command-target-card" in css


def test_numbered_card_headers_share_the_same_card_origin():
    css = (operator_api.WEB_DIRECTORY / "operator.css").read_text()

    header_rule_start = css.index(".hosted-opportunity-score > .eyebrow,")
    header_rule_end = css.index(".hosted-opportunity-score > .eyebrow::before", header_rule_start)
    header_rule = css[header_rule_start:header_rule_end]
    assert "align-items: center;" in header_rule
    assert "margin: 0;" in header_rule
    assert ".hosted-decision {\n    padding: 16px 18px;" not in css
    assert '.hosted-target-heading .eyebrow::before { content: "03"; }' in css
    assert '.hosted-setup-card > .eyebrow::before { content: "04"; }' in css
    assert '.hosted-schedule-label::before' in css


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
