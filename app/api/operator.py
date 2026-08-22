import json
import secrets
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.storage import TARGETS_ROOT
from app.core.storage import get_processed_preview_path
from app.core.config import settings
from app.database.database import get_tenant_db
from app.models import Capture


router = APIRouter(tags=["Operator Dashboard"])

DASHBOARD_FILE = (
    Path(__file__).resolve().parents[1]
    / "web"
    / "operator.html"
)
WEB_DIRECTORY = DASHBOARD_FILE.parent
ASSET_FILES = (
    WEB_DIRECTORY / "operator.css",
    WEB_DIRECTORY / "operator.js",
    WEB_DIRECTORY / "leaflet.css",
    WEB_DIRECTORY / "leaflet.js",
    WEB_DIRECTORY / "target-art" / "m31-andromeda.svg",
)


def _dashboard_html(*, script_nonce: str = "test-nonce") -> str:
    asset_version = max(
        asset.stat().st_mtime_ns
        for asset in ASSET_FILES
    )
    auth_config = json.dumps(
        {
            "mode": settings.AUTH_MODE,
            "supabaseUrl": settings.SUPABASE_URL,
            "supabasePublishableKey": settings.SUPABASE_PUBLISHABLE_KEY,
        },
    ).replace("<", "\\u003c")
    auth_script = (
        '<script defer src="https://cdn.jsdelivr.net/npm/'
        '@supabase/supabase-js@2"></script>'
        if settings.AUTH_MODE == "supabase"
        else ""
    )
    return (
        DASHBOARD_FILE.read_text(encoding="utf-8")
        .replace("__ASSET_VERSION__", str(asset_version))
        .replace("__POLARIS_AUTH_CONFIG__", auth_config)
        .replace("__SUPABASE_CLIENT_SCRIPT__", auth_script)
        .replace("__SCRIPT_NONCE__", script_nonce)
    )


def _dashboard_content_security_policy(script_nonce: str) -> str:
    script_sources = ["'self'", f"'nonce-{script_nonce}'"]
    connect_sources = ["'self'"]
    if settings.AUTH_MODE == "supabase" and settings.SUPABASE_URL:
        supabase_url = urlsplit(settings.SUPABASE_URL)
        supabase_origin = (
            f"{supabase_url.scheme}://{supabase_url.netloc}"
        )
        script_sources.append("https://cdn.jsdelivr.net")
        connect_sources.extend(
            [
                supabase_origin,
                f"wss://{supabase_url.netloc}",
            ]
        )

    return "; ".join(
        [
            "default-src 'self'",
            f"script-src {' '.join(script_sources)}",
            "style-src 'self' 'unsafe-inline'",
            (
                "img-src 'self' data: blob: "
                "https://*.tile.openstreetmap.org"
            ),
            f"connect-src {' '.join(connect_sources)}",
            "font-src 'self' data:",
            "object-src 'none'",
            "base-uri 'self'",
            "frame-ancestors 'none'",
            "form-action 'self'",
        ]
    )


def _find_preview_path(
    capture: Capture,
    processed: bool = False,
):
    if not capture.object_name or not capture.polaris_id:
        return None

    target_root = (
        TARGETS_ROOT
        / capture.object_name.upper()
    ).resolve()
    library_root = TARGETS_ROOT.resolve()

    if library_root not in target_root.parents:
        return None

    if processed:
        candidate = get_processed_preview_path(
            object_name=capture.object_name,
            polaris_id=capture.polaris_id,
        ).resolve()
        return (
            candidate
            if target_root in candidate.parents and candidate.is_file()
            else None
        )

    for folder, suffix in (("jpg", ".jpg"), ("png", ".png")):
        candidate = (
            target_root
            / folder
            / f"{capture.polaris_id}{suffix}"
        ).resolve()
        if target_root in candidate.parents and candidate.is_file():
            return candidate

    return None


@router.get(
    "/operator/locations",
    response_class=HTMLResponse,
    include_in_schema=False,
)
@router.get(
    "/operator/data",
    response_class=HTMLResponse,
    include_in_schema=False,
)
@router.get(
    "/operator/history",
    response_class=HTMLResponse,
    include_in_schema=False,
)
@router.get(
    "/operator/quality",
    response_class=HTMLResponse,
    include_in_schema=False,
)
@router.get(
    "/operator/portfolio",
    response_class=HTMLResponse,
    include_in_schema=False,
)
@router.get(
    "/operator",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def operator_dashboard():
    script_nonce = secrets.token_urlsafe(18)
    return HTMLResponse(
        _dashboard_html(script_nonce=script_nonce),
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": (
                _dashboard_content_security_policy(script_nonce)
            ),
        },
    )


@router.get(
    "/operator-preview/{polaris_id}",
    response_class=FileResponse,
    include_in_schema=False,
)
def operator_preview(
    polaris_id: str,
    variant: str = "original",
    _current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_tenant_db),
):
    if variant not in {"original", "processed"}:
        raise HTTPException(
            status_code=404,
            detail="Capture preview variant was not found.",
        )

    capture = (
        db.query(Capture)
        .filter(Capture.polaris_id == polaris_id)
        .first()
    )
    preview_path = (
        _find_preview_path(
            capture,
            processed=variant == "processed",
        )
        if capture is not None
        else None
    )

    if preview_path is None:
        raise HTTPException(
            status_code=404,
            detail="Capture preview was not found.",
        )

    return FileResponse(
        preview_path,
        media_type=(
            "image/jpeg"
            if preview_path.suffix.lower() == ".jpg"
            else "image/png"
        ),
        headers={"Cache-Control": "private, max-age=3600"},
    )
