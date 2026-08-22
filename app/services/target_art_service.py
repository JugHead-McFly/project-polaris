"""Background NASA reference resolution and cached target-art generation."""

from __future__ import annotations

import html
import json
import logging
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Optional
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.data.target_art_catalog import NASA_TARGET_ART_CATALOG


logger = logging.getLogger(__name__)

NASA_IMAGE_SEARCH_URL = "https://images-api.nasa.gov/search"
NASA_MEDIA_USAGE_URL = "https://www.nasa.gov/nasa-brand-center/images-and-media/"
TARGET_ART_CACHE_SCHEMA = 6
TARGET_ART_CACHE_TTL = timedelta(days=30)
TARGET_ART_CACHE_ROOT = settings.BASE_DIR / ".cache" / "target-art"
CANONICAL_TARGET_ART_PALETTE = (
    "#72d8c6",
    "#f0e4c5",
    "#315f63",
    "#d5a54d",
)
MAPPED_TARGET_ART_ASSETS = {
    "M31": {
        "path": settings.BASE_DIR
        / "app"
        / "web"
        / "target-art"
        / "m31-andromeda.svg",
        "source_catalog_sha256": (
            "2f1d3e608eef02139168a2555041c306"
            "b11f19d744b09a005a3a4365fe444e7c"
        ),
    },
}
_DISALLOWED_ASSET_ELEMENTS = {
    "a",
    "desc",
    "foreignObject",
    "image",
    "script",
    "text",
    "title",
    "use",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _mapped_artwork_svg(target_name: str) -> Optional[str]:
    mapping = MAPPED_TARGET_ART_ASSETS.get(target_name.strip().upper())
    if mapping is None:
        return None
    markup = Path(mapping["path"]).read_text(encoding="utf-8").strip()
    try:
        root = ElementTree.fromstring(markup)
    except ElementTree.ParseError as error:
        raise ValueError("Mapped target artwork is not valid SVG") from error
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise ValueError("Mapped target artwork must have an SVG root")
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag in _DISALLOWED_ASSET_ELEMENTS:
            raise ValueError(f"Mapped target artwork contains disallowed {tag}")
        for raw_name, raw_value in element.attrib.items():
            name = raw_name.rsplit("}", 1)[-1].lower()
            value = str(raw_value).lower()
            if name.startswith("on") or name in {"href", "xlink:href"}:
                raise ValueError("Mapped target artwork contains an unsafe attribute")
            if name == "style" and "http" in value:
                raise ValueError("Mapped target artwork contains an external style URL")
    return markup


def _cache_path(target_name: str, cache_dir: Optional[Path] = None) -> Path:
    root = Path(cache_dir or TARGET_ART_CACHE_ROOT)
    normalized = target_name.strip().upper().replace(" ", "-")
    return root / f"{normalized}.json"


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_cache_entry(
    target_name: str,
    *,
    cache_dir: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    path = _cache_path(target_name, cache_dir)
    try:
        entry = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if (
        not isinstance(entry, dict)
        or entry.get("schema_version") != TARGET_ART_CACHE_SCHEMA
        or entry.get("target") != target_name.strip().upper()
        or not isinstance(entry.get("reference_image"), dict)
    ):
        return None
    return entry


def get_cached_target_reference(
    target_name: str,
    *,
    cache_dir: Optional[Path] = None,
    now: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """Read a cached reference without any network activity."""
    normalized = (target_name or "").strip().upper()
    if normalized not in NASA_TARGET_ART_CATALOG:
        return None
    entry = _load_cache_entry(normalized, cache_dir=cache_dir)
    if entry is None:
        return None

    expires_at = _parse_timestamp(entry.get("expires_at"))
    current_time = (now or _utc_now()).astimezone(timezone.utc)
    reference = dict(entry["reference_image"])
    reference["cache_status"] = (
        "fresh"
        if expires_at is not None and expires_at > current_time
        else "stale"
    )
    return reference


def _candidate_data(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    data = item.get("data")
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        return None
    return data[0]


def _candidate_score(
    item: Dict[str, Any],
    catalog_entry: Dict[str, Any],
) -> Optional[int]:
    data = _candidate_data(item)
    if data is None or data.get("media_type") != "image":
        return None
    # NASA sometimes hosts third-party material under a separate copyright
    # notice.  A generated Polaris reference must never silently inherit it.
    if data.get("copyright"):
        return None

    keywords = data.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [keywords]
    elif not isinstance(keywords, list):
        keywords = []
    corpus = " ".join(
        str(value)
        for value in (
            data.get("nasa_id"),
            data.get("title"),
            data.get("description"),
            " ".join(str(keyword) for keyword in keywords),
        )
        if value
    ).lower()
    required_terms = catalog_entry.get("required_terms") or ()
    if any(term.lower() not in corpus for term in required_terms):
        return None

    title = str(data.get("title") or "").lower()
    score = 0
    for term in required_terms:
        score += 5 if term.lower() in title else 2
    if "hubble" in corpus:
        score += 3
    if data.get("center"):
        score += 1
    if item.get("links"):
        score += 1
    return score


def _select_candidate(
    payload: Dict[str, Any],
    catalog_entry: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    collection = payload.get("collection")
    items = collection.get("items") if isinstance(collection, dict) else None
    if not isinstance(items, list):
        return None
    scored = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        score = _candidate_score(item, catalog_entry)
        if score is not None:
            scored.append((score, -index, item))
    return max(scored, default=(None, None, None))[2]


def _reference_credit(data: Dict[str, Any]) -> str:
    contributors = []
    for key in ("center", "photographer", "secondary_creator"):
        value = str(data.get(key) or "").strip()
        if value and value not in contributors:
            contributors.append(value)
    return " · ".join(contributors) or "NASA"


def _first_preview_url(item: Dict[str, Any]) -> Optional[str]:
    links = item.get("links")
    if not isinstance(links, list):
        return None
    for link in links:
        if not isinstance(link, dict):
            continue
        href = link.get("href")
        if isinstance(href, str) and href.startswith("https://"):
            return href
    return None


def _svg_shell(
    target_name: str,
    profile: str,
    palette: tuple,
    body: str,
    *,
    visual_treatment: str = "canonical-m31-v3",
) -> str:
    safe_profile = html.escape(profile)
    safe_visual_treatment = html.escape(visual_treatment)
    teal, cream, shadow_teal, amber = palette
    prefix = "polaris-" + target_name.lower().replace(" ", "-")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 140" '
        'preserveAspectRatio="xMidYMid meet" aria-hidden="true" '
        f'focusable="false" data-reference="nasa" data-profile="{safe_profile}" '
        f'data-visual-treatment="{safe_visual_treatment}">'
        '<defs>'
        f'<radialGradient id="{prefix}-glow"><stop offset="0" stop-color="{cream}"/>'
        f'<stop offset=".32" stop-color="{teal}" stop-opacity=".72"/>'
        f'<stop offset="1" stop-color="{shadow_teal}" stop-opacity="0"/></radialGradient>'
        '</defs><rect width="240" height="140" fill="#06131a"/>'
        f'<g fill="{cream}" opacity=".66"><circle cx="18" cy="29" r=".7"/>'
        '<circle cx="43" cy="116" r=".55"/><circle cx="74" cy="19" r=".45"/>'
        '<circle cx="105" cy="126" r=".75"/><circle cx="184" cy="18" r=".55"/>'
        '<circle cx="218" cy="108" r=".65"/><circle cx="228" cy="47" r=".4"/></g>'
        f'<g fill="{amber}" opacity=".34"><circle cx="31" cy="67" r=".55"/>'
        '<circle cx="117" cy="22" r=".45"/><circle cx="197" cy="96" r=".5"/></g>'
        f'<path d="M-8 118C42 104 61 124 104 114S177 97 249 108" fill="none" '
        f'stroke="{shadow_teal}" stroke-width=".7" stroke-dasharray="1 7" opacity=".44"/>'
        f'{body}</svg>'
    )


def _generate_artwork_svg(
    target_name: str,
    catalog_entry: Dict[str, Any],
) -> str:
    mapped_artwork = _mapped_artwork_svg(target_name)
    if mapped_artwork is not None:
        return mapped_artwork

    profile = catalog_entry["profile"]
    palette = CANONICAL_TARGET_ART_PALETTE
    teal, cream, shadow_teal, amber = palette
    prefix = "polaris-" + target_name.lower().replace(" ", "-")
    canonical_body = (
        '<g transform="rotate(-17 120 70)">'
        f'<ellipse cx="120" cy="70" rx="92" ry="36" fill="url(#{prefix}-glow)" opacity=".72"/>'
        f'<path d="M28 75C63 41 159 40 212 68" fill="none" stroke="{teal}" '
        'stroke-width="3" stroke-linecap="round" stroke-dasharray="76 10 42 18" opacity=".68"/>'
        f'<path d="M35 56C75 86 160 92 205 61" fill="none" stroke="{cream}" '
        'stroke-width="1.8" stroke-linecap="round" stroke-dasharray="42 13 65 17" opacity=".52"/>'
        f'<path d="M45 87C87 65 162 65 196 78" fill="none" stroke="{shadow_teal}" '
        'stroke-width="4" stroke-linecap="round" stroke-dasharray="61 14" opacity=".56"/>'
        f'<ellipse cx="120" cy="70" rx="25" ry="9" fill="{cream}" opacity=".86"/>'
        f'<circle cx="178" cy="58" r="1.8" fill="{amber}"/>'
        f'<circle cx="68" cy="78" r="1.4" fill="{amber}"/></g>'
    )
    return _svg_shell(target_name, profile, palette, canonical_body)


def _build_cache_entry(
    target_name: str,
    item: Dict[str, Any],
    catalog_entry: Dict[str, Any],
    *,
    now: datetime,
) -> Dict[str, Any]:
    data = _candidate_data(item) or {}
    nasa_id = str(data["nasa_id"])
    title = str(data.get("title") or target_name)
    source_label = (
        catalog_entry.get("source_label") or "NASA Image and Video Library"
    )
    fetched_at = now.astimezone(timezone.utc)
    expires_at = fetched_at + TARGET_ART_CACHE_TTL
    return {
        "schema_version": TARGET_ART_CACHE_SCHEMA,
        "target": target_name,
        "fetched_at": fetched_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "reference_image": {
            "source_url": catalog_entry.get("official_source_url")
            or f"https://images.nasa.gov/details/{quote(nasa_id, safe='')}",
            "source_label": source_label,
            "title": title,
            "alt": f"Polaris representative artwork for {target_name}, informed by NASA reference metadata",
            "nasa_id": nasa_id,
            "credit": catalog_entry.get("credit_override")
            or _reference_credit(data),
            "attribution": f"Art reference · {source_label}",
            "usage_url": NASA_MEDIA_USAGE_URL,
            "remote_preview_url": _first_preview_url(item),
            "artwork_profile": catalog_entry["profile"],
            "artwork_svg": _generate_artwork_svg(target_name, catalog_entry),
            "cache_expires_at": expires_at.isoformat(),
        },
    }


def _write_cache_entry(
    target_name: str,
    entry: Dict[str, Any],
    *,
    cache_dir: Optional[Path] = None,
) -> None:
    path = _cache_path(target_name, cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.stem}-",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        json.dump(entry, temporary, indent=2, sort_keys=True)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def refresh_target_art_cache(
    *,
    client: Optional[httpx.Client] = None,
    cache_dir: Optional[Path] = None,
    now: Optional[datetime] = None,
    force: bool = False,
) -> Dict[str, str]:
    """Refresh mapped targets outside the user-facing request path."""
    current_time = (now or _utc_now()).astimezone(timezone.utc)
    owns_client = client is None
    http_client = client or httpx.Client(
        timeout=httpx.Timeout(10.0),
        headers={"User-Agent": "Project-Polaris/1.0 target-reference-cache"},
        follow_redirects=True,
    )
    statuses: Dict[str, str] = {}
    try:
        for target_name, catalog_entry in NASA_TARGET_ART_CATALOG.items():
            cached = _load_cache_entry(target_name, cache_dir=cache_dir)
            expires_at = _parse_timestamp((cached or {}).get("expires_at"))
            if not force and expires_at is not None and expires_at > current_time:
                statuses[target_name] = "fresh"
                continue
            try:
                response = http_client.get(
                    NASA_IMAGE_SEARCH_URL,
                    params={
                        "q": catalog_entry["query"],
                        "media_type": "image",
                        "page_size": 25,
                    },
                )
                response.raise_for_status()
                candidate = _select_candidate(response.json(), catalog_entry)
                if candidate is None:
                    statuses[target_name] = "stale" if cached else "unavailable"
                    continue
                entry = _build_cache_entry(
                    target_name,
                    candidate,
                    catalog_entry,
                    now=current_time,
                )
                _write_cache_entry(target_name, entry, cache_dir=cache_dir)
                statuses[target_name] = "refreshed"
            except httpx.HTTPStatusError as error:
                logger.warning(
                    "target_art_refresh_failed target=%s status=%s",
                    target_name,
                    error.response.status_code,
                )
                statuses[target_name] = "stale" if cached else "unavailable"
                if error.response.status_code == 429:
                    # A rate-limit response applies to the service, not merely
                    # this catalog entry. Avoid amplifying it with more calls.
                    remaining = list(NASA_TARGET_ART_CATALOG)
                    start = remaining.index(target_name) + 1
                    for remaining_target in remaining[start:]:
                        remaining_cached = _load_cache_entry(
                            remaining_target,
                            cache_dir=cache_dir,
                        )
                        remaining_expiry = _parse_timestamp(
                            (remaining_cached or {}).get("expires_at")
                        )
                        if (
                            not force
                            and remaining_expiry is not None
                            and remaining_expiry > current_time
                        ):
                            statuses[remaining_target] = "fresh"
                        else:
                            statuses[remaining_target] = (
                                "stale" if remaining_cached else "unavailable"
                            )
                    break
            except (httpx.HTTPError, ValueError, TypeError, OSError) as error:
                logger.warning(
                    "target_art_refresh_failed target=%s error_type=%s",
                    target_name,
                    type(error).__name__,
                )
                statuses[target_name] = "stale" if cached else "unavailable"
    finally:
        if owns_client:
            http_client.close()
    return statuses
