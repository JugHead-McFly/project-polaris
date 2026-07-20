import os
import tempfile
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.advisor import router as advisor_router
from app.api.captures import router as capture_router
from app.api.candidate_sites import router as candidate_sites_router
from app.api.dashboard import router as dashboard_router
from app.api.mission import router as mission_router
from app.api.objects import router as objects_router
from app.api.operator import router as operator_router
from app.api.portfolio import router as portfolio_router
from app.api.sessions import router as sessions_router
from app.api.system import router as system_router
from app.api.tonight import router as tonight_router
from app.core.config import settings
from app.core.runtime_logging import configure_logging
from app.core.startup_preflight import format_preflight_failure
from app.core.startup_preflight import log_preflight_report
from app.core.startup_preflight import run_startup_preflight
from app.database.database import SessionLocal
from app.services.capture_service import (
    create_capture_from_parsed_fits,
)
from parser.fits_parser import parse_fits
from app.api.planner import (
    router as planner_router,
)
from app.api.schedule import router as schedule_router


logger = configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    report = run_startup_preflight()
    log_preflight_report(report, logger)
    if not report["ready"]:
        raise RuntimeError(format_preflight_failure(report))
    yield


app = FastAPI(
    title="Project Polaris API",
    version=settings.VERSION,
    lifespan=lifespan,
)


@app.middleware("http")
async def log_request(request: Request, call_next):
    request_id = uuid4().hex[:12]
    started_at = perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((perf_counter() - started_at) * 1000, 1)
        logger.exception(
            "request_failed request_id=%s method=%s path=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error.",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )

    duration_ms = round((perf_counter() - started_at) * 1000, 1)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        (
            "request_complete request_id=%s method=%s path=%s "
            "status=%s duration_ms=%s"
        ),
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response

WEB_DIRECTORY = settings.BASE_DIR / "app" / "web"
app.mount(
    "/operator-assets",
    StaticFiles(directory=str(WEB_DIRECTORY), check_dir=False),
    name="operator-assets",
)


app.include_router(capture_router)
app.include_router(candidate_sites_router)
app.include_router(mission_router)
app.include_router(dashboard_router)
app.include_router(sessions_router)
app.include_router(objects_router)
app.include_router(operator_router)
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
        "operator_dashboard": "/operator",
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
