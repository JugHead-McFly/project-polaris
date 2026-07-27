import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from zoneinfo import ZoneInfo

import astropy.units as u
from astroplan import Observer
from astropy.coordinates import (
    AltAz,
    EarthLocation,
    GeocentricTrueEcliptic,
    SkyCoord,
    get_body,
    get_sun,
)
from astropy.time import Time

from app.core.planning_context import ObservatoryContext
from app.core.planning_context import use_observatory_context
from app.data.targets import SOLAR_SYSTEM_TARGETS
from app.data.targets import TARGETS
from app.services.ephemeris_service import (
    get_ephemeris_coordinate_at,
    get_ephemeris_coordinates,
    is_ephemeris_target,
)


def _get_location(
    observatory: Optional[ObservatoryContext] = None,
) -> EarthLocation:
    context = use_observatory_context(observatory)
    return EarthLocation(
        lat=context.latitude * u.deg,
        lon=context.longitude * u.deg,
        height=context.elevation_meters * u.m,
    )


def _get_observer(
    observatory: Optional[ObservatoryContext] = None,
) -> Observer:
    context = use_observatory_context(observatory)
    return Observer(
        location=_get_location(context),
        timezone=context.timezone_name,
    )


def _moon_phase_name(phase_angle_degrees: float) -> str:
    phase_angle = phase_angle_degrees % 360

    if phase_angle < 22.5 or phase_angle >= 337.5:
        return "New Moon"
    if phase_angle < 67.5:
        return "Waxing Crescent"
    if phase_angle < 112.5:
        return "First Quarter"
    if phase_angle < 157.5:
        return "Waxing Gibbous"
    if phase_angle < 202.5:
        return "Full Moon"
    if phase_angle < 247.5:
        return "Waning Gibbous"
    if phase_angle < 292.5:
        return "Last Quarter"
    return "Waning Crescent"


def get_target(
    target_name: str,
) -> Optional[Dict]:
    return TARGETS.get(
        target_name.strip().upper()
    )


def normalize_datetime(
    observation_datetime: Optional[datetime] = None,
    observatory: Optional[ObservatoryContext] = None,
) -> datetime:
    context = use_observatory_context(observatory)
    if observation_datetime is None:
        return datetime.now(timezone.utc)

    if observation_datetime.tzinfo is None:
        return observation_datetime.replace(
            tzinfo=ZoneInfo(context.timezone_name)
        )

    return observation_datetime


def to_astropy_time(
    observation_datetime: Optional[datetime] = None,
    observatory: Optional[ObservatoryContext] = None,
) -> Time:
    normalized = normalize_datetime(
        observation_datetime,
        observatory=observatory,
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
    observatory: Optional[ObservatoryContext] = None,
) -> Optional[SkyCoord]:
    normalized_name = target_name.strip().upper()
    solar_system_body = SOLAR_SYSTEM_TARGETS.get(
        normalized_name
    )

    if solar_system_body is not None:
        return get_body(
            solar_system_body,
            to_astropy_time(
                observation_datetime,
                observatory=observatory,
            ),
            _get_location(observatory),
        )

    if is_ephemeris_target(normalized_name):
        return get_ephemeris_coordinate_at(
            target_name=normalized_name,
            observation_datetime=observation_datetime,
            observatory=observatory,
        )

    return get_target_coordinate(normalized_name)


def _altitude_from_coordinate(
    coordinate: SkyCoord,
    observation_datetime: datetime,
    observatory: Optional[ObservatoryContext] = None,
) -> float:
    observation_time = to_astropy_time(
        observation_datetime,
        observatory=observatory,
    )
    altaz_frame = AltAz(
        obstime=observation_time,
        location=_get_location(observatory),
    )
    altitude = coordinate.transform_to(
        altaz_frame
    ).alt.deg

    return round(float(altitude), 1)


