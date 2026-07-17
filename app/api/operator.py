from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(tags=["Operator Dashboard"])

DASHBOARD_FILE = (
    Path(__file__).resolve().parents[1]
    / "web"
    / "operator.html"
)


@router.get(
    "/operator",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def operator_dashboard():
    return HTMLResponse(
        DASHBOARD_FILE.read_text(encoding="utf-8"),
        headers={"Cache-Control": "no-store"},
    )
