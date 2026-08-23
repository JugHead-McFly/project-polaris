"""Resolve local target artwork without making request-time network calls."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Dict, Optional

from app.core.config import settings


CATALOG_PATH = settings.BASE_DIR / "app" / "data" / "target_art_library.json"
ASSET_ROOT = settings.BASE_DIR / "app" / "web" / "target-art" / "library"
ASSET_URL_ROOT = "/operator-assets/target-art/library"
FALLBACK_URL_ROOT = "/operator-assets/target-art/fallbacks"

# These aliases are deliberately explicit. They resolve identities Polaris
# already knows, including ambiguous catalog cases such as M16.
VERIFIED_ALIASES = {
    "C20": "north-america-nebula",
    "CALDWELL20": "north-america-nebula",
    "NGC7000": "north-america-nebula",
    "NORTHAMERICANEBULA": "north-america-nebula",
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


def _normalize(value: Optional[str]) -> str:
    return re.sub(r"[^A-Z0-9]+", "", (value or "").upper())


def _fallback_category(target_type: Optional[str]) -> str:
    value = _normalize(target_type)
    if "PLANETARYNEBULA" in value:
        return "planetary-nebula"
    if "GALAXY" in value:
        return "galaxy"
    if "NEBULA" in value:
        return "nebula"
    if "CLUSTER" in value:
        return "cluster"
    if any(name in value for name in ("PLANET", "MOON", "COMET", "ASTEROID")):
        return "solar-system"
    return "deep-sky"


@lru_cache(maxsize=1)
def _catalog() -> Dict:
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if data.get("target_count") != 1000 or len(data.get("targets", [])) != 1000:
        raise RuntimeError("Bundled target-art catalog is incomplete")

    by_slug = {}
    by_exact_name = {}
    for entry in data["targets"]:
        slug = entry["slug"]
        asset = entry["asset"]
        asset_path = (ASSET_ROOT / asset).resolve()
        if ASSET_ROOT.resolve() not in asset_path.parents or not asset_path.is_file():
            raise RuntimeError(f"Unsafe or missing bundled target art: {asset}")
        by_slug[slug] = entry
        by_exact_name.setdefault(_normalize(entry["display_name"]), []).append(entry)
        by_exact_name.setdefault(_normalize(slug), []).append(entry)

    for alias, slug in VERIFIED_ALIASES.items():
        if slug not in by_slug:
            raise RuntimeError(f"Verified target-art alias points to missing slug: {alias}")

    return {
        "version": data["version"],
        "by_slug": by_slug,
        "by_exact_name": by_exact_name,
    }


def _exact_entry(object_name: Optional[str], common_name: Optional[str]) -> Optional[Dict]:
    catalog = _catalog()
    values = [object_name, common_name]
    for value in values:
        normalized = _normalize(value)
        slug = VERIFIED_ALIASES.get(normalized)
        if slug:
            return catalog["by_slug"][slug]

    combined = " ".join(value for value in values if value)
    for value in (*values, combined):
        matches = catalog["by_exact_name"].get(_normalize(value), [])
        unique_slugs = {entry["slug"] for entry in matches}
        if len(unique_slugs) == 1:
            return matches[0]
    return None


def resolve_target_artwork(
    object_name: Optional[str],
    *,
    common_name: Optional[str] = None,
    target_type: Optional[str] = None,
) -> Optional[Dict]:
    """Return one approved local artwork URL, or None for a missing target."""

    if not object_name and not common_name:
        return None

    catalog = _catalog()
    entry = _exact_entry(object_name, common_name)
    target_label = common_name or object_name or "deep-sky target"
    if entry:
        return {
            "slug": entry["slug"],
            "asset_url": (
                f"{ASSET_URL_ROOT}/{entry['asset']}?v={catalog['version']}"
            ),
            "category": entry["category"],
            "match_kind": "exact",
            "alt": f"Polaris illustration of {target_label}",
        }

    category = _fallback_category(target_type)
    return {
        "slug": None,
        "asset_url": f"{FALLBACK_URL_ROOT}/{category}.svg?v=1",
        "category": category,
        "match_kind": "category",
        "alt": f"Stylized {category.replace('-', ' ')} illustration for {target_label}",
    }