def get_altitudes_at(
    target_name: str,
    observation_datetimes: list,
    observatory: Optional[ObservatoryContext] = None,
) -> list:
    if is_ephemeris_target(target_name):
        coordinates = get_ephemeris_coordinates(
            target_name=target_name,
            observation_times=observation_datetimes,
            observatory=observatory,
        )
    else:
        coordinates = [
            get_target_coordinate_at(
                target_name=target_name,
                observation_datetime=observation_datetime,
                observatory=observatory,
            )
            for observation_datetime in observation_datetimes
        ]

    return [
        (
            _altitude_from_coordinate(
                coordinate=coordinate,
                observation_datetime=observation_datetime,
                observatory=observatory,
            )
            if coordinate is not None
            else None
        )
        for coordinate, observation_datetime in zip(
            coordinates,
            observation_datetimes,
        )
    ]


def get_altitude_at(
    target_name: str,
    observation_datetime: datetime,
    observatory: Optional[ObservatoryContext] = None,
) -> Optional[float]:
    return get_altitudes_at(
        target_name=target_name,
        observation_datetimes=[observation_datetime],
        observatory=observatory,
    )[0]


def get_altitude(
    target_name: str,
    observation_datetime: Optional[datetime] = None,
    observatory: Optional[ObservatoryContext] = None,
) -> Optional[float]:
    return get_altitude_at(
        target_name=target_name,
        observation_datetime=normalize_datetime(
            observation_datetime,
            observatory=observatory,
        ),
        observatory=observatory,
    )


def is_observable_at(
    target_name: str,
    observation_datetime: datetime,
    minimum_altitude: float = 20.0,
    observatory: Optional[ObservatoryContext] = None,
) -> bool:
    altitude = get_altitude_at(
        target_name=target_name,
        observation_datetime=observation_datetime,
        observatory=observatory,
    )

    if altitude is None:
        return False

    return altitude >= minimum_altitude


def is_observable(
    target_name: str,
    observation_datetime: Optional[datetime] = None,
    minimum_altitude: float = 20.0,
    observatory: Optional[ObservatoryContext] = None,
) -> bool:
    return is_observable_at(
        target_name=target_name,
        observation_datetime=normalize_datetime(
            observation_datetime,
            observatory=observatory,
        ),
        minimum_altitude=minimum_altitude,
        observatory=observatory,
    )


def get_transit_datetime(
    target_name: str,
    reference_datetime: Optional[datetime] = None,
    observatory: Optional[ObservatoryContext] = None,
) -> Optional[datetime]:
    context = use_observatory_context(observatory)
    normalized_reference = normalize_datetime(
        reference_datetime,
        observatory=context,
    )
    coordinate = get_target_coordinate_at(
        target_name=target_name,
        observation_datetime=normalized_reference,
        observatory=context,
    )

    if coordinate is None:
        return None

    reference_time = to_astropy_time(
        normalized_reference,
        observatory=context,
    )

    transit = (
        _get_observer(context).target_meridian_transit_time(
            reference_time,
            coordinate,
            which="next",
        )
    )

    return transit.to_datetime(
        timezone=ZoneInfo(context.timezone_name)
    )


def get_transit_time(
    target_name: str,
    reference_datetime: Optional[datetime] = None,
    observatory: Optional[ObservatoryContext] = None,
) -> Optional[str]:
    transit_datetime = get_transit_datetime(
        target_name=target_name,
        reference_datetime=reference_datetime,
        observatory=observatory,
    )

    if transit_datetime is None:
        return None

    return transit_datetime.strftime(
        "%Y-%m-%d %I:%M %p"
    )


def get_recommended_window(
    target_name: str,
    reference_datetime: Optional[datetime] = None,
    observatory: Optional[ObservatoryContext] = None,
) -> Dict:
    transit_datetime = get_transit_datetime(
        target_name=target_name,
        reference_datetime=reference_datetime,
        observatory=observatory,
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
    observatory: Optional[ObservatoryContext] = None,
) -> Dict:
    location = _get_location(observatory)
    observation_time = to_astropy_time(
        observation_datetime,
        observatory=observatory,
    )

    moon = get_body(
        "moon",
        observation_time,
        location,
    )

    moon_altaz = moon.transform_to(
        AltAz(
            obstime=observation_time,
            location=location,
        )
    )

    moon_altitude = float(
        moon_altaz.alt.deg
    )

    sun = get_sun(
        observation_time
    )

    ecliptic_frame = GeocentricTrueEcliptic(
        equinox=observation_time,
    )
    moon_longitude = moon.transform_to(
        ecliptic_frame
    ).lon.deg
    sun_longitude = sun.transform_to(
        ecliptic_frame
    ).lon.deg
    phase_angle = (
        moon_longitude - sun_longitude
    ) % 360

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
        "phase_name": _moon_phase_name(phase_angle),
        "altitude_degrees": round(
            moon_altitude,
            1,
        ),
        "above_horizon": (
            moon_altitude > 0
        ),
    }


