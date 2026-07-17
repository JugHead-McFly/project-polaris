from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.astronomy_service import (
    get_altitude_at,
    get_moon_separation_at,
    get_target_coordinate,
    get_target_coordinate_at,
    get_transit_datetime,
)


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


def test_uncataloged_comet_remains_excluded():
    coordinate = get_target_coordinate_at(
        "C 2026 B3 PANSTARRS",
        OBSERVATION_TIME,
    )

    assert coordinate is None
