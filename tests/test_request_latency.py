from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import numpy as np
import pytest
from astropy.time import Time
from astropy.utils import iers
from astroplan import Observer
from astroplan.target import MoonFlag
from app.core.planning_context import ObservatoryContext
from app.services import astronomy_service as a, planning_runtime_service as runtime


@pytest.mark.parametrize('latitude,longitude,zone,instant', [
    (33.4,-112,'America/Phoenix','2026-10-18T18:24:00'),
    (33.4,-112,'America/Phoenix','2026-10-18T03:24:00'),
    (40.7,-74,'America/New_York','2026-11-01T06:30:00'),
    (-33.9,151.2,'Australia/Sydney','2026-12-21T12:00:00'),
    (0,0,'UTC','2027-03-21T00:00:00'),
    (89,0,'UTC','2026-06-21T00:00:00'),
    (-89,0,'UTC','2026-12-21T00:00:00')])
def test_moon_event_pair_identical_jd_parts_and_masks(latitude,longitude,zone,instant):
    context=ObservatoryContext('Synthetic',latitude,longitude,zone)
    at=Time(instant,scale='utc')
    with iers.conf.set_temp('auto_download',False):
        observer=a._get_observer(context)
        expected=(a._next_moonrise(observer,at),a._next_moonset(observer,at))
        original=Observer.altaz
        calls=[]
        def counted(self,*args,**kwargs):
            calls.append(1)
            return original(self,*args,**kwargs)
        with patch.object(Observer,'altaz',counted):
            actual=a._next_moon_events(context,at)
        assert len(calls)==1
        for left,right in zip(expected,actual):
            assert np.array_equal(left.mask,right.mask)
            for part in ('jd1','jd2'):
                assert np.array_equal(np.ma.getdata(getattr(left,part)),np.ma.getdata(getattr(right,part)),equal_nan=True)


def test_event_grid_exact_time_keys_copies_and_bound():
    context=ObservatoryContext('Synthetic',33.4,-112,'UTC')
    observer=a._MoonEventObserver(location=a._get_location(context),timezone='UTC')
    at=Time(['2026-10-18T18:24:00','2026-10-18T18:25:00'])
    with iers.conf.set_temp('auto_download',False):
        original=Observer.altaz
        calls=[]
        def counted(self,*args,**kwargs):
            calls.append(1)
            return original(self,*args,**kwargs)
        with patch.object(Observer,'altaz',counted):
            first=observer.altaz(at,MoonFlag)
            again=observer.altaz(at.copy(),MoonFlag)
            assert first is not again
            assert np.array_equal(first.alt.deg,again.alt.deg)
            assert len(calls)==1
            shifted=Time(at.jd1,at.jd2+1e-9,format='jd',scale=at.scale)
            observer.altaz(shifted,MoonFlag)
            assert len(calls)==2
            large=Time(np.repeat(at.jd1[0],1025),np.repeat(at.jd2[0],1025),format='jd')
            observer.altaz(large,MoonFlag)
            observer.altaz(large,MoonFlag)
            assert len(calls)==4


def test_catalog_cache_values_invalidate_and_copies_isolate_callers():
    a._fixed_catalog_coordinate.cache_clear()
    with patch.object(a,'get_target',return_value={'ra':'1h','dec':'2d'}):
        first=a.get_target_coordinate('fixture')
        first.data.lon[...] = 0
        second=a.get_target_coordinate('fixture')
        assert second.ra.deg == pytest.approx(15)
        assert a._fixed_catalog_coordinate.cache_info().hits==1
    with patch.object(a,'get_target',return_value={'ra':'2h','dec':'2d'}):
        assert a.get_target_coordinate('fixture').ra.deg == pytest.approx(30)
    assert a._fixed_catalog_coordinate.cache_info().misses==2
    for i in range(520):
        a._fixed_catalog_coordinate(f'{i/1000}h','2d')
    assert a._fixed_catalog_coordinate.cache_info().currsize==512
    a._fixed_catalog_coordinate.cache_clear()


def test_catalog_cache_concurrent_defensive_copies():
    a._fixed_catalog_coordinate.cache_clear()
    def run(i):
        coordinate=a.get_target_coordinate('M31')
        expected=coordinate.ra.deg
        coordinate.data.lon[...] = i * coordinate.data.lon.unit
        return expected
    with ThreadPoolExecutor(max_workers=4) as pool:
        values=list(pool.map(run,range(20)))
    assert len(set(values))==1
    assert a.get_target_coordinate('M31').ra.deg==values[0]


def test_art_preparation_failure_is_independent_and_retried(caplog):
    with patch.object(runtime,'get_moon_info_at',return_value={}), \
            patch.object(runtime,'catalog',return_value={}), \
            patch.object(runtime,'prepare_target_art_library',side_effect=[RuntimeError('private fixture'),None]) as art:
        first=runtime.prepare_planning_runtime()
        second=runtime.prepare_planning_runtime()
    assert first['art_catalog_reference']['status']=='deferred'
    assert first['catalog_reference']['status']=='ready'
    assert second['art_catalog_reference']['status']=='ready'
    assert art.call_count==2
    assert 'private fixture' not in caplog.text
