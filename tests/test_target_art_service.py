from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.data.target_art_catalog import NASA_TARGET_ART_CATALOG
from app.services.target_art_service import MAPPED_TARGET_ART_ASSETS
from app.services.target_art_service import _generate_artwork_svg
from app.services.target_art_service import _mapped_artwork_svg
from app.services.target_art_service import get_cached_target_reference
from app.services.target_art_service import refresh_target_art_cache


NOW = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)


def nasa_item(
    *,
    nasa_id="GSFC_20171208_Archive_e001861",
    title="Hubble view of the Andromeda Galaxy",
    description="The Andromeda Galaxy, also known as M31.",
    copyright=None,
):
    data = {
        "nasa_id": nasa_id,
        "title": title,
        "description": description,
        "media_type": "image",
        "center": "NASA Goddard",
        "secondary_creator": "Hubble Heritage Team",
        "keywords": ["Hubble", "Andromeda", "Galaxy"],
    }
    if copyright is not None:
        data["copyright"] = copyright
    return {
        "data": [data],
        "links": [
            {
                "href": "https://images-assets.nasa.gov/image/example/example~thumb.jpg",
                "rel": "preview",
                "render": "image",
            }
        ],
    }


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.request = httpx.Request("GET", "https://images-api.nasa.gov/search")

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "NASA request failed",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params):
        self.calls.append((url, params))
        if self.responses:
            return self.responses.pop(0)
        return FakeResponse({"collection": {"items": []}})


def search_payload(*items):
    return {"collection": {"items": list(items)}}


def responses_for_mapped_targets(m31_response):
    # The catalog currently resolves six targets in insertion order; only M31
    # needs a successful fixture for these focused assertions.
    return [
        FakeResponse(search_payload()),
        FakeResponse(search_payload()),
        FakeResponse(search_payload()),
        m31_response,
        FakeResponse(search_payload()),
        FakeResponse(search_payload()),
    ]


def test_refresh_caches_nasa_metadata_and_generated_svg(tmp_path):
    client = FakeClient(
        responses_for_mapped_targets(FakeResponse(search_payload(nasa_item())))
    )

    statuses = refresh_target_art_cache(
        client=client,
        cache_dir=tmp_path,
        now=NOW,
    )
    reference = get_cached_target_reference(
        "M31",
        cache_dir=tmp_path,
        now=NOW,
    )

    assert statuses["M31"] == "refreshed"
    assert reference["cache_status"] == "fresh"
    assert reference["nasa_id"] == "GSFC_20171208_Archive_e001861"
    assert reference["source_label"] == "NASA Image and Video Library"
    assert reference["source_url"].startswith("https://images.nasa.gov/details/")
    assert reference["credit"] == "NASA Goddard · Hubble Heritage Team"
    assert reference["artwork_profile"] == "inclined_spiral"
    assert 'preserveAspectRatio="xMidYMid meet"' in reference["artwork_svg"]
    assert 'viewBox="0 0 400 300"' in reference["artwork_svg"]
    assert 'data-visual-treatment="m31-library-v2"' in reference["artwork_svg"]
    assert 'data-morphology="m31-andromeda-current"' in reference["artwork_svg"]
    assert "M87.9 132.1 A124 42 0 0 1 316.5 135.6" in reference["artwork_svg"]
    assert "<title>" not in reference["artwork_svg"]
    assert "<desc" not in reference["artwork_svg"]
    assert "#d49a3a" in reference["artwork_svg"]
    assert "#e48191" not in reference["artwork_svg"]
    assert "#6e9fd0" not in reference["artwork_svg"]
    assert "M66.3 128.5 A137 98" not in reference["artwork_svg"]
    assert "<image" not in reference["artwork_svg"]
    assert client.calls[3][1] == {
        "q": "M31 Andromeda Galaxy",
        "media_type": "image",
        "page_size": 25,
    }


def test_refresh_rejects_copyrighted_candidates_and_uses_safe_match(tmp_path):
    copyrighted = nasa_item(
        nasa_id="third-party",
        title="Andromeda Galaxy by a third party",
        copyright="Example Photographer",
    )
    safe = nasa_item(nasa_id="safe-nasa-asset")
    client = FakeClient(
        responses_for_mapped_targets(
            FakeResponse(search_payload(copyrighted, safe))
        )
    )

    refresh_target_art_cache(client=client, cache_dir=tmp_path, now=NOW)

    reference = get_cached_target_reference("M31", cache_dir=tmp_path, now=NOW)
    assert reference["nasa_id"] == "safe-nasa-asset"


def test_ambiguous_search_result_does_not_create_a_cache_entry(tmp_path):
    unrelated = nasa_item(
        title="A distant spiral galaxy",
        description="A galaxy with no catalog match.",
    )
    unrelated["data"][0]["keywords"] = ["Hubble", "Galaxy"]
    client = FakeClient(
        responses_for_mapped_targets(FakeResponse(search_payload(unrelated)))
    )

    statuses = refresh_target_art_cache(
        client=client,
        cache_dir=tmp_path,
        now=NOW,
    )

    assert statuses["M31"] == "unavailable"
    assert get_cached_target_reference("M31", cache_dir=tmp_path, now=NOW) is None


