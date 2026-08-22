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
TARGET_ART_CACHE_SCHEMA = 1
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


def _svg_shell(target_name: str, profile: str, body: str) -> str:
    safe_target = html.escape(target_name)
    safe_profile = html.escape(profile)
    prefix = "polaris-" + target_name.lower().replace(" ", "-")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 140" '
        'preserveAspectRatio="xMidYMid meet" aria-hidden="true" '
        f'focusable="false" data-reference="nasa" data-profile="{safe_profile}">'
        f'<title>Polaris representative artwork for {safe_target}</title>'
        '<defs>'
        f'<radialGradient id="{prefix}-glow"><stop offset="0" stop-color="#fff6d8"/>'
        '<stop offset=".3" stop-color="#7fe4d8" stop-opacity=".82"/>'
        '<stop offset="1" stop-color="#294a62" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="{prefix}-accent" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#8be9dc"/><stop offset=".55" stop-color="#668fc1"/>'
        '<stop offset="1" stop-color="#e48191"/></linearGradient>'
        '</defs><rect width="240" height="140" rx="14" fill="#06141e"/>'
        '<g fill="#d8fff7" opacity=".7"><circle cx="22" cy="24" r="1.2"/>'
        '<circle cx="52" cy="111" r=".9"/><circle cx="206" cy="24" r="1.1"/>'
        '<circle cx="196" cy="114" r="1.2"/><circle cx="221" cy="72" r=".8"/></g>'
        f'{body}</svg>'
    )


def _generate_artwork_svg(
    target_name: str,
    catalog_entry: Dict[str, Any],
) -> str:
    profile = catalog_entry["profile"]
    prefix = "polaris-" + target_name.lower().replace(" ", "-")
    if profile == "face_on_spiral_companion":
        body = (
            '<g transform="translate(103 72) rotate(-16)">'
            f'<circle r="57" fill="url(#{prefix}-glow)" opacity=".38"/>'
            '<path d="M-5-4C30-36 72-19 69 14C66 46 18 62-29 43C-68 27-79-12-53-38" '
            f'fill="none" stroke="url(#{prefix}-accent)" stroke-width="9" opacity=".72"/>'
            '<path d="M6 5C-28 36-69 18-67-14C-65-44-20-62 27-44C66-29 80 10 54 37" '
            'fill="none" stroke="#93e8de" stroke-width="6" opacity=".64"/>'
            '<circle r="14" fill="#fff1c4" opacity=".94"/>'
            '<g fill="#ed8794"><circle cx="-52" cy="9" r="2.5"/><circle cx="-24" cy="45" r="2.2"/>'
            '<circle cx="37" cy="39" r="2.4"/><circle cx="59" cy="-7" r="2.2"/></g></g>'
            '<path d="M148 55C167 35 188 30 204 40" fill="none" stroke="#7dbdc8" '
            'stroke-width="1.5" stroke-dasharray="4 5" opacity=".4"/>'
            '<ellipse cx="207" cy="38" rx="23" ry="16" fill="#f0ce91" opacity=".62"/>'
            '<ellipse cx="207" cy="38" rx="8" ry="6" fill="#fff0bf"/>'
        )
    elif profile == "inclined_spiral":
        body = (
            '<g transform="rotate(-18 120 70)">'
            f'<ellipse cx="120" cy="70" rx="94" ry="39" fill="url(#{prefix}-glow)" opacity=".95"/>'
            '<ellipse cx="120" cy="70" rx="82" ry="27" fill="none" stroke="#6eddd2" stroke-width="2" opacity=".46"/>'
            '<path d="M38 77C72 40 166 40 202 69C165 55 83 63 52 91" fill="none" stroke="#b7fff5" stroke-width="2.2" opacity=".6"/>'
            '<path d="M49 56C86 86 165 91 195 61C166 100 84 102 43 70" fill="none" stroke="#dc8791" stroke-width="1.6" opacity=".42"/>'
            '<ellipse cx="120" cy="70" rx="26" ry="12" fill="#f7ead2" opacity=".92"/></g>'
        )
    elif profile == "ring_nebula":
        body = (
            f'<ellipse cx="120" cy="70" rx="59" ry="43" fill="url(#{prefix}-glow)" opacity=".54"/>'
            f'<ellipse cx="120" cy="70" rx="42" ry="30" fill="none" stroke="url(#{prefix}-accent)" stroke-width="15" opacity=".84"/>'
            '<ellipse cx="120" cy="70" rx="25" ry="18" fill="#071720" stroke="#78dfd5" stroke-width="3" opacity=".92"/>'
            '<circle cx="120" cy="70" r="2.2" fill="#fff2ce"/>'
        )
    elif profile == "globular_cluster":
        stars = (
            (120, 70, 7), (95, 53, 4), (145, 49, 5), (151, 79, 4),
            (88, 86, 5), (120, 101, 3), (68, 68, 3), (175, 64, 3),
        )
        circles = "".join(
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="{("#f7ead2" if index % 2 == 0 else "#75ded4")}" opacity=".82"/>'
            for index, (cx, cy, radius) in enumerate(stars)
        )
        body = f'<circle cx="120" cy="70" r="58" fill="url(#{prefix}-glow)" opacity=".38"/>{circles}'
    elif profile == "pillar_nebula":
        body = (
            f'<path d="M38 112C48 42 78 34 101 67C122 24 164 32 170 79C190 51 215 67 211 111Z" fill="url(#{prefix}-accent)" opacity=".62"/>'
            '<path d="M83 113C78 85 84 57 98 48C112 70 107 94 116 113M137 113C132 80 143 49 158 42C171 69 160 95 168 113" '
            'fill="#102a32" stroke="#e2b081" stroke-width="2" opacity=".92"/>'
            '<circle cx="126" cy="43" r="5" fill="#fff1c9"/>'
        )
    else:
        body = (
            f'<path d="M37 94C57 42 91 31 119 59C145 24 202 42 208 91C181 117 147 110 125 96C96 121 56 119 37 94Z" fill="url(#{prefix}-accent)" opacity=".68"/>'
            '<path d="M61 91C84 65 106 94 128 67C151 42 181 56 191 84" fill="none" stroke="#c3fff6" stroke-width="2.4" opacity=".58"/>'
            '<circle cx="127" cy="68" r="7" fill="#f7ead2" opacity=".9"/>'
        )
    return _svg_shell(target_name, profile, body)


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
