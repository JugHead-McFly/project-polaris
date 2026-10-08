"""Authenticated, stateless geometry preview. No account or astronomy queries."""
import json

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, ValidationError

from app.core.obstruction_profile import Altitude, Azimuth, ObstructionProfile
from app.services.obstruction_service import interval_exclusion_reason
from app.services.planner_service import MINIMUM_ALTITUDE_DEGREES

router = APIRouter(prefix="/obstructions", tags=["Obstruction preview"])
MAX_PREVIEW_BYTES = 128 * 1024


class Probe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    azimuth_degrees: Azimuth
    altitude_degrees: Altitude


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile: ObstructionProfile
    probe: Probe


def _reject(status, detail):
    return HTTPException(status, detail, headers={"Cache-Control": "no-store"})


def _unique_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("Duplicate JSON field")
    return result


def _invalid_constant(_value):
    raise ValueError("Non-finite JSON number")


async def read_bounded_model(request: Request, model):
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        raise _reject(415, "Use a JSON profile and target-center direction.")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_PREVIEW_BYTES:
            raise _reject(413, "Profile preview is limited to 128 KiB.")
        body.extend(chunk)
    try:
        data = json.loads(body, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
        payload = model.model_validate(data)
    except ValidationError as error:
        # Never echo submitted profile values in validation responses.
        raise _reject(422, [{"loc": item["loc"], "msg": item["msg"]}
                                  for item in error.errors(include_input=False, include_context=False)]) from error
    except (ValueError, UnicodeError, RecursionError) as error:
        raise _reject(422, "Use valid JSON with unique fields and finite numbers.") from error

    return payload


@router.post("/preview")
async def preview(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    payload = await read_bounded_model(request, PreviewRequest)
    profile = payload.profile
    probe = payload.probe
    position = (probe.azimuth_degrees, probe.altitude_degrees)
    reason = interval_exclusion_reason(profile, position, position, MINIMUM_ALTITUDE_DEGREES)
    # Exact piecewise-linear knots, with both sides of north for the rectangular plot.
    azimuths = sorted({0.0, 360.0, *(point.azimuth_degrees for point in profile.horizon)})
    horizon = [{"azimuth_degrees": az, "altitude_degrees": profile.horizon_altitude(az)}
               for az in azimuths]
    sectors = []
    for sector in profile.sectors:
        start, end = sector.start_azimuth_degrees, sector.end_azimuth_degrees
        bounds = [(start, end)] if start < end else [(start, 360), (0, end)]
        for left, right in bounds:
            sectors.append({"start": left, "end": right,
                            "low": max(0, sector.minimum_altitude_degrees - profile.clearance_degrees),
                            "high": min(90, sector.maximum_altitude_degrees + profile.clearance_degrees)})
    return {
        "profile": profile.model_dump(),
        "horizon": horizon,
        "sectors": sectors,
        "minimum_altitude_degrees": MINIMUM_ALTITUDE_DEGREES,
        "probe": {**probe.model_dump(), "clear": reason is None, "reason": reason},
        "applied_to_tonight": False,
    }
