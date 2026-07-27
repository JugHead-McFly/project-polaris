from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.planning_context import ObservatoryContext
from app.services.astronomy_service import (
    _moon_phase_name,
    get_altitude_at,
    get_moon_separation_at,
    get_target_coordinate,
    get_target_coordinate_at,
    get_transit_datetime,
)
from app.services.ephemeris_service import is_ephemeris_target


OBSERVATION_TIME = datetime(
    2026,
    7,
    17,
    21,
    0,
    tzinfo=ZoneInfo("America/Phoenix"),
)


def test_c20_has_a_fixed_catalog_coordinate():
    coordinate = get_target_coordinate("C 20")

    assert coordinate is not None
    assert round(coordinate.ra.deg, 3) == 314.696
    assert round(coordinate.dec.deg, 3) == 44.33


def test_jupiter_uses_a_time_specific_coordinate():
    coordinate = get_target_coordinate_at(
        "JUPITER",
        OBSERVATION_TIME,
    )

    assert coordinate is not None
    assert get_altitude_at("JUPITER", OBSERVATION_TIME) is not None
    assert get_moon_separation_at("JUPITER", OBSERVATION_TIME) is not None
    assert get_transit_datetime("JUPITER", OBSERVATION_TIME) is not None


def test_comet_requires_a_date_specific_ephemeris():
    assert is_ephemeris_target("C 2026 B3 PANSTARRS")
    assert get_target_coordinate("C 2026 B3 PANSTARRS") is None


def test_moon_phase_name_adds_plain_language_context():
    assert _moon_phase_name(30) == "Waxing Crescent"
    assert _moon_phase_name(90) == "First Quarter"
    assert _moon_phase_name(180) == "Full Moon"
    assert _moon_phase_name(270) == "Last Quarter"
    assert _moon_phase_name(330) == "Waning Crescent"


def test_target_altitude_changes_with_the_planning_observatory():
    phoenix = ObservatoryContext(
        name="Phoenix",
        latitude=33.4484,
        longitude=-112.0740,
        timezone_name="America/Phoenix",
    )
    sydney = ObservatoryContext(
        name="Sydney",
        latitude=-33.8688,
        longitude=151.2093,
        timezone_name="Australia/Sydney",
    )

    phoenix_altitude = get_altitude_at(
        "M57",
        OBSERVATION_TIME,
        observatory=phoenix,
    )
    sydney_altitude = get_altitude_at(
        "M57",
        OBSERVATION_TIME,
        observatory=sydney,
    )

    assert phoenix_altitude != sydney_altitude
