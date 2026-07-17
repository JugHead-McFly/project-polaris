import csv
import io
import json
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import astropy.units as u
from astropy.coordinates import SkyCoord

from app.core.observatory import (
    ELEVATION_METERS,
    LATITUDE,
    LONGITUDE,
)
from app.data.targets import EPHEMERIS_TARGETS


HORIZONS_API_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
HORIZONS_TIMEOUT_SECONDS = 8
SUPPORTED_API_VERSIONS = {"1.2", "1.3"}

# Coordinates are immutable for an exact UTC instant. This process-local cache
# avoids repeated network calls during one planner run and is never persisted.
_coordinate_cache: Dict[Tuple[str, datetime], SkyCoord] = {}


def is_ephemeris_target(target_name: str) -> bool:
    return target_name.strip().upper() in EPHEMERIS_TARGETS


def clear_ephemeris_cache() -> None:
    _coordinate_cache.clear()


def _normalize_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Ephemeris times must include a timezone.")

    return value.astimezone(timezone.utc).replace(microsecond=0)


def _horizons_time(value: datetime) -> str:
    return _normalize_time(value).strftime("%Y-%b-%d %H:%M:%S")


def _build_horizons_url(
    command: str,
    observation_times: Iterable[datetime],
) -> str:
    time_list = " ".join(
        f"'{_horizons_time(value)}'"
        for value in observation_times
    )
    site_coordinates = (
        f"{LONGITUDE},{LATITUDE},{ELEVATION_METERS / 1000}"
    )
    params = {
        "format": "json",
        "COMMAND": f"'{command}'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'OBSERVER'",
        "CENTER": "'coord@399'",
        "COORD_TYPE": "'GEODETIC'",
        "SITE_COORD": f"'{site_coordinates}'",
        "TLIST": time_list,
        "TLIST_TYPE": "'CAL'",
        "TIME_TYPE": "'UT'",
        "TIME_DIGITS": "'FRACSEC'",
        "QUANTITIES": "'1'",
        "ANG_FORMAT": "'DEG'",
        "CSV_FORMAT": "'YES'",
        "EXTRA_PREC": "'YES'",
    }

    return HORIZONS_API_URL + "?" + urlencode(params)


def _validate_signature(payload: Dict) -> None:
    signature = payload.get("signature", {})

    if signature.get("source") != "NASA/JPL Horizons API":
        raise ValueError("Unexpected ephemeris source.")

    if signature.get("version") not in SUPPORTED_API_VERSIONS:
        raise ValueError("Unsupported Horizons API response version.")


def _parse_horizons_result(result: str) -> Dict[datetime, SkyCoord]:
    if "$$SOE" not in result or "$$EOE" not in result:
        raise ValueError("Horizons response did not contain ephemeris data.")

    table = result.split("$$SOE", 1)[1].split("$$EOE", 1)[0]
    coordinates = {}

    for row in csv.reader(io.StringIO(table)):
        fields = [field.strip() for field in row]
        if not fields or not fields[0]:
            continue

        numeric_fields = []
        for field in fields[1:]:
            try:
                numeric_fields.append(float(field))
            except ValueError:
                continue

        if len(numeric_fields) < 2:
            continue

        observation_time = datetime.strptime(
            fields[0],
            "%Y-%b-%d %H:%M:%S.%f",
        ).replace(tzinfo=timezone.utc)
        right_ascension, declination = numeric_fields[-2:]
        coordinates[_normalize_time(observation_time)] = SkyCoord(
            right_ascension * u.deg,
            declination * u.deg,
            frame="icrs",
        )

    if not coordinates:
        raise ValueError("Horizons returned an empty ephemeris table.")

    return coordinates


def _fetch_coordinates(
    command: str,
    observation_times: List[datetime],
) -> Dict[datetime, SkyCoord]:
    url = _build_horizons_url(
        command=command,
        observation_times=observation_times,
    )
    request = Request(
        url,
        headers={"User-Agent": "Project-Polaris/0.5"},
    )

    with urlopen(
        request,
        timeout=HORIZONS_TIMEOUT_SECONDS,
    ) as response:
        payload = json.load(response)

    _validate_signature(payload)
    return _parse_horizons_result(payload.get("result", ""))


def get_ephemeris_coordinates(
    target_name: str,
    observation_times: Iterable[datetime],
) -> List[Optional[SkyCoord]]:
    normalized_name = target_name.strip().upper()
    command = EPHEMERIS_TARGETS.get(normalized_name)
    normalized_times = [
        _normalize_time(value)
        for value in observation_times
    ]

    if command is None or not normalized_times:
        return [None for _ in normalized_times]

    missing_times = list(
        dict.fromkeys(
            value
            for value in normalized_times
            if (normalized_name, value) not in _coordinate_cache
        )
    )

    if missing_times:
        try:
            fetched = _fetch_coordinates(
                command=command,
                observation_times=missing_times,
            )
        except (URLError, TimeoutError, OSError, ValueError, KeyError):
            fetched = {}

        for observation_time, coordinate in fetched.items():
            _coordinate_cache[(normalized_name, observation_time)] = coordinate

    return [
        _coordinate_cache.get((normalized_name, value))
        for value in normalized_times
    ]


def get_ephemeris_coordinate_at(
    target_name: str,
    observation_datetime: datetime,
) -> Optional[SkyCoord]:
    return get_ephemeris_coordinates(
        target_name=target_name,
        observation_times=[observation_datetime],
    )[0]
