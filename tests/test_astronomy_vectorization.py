from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from astropy.utils import iers
from app.services import astronomy_service as sky
from app.core.planning_context import ObservatoryContext

@pytest.mark.parametrize('target', ['M31', 'NGC7217', 'NGC2099'])
@pytest.mark.parametrize('latitude,month', [(33.4484,10),(-33.86,2),(65,6)])
def test_vectorized_altitudes_match_scalar_at_every_sample(target, latitude, month):
    context = ObservatoryContext('Synthetic',latitude,-112.074,'America/Phoenix',elevation_meters=331)
    start = datetime(2026,month,17,23,tzinfo=timezone.utc)
    times = [start+timedelta(minutes=i*13) for i in range(60)]
    with iers.conf.set_temp('auto_download',False):
        coordinate = sky.get_target_coordinate(target)
        expected = [sky._altitude_from_coordinate(coordinate,t,context) for t in times]
        with patch.object(sky,'get_target_coordinate',wraps=sky.get_target_coordinate) as lookup:
            actual = sky.get_altitudes_at(target,times,context)
        assert actual == expected
        assert lookup.call_count == 1  # no repeated catalog/coordinate construction

def test_unknown_and_empty_series():
    assert sky.get_altitudes_at('unknown',[]) == []
    assert sky.get_altitudes_at('unknown',[datetime.now(timezone.utc)]) == [None]

def test_moving_targets_keep_time_specific_path():
    times=[datetime(2026,10,17,tzinfo=timezone.utc),datetime(2026,10,18,tzinfo=timezone.utc)]
    with patch.object(sky,'is_ephemeris_target',return_value=True), patch.object(sky,'get_ephemeris_coordinates',return_value=[None,None]) as positions:
        assert sky.get_altitudes_at('COMET',times) == [None,None]
        positions.assert_called_once()
