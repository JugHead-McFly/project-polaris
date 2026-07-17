import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from zoneinfo import ZoneInfo

import astropy.units as u
from astroplan import Observer
from astropy.coordinates import (
    AltAz,
    EarthLocation,
    SkyCoord,
    get_body,
    get_sun,
)
from astropy.time import Time

from app.core.observatory import (
    ELEVATION_METERS,
    LATITUDE,
    LONGITUDE,
    TIMEZONE,
)
from app.data.targets import SOLAR_SYSTEM_TARGETS
from app.data.targets import TARGETS


OBSERVATORY_LOCATION = EarthLocation(
    lat=LATITUDE * u.deg,
    lon=LONGITUDE * u.deg,
    height=ELEVATION_METERS * u.m,
)

OBSERVER = Observer(
    location=OBSERVATORY_LOCATION,
    timezone=TIMEZONE,
)


def get_target(
    target_name: str,
) -> Optional[Dict]:
    return TARGETS.get(
        target_name.strip().upper()
    )


def normalize_datetime(
    observation_datetime: Optional[datetime] = None,
) -> datetime:
    if observation_datetime is None:
        return datetime.now(timezone.utc)

    if observation_datetime.tzinfo is None:
        return observation_datetime.replace(
            tzinfo=ZoneInfo(TIMEZONE)
        )

    return observation_datetime


def to_astropy_time(
    observation_datetime: Optional[datetime] = None,
) -> Time:
    normalized = normalize_datetime(
        observation_datetime
    )

    return Time(
        normalized.astimezone(timezone.utc)
    )


def get_target_coordinate(
    target_name: str,
) -> Optional[SkyCoord]:
    target = get_target(target_name)

    if target is None:
        return None

    return SkyCoord(
        target["ra"],
        target["dec"],
        frame="icrs",
    )


def get_target_coordinate_at(
    target_name: str,
    observation_datetime: datetime,
) -> Optional[SkyCoord]:
    normalized_name = target_name.strip().upper()
    solar_system_body = SOLAR_SYSTEM_TARGETS.get(
        normalized_name
    )

    if solar_system_body is not None:
        return get_body(
            solar_system_body,
            to_astropy_time(observation_datetime),
            OBSERVATORY_LOCATION,
        )

    return get_target_coordinate(normalized_name)


def get_altitude_at(
    target_name: str,
    observation_datetime: datetime,
) -> Optional[float]:
    coordinate = get_target_coordinate_at(
        target_name=target_name,
        observation_datetime=observation_datetime,
    )

    if coordinate is None:
        return None

    observation_time = to_astropy_time(
        observation_datetime
    )

    altaz_frame = AltAz(
        obstime=observation_time,
        location=OBSERVATORY_LOCATION,
    )

    altitude = coordinate.transform_to(
        altaz_frame
    ).alt.deg

    return round(
        float(altitude),
        1,
    )


def get_altitude(
    target_name: str,
    observation_datetime: Optional[datetime] = None,
) -> Optional[float]:
    return get_altitude_at(
        target_name=target_name,
        observation_datetime=normalize_datetime(
            observation_datetime
        ),
    )


def is_observable_at(
    target_name: str,
    observation_datetime: datetime,
    minimum_altitude: float = 20.0,
) -> bool:
    altitude = get_altitude_at(
        target_name=target_name,
        observation_datetime=observation_datetime,
    )

    if altitude is None:
        return False

    return altitude >= minimum_altitude


def is_observable(
    target_name: str,
    observation_datetime: Optional[datetime] = None,
    minimum_altitude: float = 20.0,
) -> bool:
    return is_observable_at(
        target_name=target_name,
        observation_datetime=normalize_datetime(
            observation_datetime
        ),
        minimum_altitude=minimum_altitude,
    )


def get_transit_datetime(
    target_name: str,
    reference_datetime: Optional[datetime] = None,
) -> Optional[datetime]:
    normalized_reference = normalize_datetime(
        reference_datetime
    )
    coordinate = get_target_coordinate_at(
        target_name=target_name,
        observation_datetime=normalized_reference,
    )

    if coordinate is None:
        return None

    reference_time = to_astropy_time(
        normalized_reference
    )

    transit = (
        OBSERVER.target_meridian_transit_time(
            reference_time,
            coordinate,
            which="next",
        )
    )

    return transit.to_datetime(
        timezone=ZoneInfo(TIMEZONE)
    )


def get_transit_time(
    target_name: str,
    reference_datetime: Optional[datetime] = None,
) -> Optional[str]:
    transit_datetime = get_transit_datetime(
        target_name=target_name,
        reference_datetime=reference_datetime,
    )

    if transit_datetime is None:
        return None

    return transit_datetime.strftime(
        "%Y-%m-%d %I:%M %p"
    )


def get_recommended_window(
    target_name: str,
    reference_datetime: Optional[datetime] = None,
) -> Dict:
    transit_datetime = get_transit_datetime(
        target_name=target_name,
        reference_datetime=reference_datetime,
    )

    if transit_datetime is None:
        return {
            "recommended_start": None,
            "recommended_end": None,
        }

    start_local = (
        transit_datetime
        - timedelta(hours=2)
    )

    end_local = (
        transit_datetime
        + timedelta(hours=2)
    )

    return {
        "recommended_start": (
            start_local.strftime(
                "%Y-%m-%d %I:%M %p"
            )
        ),
        "recommended_end": (
            end_local.strftime(
                "%Y-%m-%d %I:%M %p"
            )
        ),
    }


