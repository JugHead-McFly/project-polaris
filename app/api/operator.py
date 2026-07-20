from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from app.core.storage import TARGETS_ROOT
from app.database.database import SessionLocal
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
)


def _dashboard_html() -> str:
    asset_version = max(
        asset.stat().st_mtime_ns
        for asset in ASSET_FILES
    )
    return DASHBOARD_FILE.read_text(encoding="utf-8").replace(
        "__ASSET_VERSION__",
        str(asset_version),
    )


def _find_preview_path(capture: Capture):
    if not capture.object_name or not capture.polaris_id:
        return None

    target_root = (
        TARGETS_ROOT
        / capture.object_name.upper()
    ).resolve()
    library_root = TARGETS_ROOT.resolve()

    if library_root not in target_root.parents:
        return None

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
    return HTMLResponse(
        _dashboard_html(),
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/operator-preview/{polaris_id}",
    response_class=FileResponse,
    include_in_schema=False,
)
def operator_preview(polaris_id: str):
    db = SessionLocal()

    try:
        capture = (
            db.query(Capture)
            .filter(Capture.polaris_id == polaris_id)
            .first()
        )
        preview_path = (
            _find_preview_path(capture)
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
    finally:
        db.close()
