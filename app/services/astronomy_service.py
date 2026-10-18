import math
import numpy as np
from functools import lru_cache
from app.core.calculation_cache import reuse_exact, reuse_altitude_samples, calculation_scope_active
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
from app.services.deep_sky_catalog import get_entry
from app.services.ephemeris_service import (
    get_ephemeris_coordinate_at,
    get_ephemeris_coordinates,
    is_ephemeris_target,
)


from app.core.request_timing import timed

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
    return TARGETS.get(target_name.strip().upper()) or get_entry(target_name)


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

    ra, dec = target["ra"], target["dec"]
    if isinstance(ra, str) and isinstance(dec, str):
        # Public static catalog coordinates only. Value keys invalidate changed
        # catalog entries immediately; copies prevent cross-caller mutation.
        return _fixed_catalog_coordinate(ra, dec).copy()
    return SkyCoord(ra, dec, frame="icrs")


@lru_cache(maxsize=512)
def _fixed_catalog_coordinate(ra, dec):
    return SkyCoord(ra, dec, frame="icrs")


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


@timed("altitude_series")
@reuse_altitude_samples
@timed("altitude_compute")
def get_altitudes_at(
    target_name: str,
    observation_datetimes: list,
    observatory: Optional[ObservatoryContext] = None,
) -> list:
    if not observation_datetimes:
        return []
    normalized_name = target_name.strip().upper()
    # A fixed deep-sky coordinate broadcasts over all sample times in one
    # Astropy transform. Keep moving/ephemeris targets on their existing path.
    if normalized_name not in SOLAR_SYSTEM_TARGETS and not is_ephemeris_target(normalized_name):
        coordinate = get_target_coordinate(normalized_name)
        if coordinate is None:
            return [None] * len(observation_datetimes)
        times = Time([normalize_datetime(value, observatory).astimezone(timezone.utc)
                      for value in observation_datetimes])
        altitudes = coordinate.transform_to(AltAz(obstime=times,
            location=_get_location(observatory))).alt.deg
        return [round(float(value), 1) for value in altitudes]
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


@timed("altitude_common_grid")
def prepare_fixed_target_altitudes(target_names, observation_datetimes, observatory=None):
    """Seed only the exact shared samples; current times/refinements stay lazy.

    Broadcast fixed coordinates across the original Astropy time grid. Moving
    and unknown targets retain their scalar paths. Bound matrix size for callers
    supplying larger candidate pools; results live only in this calculation.
    """
    if not calculation_scope_active() or not observation_datetimes:
        return
    context = use_observatory_context(observatory)
    times = list(observation_datetimes)
    astropy_times = Time([normalize_datetime(at, context).astimezone(timezone.utc) for at in times])
    frame = AltAz(obstime=astropy_times, location=_get_location(context))
    names, coordinates = [], []
    for name in dict.fromkeys(target_names):
        normalized = name.strip().upper()
        if normalized in SOLAR_SYSTEM_TARGETS or is_ephemeris_target(normalized):
            continue
        try:
            coordinate = get_target_coordinate(normalized)
        except ValueError:
            # Leave invalid coordinates to the existing per-target error path.
            continue
        if coordinate is not None:
            names.append(name)
            coordinates.append(coordinate)
        if len(names) == 64:
            _seed_fixed_altitude_chunk(names, coordinates, times, frame, observatory)
            names, coordinates = [], []
    if names:
        _seed_fixed_altitude_chunk(names, coordinates, times, frame, observatory)


def _seed_fixed_altitude_chunk(names, coordinates, times, frame, context):
    altitudes = SkyCoord(coordinates).reshape(-1, 1).transform_to(frame).alt.deg
    for name, row in zip(names, altitudes):
        get_altitudes_at.seed_exact_samples(name, times,
            [round(float(value), 1) for value in row], context)


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
    # Resolve an implicit "now" before cache lookup; None is not an instant.
    reference = normalize_datetime(reference_datetime, observatory=context)
    return _get_transit_datetime_at(target_name, reference, context)


@reuse_exact
@timed("transit")
def _get_transit_datetime_at(target_name, reference_datetime, observatory):
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


