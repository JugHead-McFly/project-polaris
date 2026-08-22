"""Background NASA reference resolution and cached target-art generation."""

from __future__ import annotations

import html
import json
import logging
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
TARGET_ART_CACHE_SCHEMA = 2
TARGET_ART_CACHE_TTL = timedelta(days=30)
TARGET_ART_CACHE_ROOT = settings.BASE_DIR / ".cache" / "target-art"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
) -> str:
    safe_target = html.escape(target_name)
    safe_profile = html.escape(profile)
    teal, cream, shadow_teal, amber = palette
    prefix = "polaris-" + target_name.lower().replace(" ", "-")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 140" '
        'preserveAspectRatio="xMidYMid slice" aria-hidden="true" '
        f'focusable="false" data-reference="nasa" data-profile="{safe_profile}" '
        'data-visual-treatment="supporting-vignette-v2">'
        f'<title>Polaris representative artwork for {safe_target}</title>'
        '<defs>'
        f'<radialGradient id="{prefix}-glow"><stop offset="0" stop-color="{cream}"/>'
        f'<stop offset=".32" stop-color="{teal}" stop-opacity=".72"/>'
        f'<stop offset="1" stop-color="{shadow_teal}" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="{prefix}-accent" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{teal}"/><stop offset=".72" stop-color="{cream}"/>'
        f'<stop offset="1" stop-color="{amber}"/></linearGradient>'
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
    profile = catalog_entry["profile"]
    palette = catalog_entry.get("palette") or (
        "#72d8c6",
        "#f0e4c5",
        "#315f63",
        "#d5a54d",
    )
    teal, cream, shadow_teal, amber = palette
    prefix = "polaris-" + target_name.lower().replace(" ", "-")
    if profile == "face_on_spiral_companion":
        body = (
            '<g transform="translate(78 82) rotate(-23)">'
            f'<circle r="62" fill="url(#{prefix}-glow)" opacity=".33"/>'
            '<path d="M-18-8C8-42 62-44 77-11C91 20 56 55 8 55C-40 56-75 28-65-5" '
            f'fill="none" stroke="{shadow_teal}" stroke-width="10" opacity=".52"/>'
            '<path d="M-9-2C20-31 58-24 62 2C65 25 41 45 9 46C-20 48-44 31-47 11" '
            f'fill="none" stroke="{teal}" stroke-width="5" stroke-linecap="round" '
            'stroke-dasharray="54 11 23 17" opacity=".82"/>'
            '<path d="M5 7C-18 29-52 17-55-9C-59-34-25-55 15-48C49-42 71-15 59 9" '
            f'fill="none" stroke="{cream}" stroke-width="2.4" stroke-linecap="round" '
            'stroke-dasharray="33 9 48 15" opacity=".58"/>'
            f'<ellipse cx="-3" cy="4" rx="13" ry="9" fill="{cream}" opacity=".9"/>'
            f'<g fill="{amber}"><circle cx="-47" cy="16" r="1.8"/>'
            '<circle cx="-20" cy="43" r="1.25"/><circle cx="30" cy="38" r="1.6"/>'
            '<circle cx="61" cy="-10" r="1.2"/></g></g>'
            f'<path d="M135 54C158 35 178 31 198 38" fill="none" stroke="{teal}" '
            'stroke-width="1.3" stroke-dasharray="2 6" opacity=".38"/>'
            f'<ellipse cx="204" cy="36" rx="20" ry="13" fill="{amber}" opacity=".52" '
            'transform="rotate(13 204 36)"/>'
            f'<ellipse cx="202" cy="35" rx="7" ry="4.5" fill="{cream}" opacity=".9"/>'
        )
    elif profile == "inclined_spiral":
        body = (
            '<g transform="rotate(-17 151 72)">'
            f'<ellipse cx="151" cy="72" rx="99" ry="38" fill="url(#{prefix}-glow)" opacity=".72"/>'
            f'<path d="M53 77C89 40 185 39 243 69" fill="none" stroke="{teal}" '
            'stroke-width="3" stroke-linecap="round" stroke-dasharray="76 10 42 18" opacity=".68"/>'
            f'<path d="M63 57C103 88 188 94 235 62" fill="none" stroke="{cream}" '
            'stroke-width="1.8" stroke-linecap="round" stroke-dasharray="42 13 65 17" opacity=".52"/>'
            f'<path d="M74 89C116 66 193 66 224 79" fill="none" stroke="{shadow_teal}" '
            'stroke-width="4" stroke-linecap="round" stroke-dasharray="61 14" opacity=".56"/>'
            f'<ellipse cx="145" cy="71" rx="25" ry="9" fill="{cream}" opacity=".86"/>'
            f'<circle cx="205" cy="60" r="1.8" fill="{amber}"/>'
            f'<circle cx="92" cy="79" r="1.4" fill="{amber}"/></g>'
        )
    elif profile == "ring_nebula":
        body = (
            f'<ellipse cx="145" cy="69" rx="59" ry="43" fill="url(#{prefix}-glow)" opacity=".42"/>'
            f'<path d="M101 48C121 20 169 23 190 55C209 85 180 112 143 108C108 105 85 78 101 48Z" '
            f'fill="none" stroke="{teal}" stroke-width="12" stroke-linecap="round" '
            'stroke-dasharray="67 9 35 12" opacity=".74"/>'
            f'<path d="M115 49C137 36 168 42 179 62C190 82 166 98 142 94C119 91 105 70 115 49Z" '
            f'fill="#071720" stroke="{cream}" stroke-width="2" stroke-dasharray="35 8" opacity=".9"/>'
            f'<circle cx="148" cy="68" r="2" fill="{amber}"/>'
        )
    elif profile == "globular_cluster":
        stars = (
            (120, 70, 7), (95, 53, 4), (145, 49, 5), (151, 79, 4),
            (88, 86, 5), (120, 101, 3), (68, 68, 3), (175, 64, 3),
        )
        circles = "".join(
            f'<circle cx="{cx + 22}" cy="{cy}" r="{radius}" fill="{(cream if index % 2 == 0 else teal)}" opacity=".78"/>'
            for index, (cx, cy, radius) in enumerate(stars)
        )
        body = (
            f'<circle cx="142" cy="70" r="58" fill="url(#{prefix}-glow)" opacity=".34"/>'
            f'{circles}<path d="M83 91C121 111 177 105 202 76" fill="none" '
            f'stroke="{shadow_teal}" stroke-width="1" stroke-dasharray="2 7" opacity=".5"/>'
        )
    elif profile == "pillar_nebula":
        body = (
            f'<path d="M55 118C63 50 91 38 111 67C130 25 174 30 181 80C198 58 220 70 228 111Z" fill="url(#{prefix}-accent)" opacity=".5"/>'
            '<path d="M102 116C94 89 101 57 116 48C128 73 122 96 132 116M151 116C147 81 159 50 175 42C185 70 173 98 184 116" '
            f'fill="#102a32" stroke="{amber}" stroke-width="1.8" stroke-dasharray="45 6" opacity=".88"/>'
            f'<circle cx="141" cy="40" r="3" fill="{cream}"/>'
        )
    else:
        body = (
            f'<path d="M56 101C75 44 112 34 137 61C166 25 220 45 233 91C204 118 167 108 145 97C116 121 76 121 56 101Z" fill="url(#{prefix}-accent)" opacity=".5"/>'
            f'<path d="M79 94C102 65 124 93 146 67C169 43 204 57 219 84" fill="none" stroke="{cream}" '
            'stroke-width="2" stroke-linecap="round" stroke-dasharray="39 11 30 16" opacity=".52"/>'
            f'<circle cx="151" cy="67" r="5" fill="{amber}" opacity=".82"/>'
        )
    return _svg_shell(target_name, profile, palette, body)


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
