"""Public, plain-language introduction for the private alpha."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(tags=["Public site"])

WEB_DIRECTORY = Path(__file__).resolve().parents[1] / "web"
LANDING_FILE = WEB_DIRECTORY / "landing.html"
LANDING_STYLESHEET = WEB_DIRECTORY / "landing.css"


def _landing_html() -> str:
    asset_version = LANDING_STYLESHEET.stat().st_mtime_ns
    return (
        LANDING_FILE.read_text(encoding="utf-8")
        .replace("__ASSET_VERSION__", str(asset_version))
    )


def _landing_content_security_policy() -> str:
    return "; ".join(
        [
            "default-src 'self'",
            "script-src 'none'",
            "style-src 'self'",
            "img-src 'self' data:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "frame-ancestors 'none'",
            "form-action 'self'",
        ]
    )


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def landing_page():
    """Serve the public alpha introduction without exposing app data."""
    return HTMLResponse(
        _landing_html(),
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": _landing_content_security_policy(),
        },
    )
