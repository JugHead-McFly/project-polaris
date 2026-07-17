import os
import tempfile

from fastapi import FastAPI, File, UploadFile

from app.api.advisor import router as advisor_router
from app.api.captures import router as capture_router
from app.api.dashboard import router as dashboard_router
from app.api.mission import router as mission_router
from app.api.objects import router as objects_router
from app.api.portfolio import router as portfolio_router
from app.api.sessions import router as sessions_router
from app.api.system import router as system_router
from app.api.tonight import router as tonight_router
from app.core.config import settings
from app.database.database import SessionLocal
from app.services.capture_service import (
    create_capture_from_parsed_fits,
)
from parser.fits_parser import parse_fits
from app.api.planner import (
    router as planner_router,
)
from app.api.schedule import router as schedule_router


app = FastAPI(
    title="Project Polaris API",
    version=settings.VERSION,
)


app.include_router(capture_router)
app.include_router(mission_router)
app.include_router(dashboard_router)
app.include_router(sessions_router)
app.include_router(objects_router)
app.include_router(portfolio_router)
app.include_router(tonight_router)
app.include_router(system_router)
app.include_router(advisor_router)
app.include_router(
    planner_router
)
app.include_router(schedule_router)


@app.get("/")
def root():
    return {
        "status": "Project Polaris API is running",
        "version": settings.VERSION,
    }


@app.post("/parse-fits")
async def parse_fits_upload(
    file: UploadFile = File(...),
):
    suffix = (
        os.path.splitext(file.filename or "")[1]
        or ".fits"
    )

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    ) as tmp:
        tmp.write(
            await file.read()
        )
        tmp_path = tmp.name

    try:
        result = parse_fits(
            tmp_path
        )

        result["filename"] = (
            file.filename
        )

        return result

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/ingest-fits")
async def ingest_fits_upload(
    file: UploadFile = File(...),
):
    suffix = (
        os.path.splitext(file.filename or "")[1]
        or ".fits"
    )

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    ) as tmp:
        tmp.write(
            await file.read()
        )
        tmp_path = tmp.name

    db = SessionLocal()

    try:
        parsed = parse_fits(
            tmp_path
        )

        capture = create_capture_from_parsed_fits(
            db=db,
            parsed=parsed,
            filename=(
                file.filename
                or f"upload{suffix}"
            ),
            source_path=tmp_path,
        )

        return {
            "status": "saved",
            "capture": {
                "id": capture.id,
                "polaris_id": (
                    capture.polaris_id
                ),
                "object_name": (
                    capture.object_name
                ),
                "filename": (
                    capture.filename
                ),
                "asset_path": (
                    capture.asset_path
                ),
                "observation_utc": (
                    capture.observation_utc
                ),
                "gain": capture.gain,
                "ra": capture.ra,
                "dec": capture.dec,
                "telescope": (
                    capture.telescope
                ),
                "firmware": (
                    capture.firmware
                ),
                "status": (
                    capture.status
                ),
            },
            "parsed": parsed,
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

        if os.path.exists(tmp_path):
            os.remove(tmp_path)
