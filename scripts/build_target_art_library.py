"""Validate and bundle the independent Polaris target-art library.

The runtime reads only the reduced catalog produced here. Provenance stays in
the independent source library and no network access is needed by the app.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path(
    "/Users/doug/Documents/Codex/2026-08-22/library-creation/outputs/"
    "polaris-astronomy-vector-library"
)
OUTPUT_CATALOG = REPO_ROOT / "app" / "data" / "target_art_library.json"
OUTPUT_ASSETS = REPO_ROOT / "app" / "web" / "target-art" / "library" / "assets"
DISALLOWED_ELEMENTS = {
    "a", "audio", "embed", "foreignobject", "iframe", "image", "object",
    "script", "style", "use", "video",
}


def _local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1]


def _validate_svg(path: Path) -> None:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        raise ValueError(f"Invalid SVG XML: {path}") from error

    if _local_name(root.tag) != "svg":
        raise ValueError(f"SVG root missing: {path}")

    for element in root.iter():
        tag = _local_name(element.tag).lower()
        if tag in DISALLOWED_ELEMENTS:
            raise ValueError(f"Disallowed <{tag}> in {path}")
        for raw_name, raw_value in element.attrib.items():
            name = _local_name(raw_name).lower()
            value = raw_value.strip().lower()
            if name.startswith("on") or name == "href":
                raise ValueError(f"Unsafe attribute {name} in {path}")
            if re.search(r"url\(\s*['\"]?(?!#)", value):
                raise ValueError(f"External URL in {path}")
            if "http://" in value or "https://" in value:
                raise ValueError(f"External reference in {path}")


def build(source_root: Path) -> dict:
    source_root = source_root.resolve()
    source_catalog = source_root / "catalog" / "targets.json"
    source_assets = (source_root / "assets").resolve()
    catalog = json.loads(source_catalog.read_text(encoding="utf-8"))
    targets = catalog.get("targets")
    if not isinstance(targets, list) or len(targets) != 1000:
        raise ValueError("The independent library must contain exactly 1,000 targets")

    reduced_targets = []
    seen_slugs = set()
    seen_assets = set()
    for entry in targets:
        slug = entry.get("slug")
        display_name = entry.get("display_name")
        category = entry.get("category")
        relative_asset = entry.get("asset")
        if not all(isinstance(value, str) and value for value in (
            slug, display_name, category, relative_asset
        )):
            raise ValueError("Every target needs slug, display_name, category, and asset")
        if slug in seen_slugs or relative_asset in seen_assets:
            raise ValueError(f"Duplicate target-art entry: {slug}")
        if not relative_asset.startswith("assets/") or not relative_asset.endswith(".svg"):
            raise ValueError(f"Unsafe asset path: {relative_asset}")

        source_asset = (source_root / relative_asset).resolve()
        if source_assets not in source_asset.parents or not source_asset.is_file():
            raise ValueError(f"Missing or escaped asset: {relative_asset}")
        _validate_svg(source_asset)
        seen_slugs.add(slug)
        seen_assets.add(relative_asset)
        reduced_targets.append(
            {
                "slug": slug,
                "display_name": display_name,
                "category": category,
                "asset": relative_asset,
            }
        )

    if OUTPUT_ASSETS.parent.exists():
        shutil.rmtree(OUTPUT_ASSETS.parent)
    OUTPUT_ASSETS.mkdir(parents=True)
    for entry in reduced_targets:
        source_asset = source_root / entry["asset"]
        shutil.copy2(source_asset, OUTPUT_ASSETS / source_asset.name)

    reduced_catalog = {
        "library": catalog.get("library", "Project Polaris Astronomy Vector Art Library"),
        "version": catalog.get("version", "1"),
        "target_count": len(reduced_targets),
        "targets": reduced_targets,
    }
    OUTPUT_CATALOG.write_text(
        json.dumps(reduced_catalog, indent=2) + "\n",
        encoding="utf-8",
    )
    return reduced_catalog


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    result = build(args.source)
    print(
        f"Bundled {result['target_count']} validated target-art assets "
        f"from library {result['version']}."
    )


if __name__ == "__main__":
    main()
