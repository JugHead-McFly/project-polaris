from datetime import datetime, timedelta, timezone

import httpx

from app.data.target_art_catalog import NASA_TARGET_ART_CATALOG
from app.services.target_art_service import _generate_artwork_svg
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
    assert 'data-reference="nasa"' in reference["artwork_svg"]
    assert 'preserveAspectRatio="xMidYMid meet"' in reference["artwork_svg"]
    assert 'data-visual-treatment="canonical-m31-v3"' in reference["artwork_svg"]
    assert "<title>" not in reference["artwork_svg"]
    assert "#d5a54d" in reference["artwork_svg"]
    assert "#e48191" not in reference["artwork_svg"]
    assert "#6e9fd0" not in reference["artwork_svg"]
    assert 'stroke-dasharray="' in reference["artwork_svg"]
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


def test_every_catalog_target_uses_the_canonical_m31_visual_grammar():
    canonical_paths = (
        "M28 75C63 41 159 40 212 68",
        "M35 56C75 86 160 92 205 61",
        "M45 87C87 65 162 65 196 78",
    )

    for target_name, catalog_entry in NASA_TARGET_ART_CATALOG.items():
        svg = _generate_artwork_svg(target_name, catalog_entry)

        assert 'data-visual-treatment="canonical-m31-v3"' in svg
        assert "<title>" not in svg
        assert 'transform="rotate(-17 120 70)"' in svg
        assert 'ellipse cx="120" cy="70" rx="92" ry="36"' in svg
        for path in canonical_paths:
            assert path in svg

        # These markers belonged to the former target-specific treatments.
        assert "translate(78 82)" not in svg
        assert "M101 48C121 20" not in svg
        assert "M55 118C63 50" not in svg