@timed("transit_batch")
def prepare_fixed_target_transits(target_names, reference_datetime, observatory=None):
    """Use Astroplan's identical time grid, broadcasting only fixed coordinates."""
    context = use_observatory_context(observatory)
    names, coordinates = [], []
    for name in target_names:
        normalized = name.strip().upper()
        if normalized in SOLAR_SYSTEM_TARGETS or is_ephemeris_target(normalized):
            continue
        coordinate = get_target_coordinate(normalized)
        if coordinate is not None:
            names.append(name)
            coordinates.append(coordinate)
    if not names:
        return
    # Shape (1, M) broadcasts with Astroplan's (N, 1) time grid. Explicit
    # grid_times_targets=True uses a different axis convention in Astroplan.
    transits = _get_observer(context).target_meridian_transit_time(
        to_astropy_time(reference_datetime, context),
        SkyCoord(coordinates).reshape(1, -1), which="next",
    ).to_datetime(timezone=ZoneInfo(context.timezone_name))
    for name, result in zip(names, np.atleast_1d(transits)):
        _get_transit_datetime_at.seed_exact_result(result, name,
            reference_datetime=normalize_datetime(reference_datetime, context), observatory=context)


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


@reuse_exact
def _moon_coordinate_at(observation_datetime, observatory=None):
    return get_body("moon", to_astropy_time(observation_datetime, observatory=observatory),
                    _get_location(observatory))


@reuse_exact
@timed("moon_current")
def get_moon_info_at(
    observation_datetime: datetime,
    observatory: Optional[ObservatoryContext] = None,
) -> Dict:
    location = _get_location(observatory)
    observation_time = to_astropy_time(
        observation_datetime,
        observatory=observatory,
    )

    moon = _moon_coordinate_at(observation_datetime, observatory)

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


@timed("moon")
def get_moon_info(
    observatory: Optional[ObservatoryContext] = None,
) -> Dict:
    context = use_observatory_context(observatory)
    now = datetime.now(timezone.utc)
    observation_time = to_astropy_time(
        now,
        observatory=context,
    )

    current_info = get_moon_info_at(
        now,
        observatory=context,
    )

    moonrise, moonset = _next_moon_events(context, observation_time)

    local_timezone = ZoneInfo(
        context.timezone_name
    )

    moonrise_local = None if bool(moonrise.mask) else moonrise.to_datetime(
        timezone=local_timezone
    )

    moonset_local = None if bool(moonset.mask) else moonset.to_datetime(
        timezone=local_timezone
    )

    return {
        **current_info,
        "next_moonrise": (
            moonrise_local.strftime(
                "%Y-%m-%d %I:%M %p"
            ) if moonrise_local is not None else None
        ),
        "next_moonset": (
            moonset_local.strftime(
                "%Y-%m-%d %I:%M %p"
            ) if moonset_local is not None else None
        ),
    }


@timed("moon_rise")
def _next_moonrise(observer, observation_time):
    return observer.moon_rise_time(
        observation_time,
        which="next",
    )


@timed("moon_set")
def _next_moonset(observer, observation_time):
    return observer.moon_set_time(
        observation_time,
        which="next",
    )


@reuse_exact
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

    moon_coordinate = _moon_coordinate_at(observation_datetime, observatory)

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
) -> Tuple[Optional[datetime], Optional[datetime], Optional[datetime]]:
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
        if bool(astronomical_dusk.mask):
            return None, None, None

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
        if bool(astronomical_dusk.mask):
            return None, None, None

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

    if bool(astronomical_dawn.mask):
        return None, None, None

    sunset_local = None if bool(sunset.mask) else sunset.to_datetime(
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
    elapsed = dawn_local.astimezone(timezone.utc) - dusk_local.astimezone(timezone.utc)
    if not timedelta(0) < elapsed <= timedelta(hours=24):
        return None, None, None

    return (
        sunset_local,
        dusk_local,
        dawn_local,
    )


@timed("darkness")
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
        ) if sunset_local is not None else None,
        "astronomical_darkness_start": (
            dusk_local.strftime(
                "%Y-%m-%d %I:%M %p"
            ) if dusk_local is not None else None
        ),
        "astronomical_darkness_end": (
            dawn_local.strftime(
                "%Y-%m-%d %I:%M %p"
            ) if dawn_local is not None else None
        ),
        "astronomical_darkness_start_at": dusk_local.isoformat() if dusk_local is not None else None,
        "astronomical_darkness_end_at": dawn_local.isoformat() if dawn_local is not None else None,
    }