def test_rate_limit_preserves_expired_cache_as_stale_fallback(tmp_path):
    initial = FakeClient(
        responses_for_mapped_targets(FakeResponse(search_payload(nasa_item())))
    )
    refresh_target_art_cache(client=initial, cache_dir=tmp_path, now=NOW)

    rate_limited = FakeClient(
        responses_for_mapped_targets(FakeResponse({}, status_code=429))
    )
    later = NOW + timedelta(days=31)
    statuses = refresh_target_art_cache(
        client=rate_limited,
        cache_dir=tmp_path,
        now=later,
        force=True,
    )
    reference = get_cached_target_reference(
        "M31",
        cache_dir=tmp_path,
        now=later,
    )

    assert statuses["M31"] == "stale"
    assert reference["cache_status"] == "stale"
    assert reference["nasa_id"] == "GSFC_20171208_Archive_e001861"
    assert len(rate_limited.calls) == 4


def test_m51_uses_curated_official_source_and_credit(tmp_path):
    whirlpool = nasa_item(
        nasa_id="GSFC_20171208_Archive_e001925",
        title="The Two-faced Whirlpool Galaxy",
        description="A Hubble view of the Whirlpool Galaxy M51.",
    )
    whirlpool["data"][0]["keywords"] = ["Hubble", "Whirlpool", "Galaxy"]
    responses = [
        FakeResponse(search_payload()),
        FakeResponse(search_payload()),
        FakeResponse(search_payload()),
        FakeResponse(search_payload()),
        FakeResponse(search_payload(whirlpool)),
        FakeResponse(search_payload()),
    ]

    refresh_target_art_cache(
        client=FakeClient(responses),
        cache_dir=tmp_path,
        now=NOW,
    )
    reference = get_cached_target_reference("M51", cache_dir=tmp_path, now=NOW)

    assert reference["source_url"] == (
        "https://science.nasa.gov/asset/hubble/"
        "hubble-acs-visible-image-of-m51/"
    )
    assert reference["source_label"] == "NASA Science · Hubble"
    assert reference["credit"] == (
        "NASA, ESA, S. Beckwith (STScI), and the Hubble Heritage Team "
        "(STScI/AURA)"
    )
    assert 'data-visual-treatment="canonical-m31-v3"' in reference["artwork_svg"]
    assert "#d5a54d" in reference["artwork_svg"]
    assert "#e48191" not in reference["artwork_svg"]
    assert "#6e9fd0" not in reference["artwork_svg"]


def test_unsupported_target_never_uses_a_cache_entry(tmp_path):
    assert get_cached_target_reference(
        "UNMAPPED",
        cache_dir=tmp_path,
        now=NOW,
    ) is None


def test_m31_uses_current_approved_library_asset_without_removed_wrapper():
    svg = _generate_artwork_svg("M31", NASA_TARGET_ART_CATALOG["M31"])

    assert 'data-visual-treatment="m31-library-v2"' in svg
    assert 'data-morphology="m31-andromeda-current"' in svg
    assert 'viewBox="0 0 400 300"' in svg
    assert '<rect width="400" height="300" fill="#102a2c"/>' in svg
    assert "M87.9 132.1 A124 42 0 0 1 316.5 135.6" in svg
    assert "M91.7 139.1 A111 38 0 0 1 307.8 144.3" in svg
    assert '<ellipse cx="183" cy="146" rx="31" ry="18"' in svg
    assert "M28 75C63 41 159 40 212 68" not in svg
    assert "M66.3 128.5 A137 98" not in svg
    assert "M282.5 219.6 A128 91" not in svg
    assert "M113.9 208 A119 84" not in svg
    assert "<title>" not in svg
    assert "<desc" not in svg
    assert MAPPED_TARGET_ART_ASSETS["M31"]["source_catalog_sha256"] == (
        "2f1d3e608eef02139168a2555041c306"
        "b11f19d744b09a005a3a4365fe444e7c"
    )


def test_mapped_artwork_rejects_visible_labels(monkeypatch, tmp_path):
    unsafe_asset = tmp_path / "unsafe.svg"
    unsafe_asset.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><text>Source</text></svg>',
        encoding="utf-8",
    )
    monkeypatch.setitem(
        MAPPED_TARGET_ART_ASSETS,
        "M31",
        {"path": unsafe_asset, "source_catalog_sha256": "fixture"},
    )

    with pytest.raises(ValueError, match="disallowed text"):
        _mapped_artwork_svg("M31")


def test_non_m31_catalog_targets_keep_existing_visual_grammar():
    canonical_paths = (
        "M28 75C63 41 159 40 212 68",
        "M35 56C75 86 160 92 205 61",
        "M45 87C87 65 162 65 196 78",
    )

    for target_name, catalog_entry in NASA_TARGET_ART_CATALOG.items():
        if target_name == "M31":
            continue
        svg = _generate_artwork_svg(target_name, catalog_entry)

        assert 'data-visual-treatment="canonical-m31-v3"' in svg
        assert "<title>" not in svg
        assert 'transform="rotate(-17 120 70)"' in svg
        assert 'ellipse cx="120" cy="70" rx="92" ry="36"' in svg
        for path in canonical_paths:
            assert path in svg

        assert 'data-morphology="m31-andromeda-current"' not in svg
        assert "M87.9 132.1 A124 42 0 0 1 316.5 135.6" not in svg

        # These markers belonged to the former target-specific treatments.
        assert "translate(78 82)" not in svg
        assert "M101 48C121 20" not in svg
        assert "M55 118C63 50" not in svg
