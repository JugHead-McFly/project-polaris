import os
import tempfile
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.advisor import router as advisor_router
from app.api.auth import router as auth_router
from app.api.captures import router as capture_router
from app.api.candidate_sites import router as candidate_sites_router
from app.api.dashboard import router as dashboard_router
from app.api.hosted_account import router as hosted_account_router
from app.api.landing import router as landing_router
from app.api.mission import router as mission_router
from app.api.objects import router as objects_router
from app.api.operator import router as operator_router
from app.api.portfolio import router as portfolio_router
from app.api.recommendations import router as recommendations_router
from app.api.sessions import router as sessions_router
from app.api.system import router as system_router
from app.api.tonight import router as tonight_router
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.monitoring import capture_request_exception
from app.core.monitoring import capture_monitoring_smoke_test
from app.core.monitoring import configure_monitoring
from app.core.runtime_logging import configure_logging
from app.core.startup_preflight import format_preflight_failure
from app.core.startup_preflight import log_preflight_report
from app.core.startup_preflight import run_startup_preflight
from app.database.database import get_db
from app.database.database import get_tenant_db
from app.services.capture_service import (
    create_capture_from_parsed_fits,
)
from parser.fits_parser import parse_fits
from app.api.planner import (
    router as planner_router,
)
from app.api.schedule import router as schedule_router


monitoring_enabled = configure_monitoring()
logger = configure_logging()
if settings.SENTRY_SMOKE_TEST_ID:
    capture_monitoring_smoke_test(settings.SENTRY_SMOKE_TEST_ID)


def apply_browser_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    # Polaris only requests a location after the person explicitly clicks the
    # setup shortcut.  Keep camera and microphone disabled, but permit that
    # one browser feature for this same hosted site.
    response.headers["Permissions-Policy"] = (
        "camera=(), geolocation=(self), microphone=()"
    )
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


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
    docs_url=(
        None
        if settings.ENVIRONMENT == "production"
        else "/docs"
    ),
    redoc_url=(
        None
        if settings.ENVIRONMENT == "production"
        else "/redoc"
    ),
    openapi_url=(
        None
        if settings.ENVIRONMENT == "production"
        else "/openapi.json"
    ),
)


@app.middleware("http")
async def log_request(request: Request, call_next):
    request_id = uuid4().hex[:12]
    started_at = perf_counter()

    try:
        response = await call_next(request)
    except Exception as error:
        duration_ms = round((perf_counter() - started_at) * 1000, 1)
        capture_request_exception(
            error,
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        logger.error(
            (
                "request_failed request_id=%s method=%s path=%s "
                "duration_ms=%s error_type=%s"
            ),
            request_id,
            request.method,
            request.url.path,
            duration_ms,
            type(error).__name__,
        )
        return apply_browser_security_headers(
            JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error.",
                    "request_id": request_id,
                },
                headers={"X-Request-ID": request_id},
            )
        )

    duration_ms = round((perf_counter() - started_at) * 1000, 1)
    response.headers["X-Request-ID"] = request_id
    apply_browser_security_headers(response)
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


protected_api_dependencies = [Depends(get_current_user)]

app.include_router(
    capture_router,
    dependencies=protected_api_dependencies,
)
app.include_router(
    candidate_sites_router,
    dependencies=protected_api_dependencies,
)
app.include_router(
    mission_router,
    dependencies=protected_api_dependencies,
)
app.include_router(
    dashboard_router,
    dependencies=protected_api_dependencies,
)
app.include_router(
    sessions_router,
    dependencies=protected_api_dependencies,
)
app.include_router(
    objects_router,
    dependencies=protected_api_dependencies,
)
app.include_router(operator_router)
app.include_router(
    portfolio_router,
    dependencies=protected_api_dependencies,
)
app.include_router(
    recommendations_router,
    dependencies=protected_api_dependencies,
)
app.include_router(
    tonight_router,
    dependencies=protected_api_dependencies,
)
app.include_router(
    system_router,
    dependencies=protected_api_dependencies,
)
app.include_router(
    advisor_router,
    dependencies=protected_api_dependencies,
)
app.include_router(
    planner_router,
    dependencies=protected_api_dependencies,
)
app.include_router(
    schedule_router,
    dependencies=protected_api_dependencies,
)
app.include_router(auth_router)
app.include_router(
    hosted_account_router,
    dependencies=protected_api_dependencies,
)
app.include_router(landing_router)


@app.get("/health/live", include_in_schema=False)
def live_health():
    """Confirm that the Polaris web process is responding."""
    return {
        "status": "alive",
        "version": settings.VERSION,
    }


@app.get("/health/ready", include_in_schema=False)
def ready_health(db: Session = Depends(get_db)):
    """Confirm that Polaris can reach its operational database."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "version": settings.VERSION,
            },
        )
    return {
        "status": "ready",
        "version": settings.VERSION,
    }


@app.post(
    "/parse-fits",
    dependencies=protected_api_dependencies,
)
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


@app.post(
    "/ingest-fits",
    dependencies=protected_api_dependencies,
)
async def ingest_fits_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_tenant_db),
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

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
