import io
import json
from datetime import datetime, timezone
from unittest.mock import patch
from urllib.error import URLError

from app.services.ephemeris_service import (
    clear_ephemeris_cache,
    get_ephemeris_coordinates,
)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def horizons_response():
    result = """
 Date__(UT)__HR:MN:SC.fff, , , R.A.___(ICRF), DEC____(ICRF),
$$SOE
 2026-Jul-18 04:00:00.000,A,m, 162.449754262, 9.883929160,
 2026-Jul-18 04:15:00.000, ,m, 162.450100000, 9.883500000,
$$EOE
"""
    payload = {
        "signature": {
            "version": "1.2",
            "source": "NASA/JPL Horizons API",
        },
        "result": result,
    }
    return FakeResponse(json.dumps(payload).encode("utf-8"))


def test_ephemeris_batches_and_caches_exact_times():
    clear_ephemeris_cache()
    times = [
        datetime(2026, 7, 18, 4, 0, tzinfo=timezone.utc),
        datetime(2026, 7, 18, 4, 15, tzinfo=timezone.utc),
    ]

    with patch(
        "app.services.ephemeris_service.urlopen",
        return_value=horizons_response(),
    ) as mocked_urlopen:
        first = get_ephemeris_coordinates(
            "C 2026 B3 PANSTARRS",
            times,
        )
        second = get_ephemeris_coordinates(
            "C 2026 B3 PANSTARRS",
            times,
        )

    assert all(coordinate is not None for coordinate in first)
    assert all(coordinate is not None for coordinate in second)
    assert round(first[0].ra.deg, 6) == 162.449754
    assert round(first[0].dec.deg, 6) == 9.883929
    assert mocked_urlopen.call_count == 1


def test_ephemeris_failure_returns_no_coordinates():
    clear_ephemeris_cache()
    observation_time = datetime(
        2026,
        7,
        18,
        4,
        0,
        tzinfo=timezone.utc,
    )

    with patch(
        "app.services.ephemeris_service.urlopen",
        side_effect=URLError("unavailable"),
    ):
        coordinates = get_ephemeris_coordinates(
            "C 2026 B3 PANSTARRS",
            [observation_time],
        )

    assert coordinates == [None]
