"""One physical night must drive both display and allocation, including at dawn."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from astropy.utils import iers
from app.core.planning_context import ObservatoryContext
from app.services import astronomy_service as astronomy
from import_plan_fixture import workflow, START, END


@pytest.mark.parametrize('latitude,longitude,zone,instant', [
    (33.4, -112, 'America/Phoenix', '2026-10-18T18:24:00+00:00'),
    (33.4, -112, 'America/Phoenix', '2026-10-18T03:24:00+00:00'),
    (40.7, -74, 'America/New_York', '2026-11-01T06:30:00+00:00'),
    (-33.9, 151.2, 'Australia/Sydney', '2026-12-21T12:00:00+00:00'),
    (89, 0, 'UTC', '2026-06-21T00:00:00+00:00'),
])
def test_precomputed_window_matches_standalone(latitude, longitude, zone, instant):
    context = ObservatoryContext('Synthetic', latitude, longitude, zone)
    at = datetime.fromisoformat(instant)
    with iers.conf.set_temp('auto_download', False):
        expected = astronomy.get_darkness_info(at, context)
        window = astronomy.get_darkness_window_datetimes(at, context)
    with patch.object(astronomy, 'get_darkness_window_datetimes', side_effect=AssertionError('recomputed')):
        assert astronomy.get_darkness_info(observatory=context, window=window) == expected


def test_display_preserves_dst_offsets_and_no_window():
    zone = ZoneInfo('America/New_York')
    dusk = datetime(2026, 10, 31, 20, tzinfo=zone)
    dawn = datetime(2026, 11, 1, 6, tzinfo=zone)
    result = astronomy.get_darkness_info(window=(None, dusk, dawn))
    assert result['astronomical_darkness_start_at'].endswith('-04:00')
    assert result['astronomical_darkness_end_at'].endswith('-05:00')
    assert all(value is None for value in astronomy.get_darkness_info(window=(None, None, None)).values())


def test_hosted_plan_cannot_switch_nights_between_display_and_schedule():
    first = (START - timedelta(hours=1), START, END)
    following = tuple(at + timedelta(days=1) for at in first)
    with workflow() as flow, \
            patch('app.services.planner_service.get_darkness_window_datetimes', side_effect=[first, following]) as windows, \
            patch('app.services.planner_service.get_darkness_info', astronomy.get_darkness_info), \
            TestClient(flow.app) as client:
        plan = flow.plan(client)
    assert windows.call_count == 1
    assert plan['darkness']['astronomical_darkness_start_at'] == START.isoformat()
    assert plan['darkness']['astronomical_darkness_end_at'] == END.isoformat()