def get_moon_info_at(
    observation_datetime: datetime,
) -> Dict:
    observation_time = to_astropy_time(
        observation_datetime
    )

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

    moon_altitude = float(
        moon_altaz.alt.deg
    )

    sun = get_sun(
        observation_time
    )

    elongation = moon.separation(
        sun
    ).deg

    illumination = (
        1
        - math.cos(
            math.radians(elongation)
        )
    ) / 2

    return {
        "illumination_percent": round(
            illumination * 100,
            1,
        ),
        "altitude_degrees": round(
            moon_altitude,
            1,
        ),
        "above_horizon": (
            moon_altitude > 0
        ),
    }


def get_moon_info() -> Dict:
    now = datetime.now(timezone.utc)
    observation_time = to_astropy_time(now)

    current_info = get_moon_info_at(
        now
    )

    moonrise = OBSERVER.moon_rise_time(
        observation_time,
        which="next",
    )

    moonset = OBSERVER.moon_set_time(
        observation_time,
        which="next",
    )

    local_timezone = ZoneInfo(
        TIMEZONE
    )

    moonrise_local = moonrise.to_datetime(
        timezone=local_timezone
    )

    moonset_local = moonset.to_datetime(
        timezone=local_timezone
    )

    return {
        **current_info,
        "next_moonrise": (
            moonrise_local.strftime(
                "%Y-%m-%d %I:%M %p"
            )
        ),
        "next_moonset": (
            moonset_local.strftime(
                "%Y-%m-%d %I:%M %p"
            )
        ),
    }


def get_moon_separation_at(
    target_name: str,
    observation_datetime: datetime,
) -> Optional[float]:
    target_coordinate = get_target_coordinate_at(
        target_name=target_name,
        observation_datetime=observation_datetime,
    )

    if target_coordinate is None:
        return None

    observation_time = to_astropy_time(
        observation_datetime
    )

    moon_coordinate = get_body(
        "moon",
        observation_time,
        OBSERVATORY_LOCATION,
    )

    separation = target_coordinate.separation(
        moon_coordinate
    ).deg

    return round(
        float(separation),
        1,
    )


def get_moon_separation(
    target_name: str,
    observation_datetime: Optional[datetime] = None,
) -> Optional[float]:
    return get_moon_separation_at(
        target_name=target_name,
        observation_datetime=normalize_datetime(
            observation_datetime
        ),
    )


def get_moon_warning_at(
    target_name: str,
    observation_datetime: datetime,
) -> str:
    separation = get_moon_separation_at(
        target_name=target_name,
        observation_datetime=observation_datetime,
    )

    moon_info = get_moon_info_at(
        observation_datetime
    )

    if separation is None:
        return "Unknown"

    illumination = moon_info[
        "illumination_percent"
    ]

    above_horizon = moon_info[
        "above_horizon"
    ]

    if not above_horizon:
        return (
            "None — Moon is below the horizon."
        )

    if illumination < 10:
        return (
            "Minimal — Moon illumination is very low."
        )

    if separation >= 60:
        return (
            "None — Excellent Moon separation."
        )

    if separation >= 30:
        return (
            "Low — Minor Moon interference expected."
        )

    if separation >= 20:
        return (
            "Moderate — Some loss of contrast is possible."
        )

    return (
        "High — Moon is close and may reduce contrast."
    )


def get_moon_warning(
    target_name: str,
    observation_datetime: Optional[datetime] = None,
) -> str:
    return get_moon_warning_at(
        target_name=target_name,
        observation_datetime=normalize_datetime(
            observation_datetime
        ),
    )


def get_darkness_window_datetimes(
    reference_datetime: Optional[datetime] = None,
) -> Tuple[datetime, datetime, datetime]:
    reference_time = to_astropy_time(
        reference_datetime
    )

    sun_altitude = float(
        OBSERVER.sun_altaz(
            reference_time
        ).alt.deg
    )

    if sun_altitude <= -18:
        astronomical_dusk = (
            OBSERVER
            .twilight_evening_astronomical(
                reference_time,
                which="previous",
            )
        )

        sunset = OBSERVER.sun_set_time(
            astronomical_dusk,
            which="previous",
        )

        astronomical_dawn = (
            OBSERVER
            .twilight_morning_astronomical(
                reference_time,
                which="next",
            )
        )

    else:
        astronomical_dusk = (
            OBSERVER
            .twilight_evening_astronomical(
                reference_time,
                which="next",
            )
        )

        sunset = OBSERVER.sun_set_time(
            astronomical_dusk,
            which="previous",
        )

        astronomical_dawn = (
            OBSERVER
            .twilight_morning_astronomical(
                astronomical_dusk,
                which="next",
            )
        )

    local_timezone = ZoneInfo(
        TIMEZONE
    )

    sunset_local = sunset.to_datetime(
        timezone=local_timezone
    )

    dusk_local = (
        astronomical_dusk.to_datetime(
            timezone=local_timezone
        )
    )

    dawn_local = (
        astronomical_dawn.to_datetime(
            timezone=local_timezone
        )
    )

    return (
        sunset_local,
        dusk_local,
        dawn_local,
    )


def get_darkness_info(
    reference_datetime: Optional[datetime] = None,
) -> Dict:
    (
        sunset_local,
        dusk_local,
        dawn_local,
    ) = get_darkness_window_datetimes(
        reference_datetime
    )

    return {
        "sunset": sunset_local.strftime(
            "%Y-%m-%d %I:%M %p"
        ),
        "astronomical_darkness_start": (
            dusk_local.strftime(
                "%Y-%m-%d %I:%M %p"
            )
        ),
        "astronomical_darkness_end": (
            dawn_local.strftime(
                "%Y-%m-%d %I:%M %p"
            )
        ),
    }
