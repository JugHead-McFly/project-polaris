from datetime import datetime, timezone

from astropy.coordinates import AltAz
from astropy.coordinates import EarthLocation
from astropy.coordinates import SkyCoord
from astropy.time import Time
import astropy.units as u

from app.core.observatory import ELEVATION_METERS
from app.core.observatory import LATITUDE
from app.core.observatory import LONGITUDE
from app.data.targets import TARGETS
from astroplan import Observer
from zoneinfo import ZoneInfo
from app.core.observatory import TIMEZONE
from datetime import timedelta
from astropy.coordinates import get_body
from astropy.coordinates import get_sun


OBSERVATORY_LOCATION = EarthLocation(
    lat=LATITUDE * u.deg,
    lon=LONGITUDE * u.deg,
    height=ELEVATION_METERS * u.m,
)

OBSERVER = Observer(
    location=OBSERVATORY_LOCATION,
    timezone=TIMEZONE,
)


def get_target(target_name: str):
    return TARGETS.get(target_name)


from typing import Optional
def get_altitude(target_name: str) -> Optional[float]:
    target = get_target(target_name)

    if not target:
        return None

    coordinate = SkyCoord(
        target["ra"],
        target["dec"],
        frame="icrs",
    )

    observation_time = Time(datetime.now(timezone.utc))

    altaz_frame = AltAz(
        obstime=observation_time,
        location=OBSERVATORY_LOCATION,
    )

    altitude = coordinate.transform_to(altaz_frame).alt.deg

    return round(float(altitude), 1)


def is_observable(target_name: str) -> bool:
    altitude = get_altitude(target_name)

    if altitude is None:
        return False

    return altitude >= 20


def get_transit_time(target_name: str) -> Optional[str]:
    target = get_target(target_name)

    if not target:
        return None

    coordinate = SkyCoord(
        target["ra"],
        target["dec"],
        frame="icrs",
    )

    current_time = Time(datetime.now(timezone.utc))

    transit = OBSERVER.target_meridian_transit_time(
        current_time,
        coordinate,
        which="next",
    )

    local_datetime = transit.to_datetime(
        timezone=ZoneInfo(TIMEZONE)
    )

    return local_datetime.strftime("%Y-%m-%d %I:%M %p")

def get_recommended_window(target_name: str):
    transit_time = get_transit_time(target_name)

    if transit_time is None:
        return {
            "recommended_start": None,
            "recommended_end": None,
        }

    return {
        "recommended_start": "2 hours before transit",
        "recommended_end": "2 hours after transit",
    }

def get_recommended_window(target_name: str):
    target = get_target(target_name)

    if not target:
        return {
            "recommended_start": None,
            "recommended_end": None,
        }

    coordinate = SkyCoord(
        target["ra"],
        target["dec"],
        frame="icrs",
    )

    current_time = Time(datetime.now(timezone.utc))

    transit = OBSERVER.target_meridian_transit_time(
        current_time,
        coordinate,
        which="next",
    )

    transit_local = transit.to_datetime(
        timezone=ZoneInfo(TIMEZONE)
    )

    start_local = transit_local - timedelta(hours=2)
    end_local = transit_local + timedelta(hours=2)

    return {
        "recommended_start": start_local.strftime(
            "%Y-%m-%d %I:%M %p"
        ),
        "recommended_end": end_local.strftime(
            "%Y-%m-%d %I:%M %p"
        ),
    }

def get_moon_info():
    observation_time = Time(datetime.now(timezone.utc))

    moon = get_body(
        "moon",
        observation_time,
        OBSERVATORY_LOCATION,
    )
    moon_altaz = moon.transform_to(
    AltAz(
        obstime=observation_time,
        location=OBSERVATORY_LOCATION,
        )
    )

    moon_altitude = moon_altaz.alt.deg

    sun = get_sun(observation_time)

    elongation = moon.separation(sun).deg

    illumination = (
        1 - __import__("math").cos(
            __import__("math").radians(elongation)
        )
    ) / 2

    moonrise = OBSERVER.moon_rise_time(
        observation_time,
        which="next",
    )

    moonset = OBSERVER.moon_set_time(
        observation_time,
        which="next",
    )

    moonrise_local = moonrise.to_datetime(
        timezone=ZoneInfo(TIMEZONE)
    )

    moonset_local = moonset.to_datetime(
        timezone=ZoneInfo(TIMEZONE)
    )

    return {
    "illumination_percent": round(
        illumination * 100,
        1,
    ),
    "altitude_degrees": round(
        float(moon_altitude),
        1,
    ),
    "above_horizon": bool(moon_altitude > 0),
            "next_moonrise": moonrise_local.strftime(
            "%Y-%m-%d %I:%M %p"
        ),
        "next_moonset": moonset_local.strftime(
            "%Y-%m-%d %I:%M %p"
        ),
}

def get_moon_separation(target_name: str) -> Optional[float]:
    target = get_target(target_name)

    if not target:
        return None

    observation_time = Time(datetime.now(timezone.utc))

    target_coordinate = SkyCoord(
        target["ra"],
        target["dec"],
        frame="icrs",
    )

    moon_coordinate = get_body(
        "moon",
        observation_time,
        OBSERVATORY_LOCATION,
    )

    separation = target_coordinate.separation(
        moon_coordinate
    ).deg

    return round(float(separation), 1)

def get_moon_warning(target_name: str) -> str:
    separation = get_moon_separation(target_name)
    moon_info = get_moon_info()

    if separation is None:
        return "Unknown"

    illumination = moon_info["illumination_percent"]
    above_horizon = moon_info["above_horizon"]

    if not above_horizon:
        return "None — Moon is below the horizon."

    if illumination < 10:
        return "Minimal — Moon illumination is very low."

    if separation >= 60:
        return "None — Excellent Moon separation."

    if separation >= 30:
        return "Low — Minor Moon interference expected."

    if separation >= 20:
        return "Moderate — Some loss of contrast is possible."

    return "High — Moon is close and may reduce contrast."

def get_darkness_info():
    current_time = Time(datetime.now(timezone.utc))

    sunset = OBSERVER.sun_set_time(
        current_time,
        which="next",
    )

    astronomical_dusk = OBSERVER.twilight_evening_astronomical(
        current_time,
        which="next",
    )

    astronomical_dawn = OBSERVER.twilight_morning_astronomical(
        current_time,
        which="next",
    )

    sunset_local = sunset.to_datetime(
        timezone=ZoneInfo(TIMEZONE)
    )

    dusk_local = astronomical_dusk.to_datetime(
        timezone=ZoneInfo(TIMEZONE)
    )

    dawn_local = astronomical_dawn.to_datetime(
        timezone=ZoneInfo(TIMEZONE)
    )

    return {
        "sunset": sunset_local.strftime(
            "%Y-%m-%d %I:%M %p"
        ),
        "astronomical_darkness_start": dusk_local.strftime(
            "%Y-%m-%d %I:%M %p"
        ),
        "astronomical_darkness_end": dawn_local.strftime(
            "%Y-%m-%d %I:%M %p"
        ),
    }