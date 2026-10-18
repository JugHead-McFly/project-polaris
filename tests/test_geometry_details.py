from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from astropy.coordinates import SkyCoord
from astropy.utils import iers
from app.core import calculation_cache as cache
from app.core.planning_context import ObservatoryContext
from app.services import astronomy_service as a, planner_service as p
from app.services.astronomy_samples import threshold_refinement_times


def test_threshold_refinement_disjoint_runs_and_dst_instants():
    start = datetime(2026, 11, 1, 5, 45, tzinfo=timezone.utc)
    zone = ZoneInfo('America/New_York')
    times = [(start + timedelta(minutes=15*i)).astimezone(zone) for i in range(5)]
    values = [29, 31, 29, 31, 29]
    actual = list(threshold_refinement_times(times, values, 30))
    expected = [(start + timedelta(minutes=15*i+j)).astimezone(zone)
                for i in range(4) for j in range(1, 15)]
    assert [(at.isoformat(), at.fold) for at in actual] == [(at.isoformat(), at.fold) for at in expected]


def test_details_bound_target_chunks_and_stream_refinement_pairs():
    start = datetime(2026, 10, 18, tzinfo=timezone.utc)
    times = [start + timedelta(minutes=15*i) for i in range(3)]
    coord = a.get_target_coordinate('M31')
    @cache.astronomy_calculation
    def run():
        with patch.object(a, 'get_target_coordinate', return_value=coord), \
                patch.object(a, 'get_altitudes_at', return_value=[29,31,29]), \
                patch.object(a, '_moon_coordinate_at', return_value=coord), \
                patch.object(a, '_seed_refinement_pairs') as seeds, \
                patch.object(a, '_prepare_detail_chunk', wraps=a._prepare_detail_chunk) as chunks:
            a.prepare_fixed_target_details((f'T{i}' for i in range(65)), coarse_times=times,
                                           midpoint=times[1], minimum_altitude=30)
            assert [len(call.args[0]) for call in chunks.call_args_list] == [64,1]
            sizes = [len(call.args[2]) for call in seeds.call_args_list]
            assert max(sizes) <= 512
            assert sum(sizes) == 65*28
    run()


def test_details_empty_oversized_and_unsupported_paths_do_not_seed():
    at = datetime(2026,10,18,tzinfo=timezone.utc)
    @cache.astronomy_calculation
    def run():
        def coordinate(name):
            if name == 'INVALID': raise ValueError('fixture')
            assert name == 'UNKNOWN'
            return None
        with patch.object(a, 'get_target_coordinate', side_effect=coordinate), \
                patch.object(a, 'is_ephemeris_target', side_effect=lambda name: name == 'COMET'):
            for times in ([], [at]*4097):
                a.prepare_fixed_target_details(['M31'],coarse_times=times,midpoint=at,minimum_altitude=30)
            a.prepare_fixed_target_details(['JUPITER','COMET','UNKNOWN','INVALID'],
                coarse_times=[at],midpoint=at,minimum_altitude=30)
        assert cache._values.get() == {}
    run()


@pytest.mark.parametrize('row', [[None,31], [float('nan'),31], [float('inf'),31], [20,21]])
def test_details_invalid_or_invisible_rows_skip_refinements(row):
    at = datetime(2026,10,18,tzinfo=timezone.utc)
    coord = a.get_target_coordinate('M31')
    @cache.astronomy_calculation
    def run():
        with patch.object(a, 'get_altitudes_at', return_value=row), \
                patch.object(a, '_moon_coordinate_at', return_value=coord), \
                patch.object(a, '_seed_refinement_pairs', side_effect=AssertionError('unexpected refinement')):
            a.prepare_fixed_target_details(['M31'],coarse_times=[at,at+timedelta(minutes=15)],
                                           midpoint=at,minimum_altitude=30)
    run()


def test_failed_refinement_optimization_leaves_scalar_fallback_available():
    at = datetime(2026,10,18,tzinfo=timezone.utc)
    context=ObservatoryContext('Synthetic',33.4,-112,'America/Phoenix')
    coords=SkyCoord([a.get_target_coordinate('M31')])
    with iers.conf.set_temp('auto_download', False):
        expected=a.get_altitude_at('M31',at,context)
        @cache.astronomy_calculation
        def run():
            with patch.object(SkyCoord,'transform_to',side_effect=ValueError('batch fixture')):
                a._seed_refinement_pairs(coords,[0],[('M31',at)],context)
            assert cache._values.get() == {}
            assert a.get_altitude_at('M31',at,context) == expected
        run()


def test_details_concurrent_sites_match_full_visibility_and_moon():
    at=datetime(2026,11,1,4,30,tzinfo=timezone.utc)
    end=at+timedelta(hours=10)
    contexts=[ObservatoryContext('North',40.7,-74,'America/New_York'),
              ObservatoryContext('South',-33.8,151.2,'Australia/Sydney')]
    midpoint=at+(end-at)/2
    names=['M31','M42','NGC7092']
    barrier=Barrier(2)
    def values(context):
        return [(p.get_dark_visibility(name,at,end,observatory=context),
                 a.get_moon_separation_at(name,midpoint,context)) for name in names]
    with iers.conf.set_temp('auto_download',False):
        expected=[values(context) for context in contexts]
        @cache.astronomy_calculation
        def run(context):
            times=p.generate_sample_times(at,end)
            a.prepare_fixed_target_altitudes(names,[*times,midpoint],context)
            a.prepare_fixed_target_details(names,coarse_times=times,midpoint=midpoint,
                                           minimum_altitude=p.MINIMUM_ALTITUDE_DEGREES,observatory=context)
            barrier.wait(timeout=15)
            return values(context)
        with ThreadPoolExecutor(max_workers=2) as executor:
            actual=list(executor.map(run,contexts))
        assert actual == expected
        assert cache._values.get() is None

@pytest.mark.parametrize('value', [float('nan'),float('inf')])
def test_nonfinite_batch_outputs_are_not_seeded(value):
    from types import SimpleNamespace
    at=datetime(2026,10,18,tzinfo=timezone.utc)
    coord=a.get_target_coordinate('M31')
    @cache.astronomy_calculation
    def run():
        with patch.object(SkyCoord,'transform_to',return_value=SimpleNamespace(alt=SimpleNamespace(deg=[value]))):
            a._seed_refinement_pairs(SkyCoord([coord]),[0],[('M31',at)],None)
        assert cache._values.get() == {}
        with patch.object(a,'get_altitudes_at',return_value=[20]), \
                patch.object(a,'_moon_coordinate_at',return_value=coord), \
                patch.object(SkyCoord,'separation',return_value=SimpleNamespace(deg=[value])):
            a.prepare_fixed_target_details(['M31'],coarse_times=[at],midpoint=at,minimum_altitude=30)
        assert cache._values.get() == {}
    run()
