from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.target_art_library_service import (
    _catalog,
    resolve_target_artwork,
)
from scripts.build_target_art_library import _validate_svg


def test_catalog_contains_exactly_one_thousand_local_assets():
    catalog = _catalog()
    assert len(catalog["by_slug"]) == 1000
    for entry in catalog["by_slug"].values():
        assert entry["asset"].startswith("assets/")
        assert ".." not in entry["asset"]


def test_real_target_and_m31_use_exact_library_art():
    m57 = resolve_target_artwork("M57", common_name="Ring Nebula", target_type="Nebula")
    m31 = resolve_target_artwork("M31", common_name="Andromeda Galaxy", target_type="Galaxy")

    assert m57["slug"] == "ring-nebula-m57"
    assert m57["match_kind"] == "exact"
    assert m57["asset_url"].startswith(
        "/operator-assets/target-art/library/assets/ring-nebula-m57.svg?v="
    )
    assert m31["slug"] == "m31-andromeda"
    assert "/library/assets/m31-andromeda.svg" in m31["asset_url"]


def test_verified_aliases_resolve_without_fuzzy_guessing():
    expected = "north-america-nebula"
    for alias in ("C 20", "Caldwell 20", "NGC 7000", "North America Nebula"):
        assert resolve_target_artwork(alias)["slug"] == expected

    # M16 is ambiguous in the source catalog, so the verified Polaris identity
    # must choose the Eagle Nebula instead of the cluster-only rendering.
    assert resolve_target_artwork("M16")["slug"] == "eagle-nebula-m16"


def test_every_current_polaris_target_has_a_verified_exact_asset():
    expected = {
        "C 20": "north-america-nebula",
        "M8": "lagoon-nebula-m8",
        "M11": "wild-duck-cluster-m11",
        "M13": "globular-m13",
        "M16": "eagle-nebula-m16",
        "M17": "omega-nebula-m17",
        "M20": "trifid-nebula-m20",
        "M22": "globular-m22",
        "M27": "dumbbell-nebula-m27",
        "M31": "m31-andromeda",
        "M51": "m51-whirlpool",
        "M57": "ring-nebula-m57",
        "M63": "sunflower-galaxy-m63",
        "M64": "black-eye-galaxy-m64",
        "M97": "owl-nebula-m97",
        "IC4665": "ic4665-summer-beehive",
        "NGC6633": "ngc6633-open-cluster",
    }
    for object_name, slug in expected.items():
        artwork = resolve_target_artwork(object_name)
        assert artwork["slug"] == slug
        assert artwork["match_kind"] == "exact"


def test_unknown_target_uses_safe_category_fallback():
    galaxy = resolve_target_artwork(
        "POLARIS-UNKNOWN-42",
        common_name="A New Galaxy",
        target_type="Galaxy",
    )
    unknown = resolve_target_artwork("POLARIS-UNKNOWN-43")

    assert galaxy == {
        "slug": None,
        "asset_url": "/operator-assets/target-art/fallbacks/galaxy.svg?v=1",
        "category": "galaxy",
        "match_kind": "category",
        "alt": "Stylized galaxy illustration for A New Galaxy",
    }
    assert unknown["asset_url"].endswith("/deep-sky.svg?v=1")
    assert unknown["match_kind"] == "category"


def test_no_target_preserves_empty_art_state():
    assert resolve_target_artwork(None) is None
    assert resolve_target_artwork(None, common_name=None) is None


def test_exact_and_fallback_assets_are_served_locally():
    client = TestClient(app)
    urls = [
        resolve_target_artwork("M31")["asset_url"],
        resolve_target_artwork("UNKNOWN", target_type="Open Cluster")["asset_url"],
    ]
    for url in urls:
        response = client.get(url)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/svg+xml")
        assert b"<svg" in response.content


def test_art_mounts_are_contained_on_desktop_and_mobile():
    css = Path("app/web/operator.css").read_text(encoding="utf-8")
    assert ".hosted-command-target-illustration img" in css
    assert "object-fit: contain;" in css
    assert ".hosted-target-illustration {\n  width: 154px;\n  height: 88px;" in css
    assert "width: 112px;\n    height: 70px;" in css


def test_build_validator_rejects_active_or_remote_svg_content(tmp_path):
    active = tmp_path / "active.svg"
    active.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        encoding="utf-8",
    )
    remote = tmp_path / "remote.svg"
    remote.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><path style="fill:url(https://bad.test/x)"/></svg>',
        encoding="utf-8",
    )

    for path in (active, remote):
        try:
            _validate_svg(path)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Unsafe SVG passed validation: {path.name}")
