"""Read-only horizontal-coordinate view; never changes a plan or stored home."""
import math
from datetime import datetime, timezone
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Request, Response, HTTPException
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, field_validator
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.obstructions import read_bounded_model
from app.core.auth import CurrentUser, get_current_user
from app.core.planning_context import ObservatoryContext
from app.data.targets import TARGETS, SOLAR_SYSTEM_TARGETS
from app.database.database import get_tenant_db
from app.services.astronomy_service import get_horizontal_positions_at
from app.services.hosted_account_service import get_planning_context, MissingObservatoryError

router = APIRouter(prefix="/sky-view", tags=["Read-only sky view"])
CATALOG = {**{key: value["name"] for key, value in TARGETS.items()},
           **{key: key.title() for key in SOLAR_SYSTEM_TARGETS}}


class ViewLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    latitude: Annotated[float, Field(strict=True, ge=-90, le=90, allow_inf_nan=False)]
    longitude: Annotated[float, Field(strict=True, ge=-180, le=180, allow_inf_nan=False)]
    elevation_meters: Annotated[float, Field(strict=True, ge=-500, le=9000, allow_inf_nan=False)] = 0
    timezone_name: str = Field(max_length=64)

    @field_validator("timezone_name")
    @classmethod
    def valid_zone(cls, value):
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError) as error:
            raise ValueError("Use an IANA timezone, such as UTC or America/Phoenix") from error
        return value


class SkyViewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    at: AwareDatetime
    location: ViewLocation
    targets: list[str] = Field(min_length=1, max_length=12)

    @field_validator("at", mode="before")
    @classmethod
    def explicit_instant(cls, value):
        if not isinstance(value, (str, datetime)):
            raise ValueError("Use an ISO datetime with an explicit UTC offset")
        return value

    @field_validator("at")
    @classmethod
    def supported_date(cls, value):
        try:
            utc_year = value.astimezone(timezone.utc).year
        except (OverflowError, ValueError) as error:
            raise ValueError("Datetime is outside the supported UTC range") from error
        if not 2000 <= utc_year <= 2100:
            raise ValueError("Prototype dates must be between 2000 and 2100")
        return value

    @field_validator("targets")
    @classmethod
    def known_unique_targets(cls, values):
        names = [value.strip().upper() for value in values]
        if len(set(names)) != len(names) or any(name not in CATALOG for name in names):
            raise ValueError("Choose unique targets from the sky-view catalog")
        return names


def calculate_view(payload: SkyViewRequest):
    instant = payload.at.astimezone(timezone.utc)
    context = ObservatoryContext(name="Sky-view input", **payload.location.model_dump())
    rows = []
    for name in payload.targets:
        try:
            position = get_horizontal_positions_at(name, [instant], observatory=context)[0]
        except (ValueError, TypeError, IndexError, RuntimeError):
            position = None
        if position is None or not all(math.isfinite(value) for value in position):
            rows.append({"id": name, "name": CATALOG[name], "status": "unavailable",
                         "azimuth_degrees": None, "altitude_degrees": None})
            continue
        azimuth, altitude = float(position[0]) % 360, float(position[1])
        if not -90 <= altitude <= 90:
            rows.append({"id": name, "name": CATALOG[name], "status": "unavailable",
                         "azimuth_degrees": None, "altitude_degrees": None})
            continue
        rows.append({"id": name, "name": CATALOG[name],
                     "status": "below_horizon" if altitude < 0 else "above_horizon",
                     "azimuth_degrees": azimuth, "altitude_degrees": altitude})
    return {"at_utc": instant.isoformat(),
            "at_local": instant.astimezone(ZoneInfo(context.timezone_name)).isoformat(),
            "location": payload.location.model_dump(), "targets": rows,
            "coordinate_system": "true-north azimuth clockwise; geometric elevation above level",
            "applied_to_tonight": False,
            "limits": "Calculated target centers, not full-frame or imaging suitability. No refraction or photographic calibration. Landscape confidence is independent."}


@router.get("/catalog")
def catalog(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return [{"id": key, "name": value} for key, value in sorted(CATALOG.items())]


@router.get("/home")
def home(response: Response, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_tenant_db)):
    response.headers["Cache-Control"] = "no-store"
    try:
        context = get_planning_context(db, current_user=user)
    except MissingObservatoryError as error:
        raise HTTPException(409, "Add an observing home, or enter a location for this view.") from error
    return {"latitude": context.latitude, "longitude": context.longitude,
            "elevation_meters": context.elevation_meters, "timezone_name": context.timezone_name}


@router.post("/positions")
async def positions(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    payload = await read_bounded_model(request, SkyViewRequest)
    return await run_in_threadpool(calculate_view, payload)