@timed("geometry_details_batch")
def prepare_fixed_target_details(target_names, *, coarse_times, midpoint,
                                 minimum_altitude, observatory=None):
    """Prepare exact refinements and midpoint Moon separation in bounded chunks.

    No current-time sample is created here. Unsupported/invalid targets and
    failed optimization chunks retain the existing per-target calculation path.
    """
    if not calculation_scope_active() or not coarse_times or len(coarse_times) > 4096:
        return
    names, coordinates = [], []
    for name in target_names:
        normalized = name.strip().upper()
        if normalized in SOLAR_SYSTEM_TARGETS or is_ephemeris_target(normalized):
            continue
        try:
            coordinate = get_target_coordinate(normalized)
        except ValueError:
            continue
        if coordinate is None:
            continue
        names.append(name)
        coordinates.append(coordinate)
        if len(names) == 64:
            _prepare_detail_chunk(names, coordinates, coarse_times, midpoint,
                                  minimum_altitude, observatory)
            names, coordinates = [], []
    if names:
        _prepare_detail_chunk(names, coordinates, coarse_times, midpoint,
                              minimum_altitude, observatory)


def _prepare_detail_chunk(names, coordinates, coarse_times, midpoint,
                          minimum_altitude, observatory):
    from app.services.astronomy_samples import threshold_refinement_times
    try:
        coordinate_array = SkyCoord(coordinates)
    except ValueError:
        return
    pairs, indices = [], []
    for index, name in enumerate(names):
        try:
            altitudes = get_altitudes_at(name, coarse_times, observatory)
        except ValueError:
            continue
        if any(value is None or not math.isfinite(value) for value in altitudes):
            continue
        if not any(value >= minimum_altitude for value in altitudes):
            continue
        for at in threshold_refinement_times(coarse_times, altitudes, minimum_altitude):
            pairs.append((name, at))
            indices.append(index)
            if len(pairs) == 512:
                _seed_refinement_pairs(coordinate_array, indices, pairs, observatory)
                pairs, indices = [], []
    if pairs:
        _seed_refinement_pairs(coordinate_array, indices, pairs, observatory)
    try:
        values = coordinate_array.separation(_moon_coordinate_at(midpoint, observatory)).deg
        results = [round(float(value), 1) for value in values]
    except ValueError:
        return
    for name, result in zip(names, results):
        if math.isfinite(result):
            get_moon_separation_at.seed_exact_result(result, name, midpoint, observatory)


def _seed_refinement_pairs(coordinates, indices, pairs, observatory):
    try:
        frame = AltAz(
            obstime=Time([normalize_datetime(at, observatory).astimezone(timezone.utc)
                          for _, at in pairs]), location=_get_location(observatory))
        values = coordinates[indices].transform_to(frame).alt.deg
        results = [round(float(value), 1) for value in values]
    except ValueError:
        # Do not replace a failed optimization with synthetic geometry.
        return
    for (name, at), result in zip(pairs, results):
        if math.isfinite(result):
            get_altitudes_at.seed_exact_samples(name, [at], [result], observatory)

class _MoonEventObserver(Observer):
    """Private, single-pair observer; reuse one identical Moon altitude grid."""
    def altaz(self, time, target=None, obswl=None, grid_times_targets=False):
        from astroplan.target import MoonFlag
        # Restrict reuse to the exact normal rise/set call shape. Other inputs
        # retain Astroplan behavior, without allocating cache keys for big grids.
        key = None
        if (target is MoonFlag and isinstance(time, Time) and time.size <= 1024
                and time.location is None and obswl is None and not grid_times_targets):
            key = (time.scale, time.shape, time.jd1.tobytes(), time.jd2.tobytes(),
                   np.asarray(time.mask).tobytes())
        cached = getattr(self, '_exact_moon_grid', None)
        if key is not None and cached is not None and cached[0] == key:
            return cached[1].copy()
        result = super().altaz(time, target, obswl=obswl, grid_times_targets=grid_times_targets)
        if key is not None:
            self._exact_moon_grid = (key, result.copy())
        return result


def _next_moon_events(context, observation_time):
    # The observer and its fixed site/atmosphere exist only for this pair. Never
    # share them across requests or reuse moving-body results at a new instant.
    observer = _MoonEventObserver(location=_get_location(context), timezone=context.timezone_name)
    return _next_moonrise(observer, observation_time), _next_moonset(observer, observation_time)