def get_moon_info(
    observatory: Optional[ObservatoryContext] = None,
) -> Dict:
    context = use_observatory_context(observatory)
    observer = _get_observer(context)
    now = datetime.now(timezone.utc)
    observation_time = to_astropy_time(
        now,
        observatory=context,
    )

    current_info = get_moon_info_at(
        now,
        observatory=context,
    )

    moonrise = observer.moon_rise_time(
        observation_time,
        which="next",
    )

    moonset = observer.moon_set_time(
        observation_time,
        which="next",
    )

    local_timezone = ZoneInfo(
        context.timezone_name
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
    observatory: Optional[ObservatoryContext] = None,
) -> Optional[float]:
    target_coordinate = get_target_coordinate_at(
        target_name=target_name,
        observation_datetime=observation_datetime,
        observatory=observatory,
    )

    if target_coordinate is None:
        return None

    observation_time = to_astropy_time(
        observation_datetime,
        observatory=observatory,
    )

    moon_coordinate = get_body(
        "moon",
        observation_time,
        _get_location(observatory),
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
    observatory: Optional[ObservatoryContext] = None,
) -> Optional[float]:
    return get_moon_separation_at(
        target_name=target_name,
        observation_datetime=normalize_datetime(
            observation_datetime,
            observatory=observatory,
        ),
        observatory=observatory,
    )


def get_moon_warning_at(
    target_name: str,
    observation_datetime: datetime,
    observatory: Optional[ObservatoryContext] = None,
) -> str:
    separation = get_moon_separation_at(
        target_name=target_name,
        observation_datetime=observation_datetime,
        observatory=observatory,
    )

    moon_info = get_moon_info_at(
        observation_datetime,
        observatory=observatory,
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
    observatory: Optional[ObservatoryContext] = None,
) -> str:
    return get_moon_warning_at(
        target_name=target_name,
        observation_datetime=normalize_datetime(
            observation_datetime,
            observatory=observatory,
        ),
        observatory=observatory,
    )


def get_darkness_window_datetimes(
    reference_datetime: Optional[datetime] = None,
    observatory: Optional[ObservatoryContext] = None,
) -> Tuple[datetime, datetime, datetime]:
    context = use_observatory_context(observatory)
    observer = _get_observer(context)
    reference_time = to_astropy_time(
        reference_datetime,
        observatory=context,
    )

    sun_altitude = float(
        observer.sun_altaz(
            reference_time
        ).alt.deg
    )

    if sun_altitude <= -18:
        astronomical_dusk = (
            observer
            .twilight_evening_astronomical(
                reference_time,
                which="previous",
            )
        )

        sunset = observer.sun_set_time(
            astronomical_dusk,
            which="previous",
        )

        astronomical_dawn = (
            observer
            .twilight_morning_astronomical(
                reference_time,
                which="next",
            )
        )

    else:
        astronomical_dusk = (
            observer
            .twilight_evening_astronomical(
                reference_time,
                which="next",
            )
        )

        sunset = observer.sun_set_time(
            astronomical_dusk,
            which="previous",
        )

        astronomical_dawn = (
            observer
            .twilight_morning_astronomical(
                astronomical_dusk,
                which="next",
            )
        )

    local_timezone = ZoneInfo(
        context.timezone_name
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
    observatory: Optional[ObservatoryContext] = None,
) -> Dict:
    (
        sunset_local,
        dusk_local,
        dawn_local,
    ) = get_darkness_window_datetimes(
        reference_datetime,
        observatory=observatory,
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
