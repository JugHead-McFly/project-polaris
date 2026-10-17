import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.services.deep_sky_catalog import catalog, get_entry, search, automatic_exclusion, shortlist, DATA, parse_rows
from app.data.rig_profiles import get_rig_profile
from app.core.planning_context import ObservatoryContext
from app.services.capture_history_service import history_advice
from app.api.objects import router


def test_pinned_corpus_valid_coordinates_and_hash():
    manifest = json.loads((DATA/'source.json').read_text())
    assert hashlib.sha256((DATA/'openngc.csv').read_bytes()).hexdigest() == manifest['sha256']
    entries, aliases = catalog()
    assert len(entries) > 12000
    assert len(entries) == manifest['usable_deep_sky_entries']
    assert all(0 <= e['ra_degrees'] < 360 and -90 <= e['dec_degrees'] <= 90 for e in entries.values())
    assert all(not e['settings_verified'] for e in entries.values())


def test_search_aliases_and_pagination():
    assert get_entry('M 101')['id'] == get_entry('NGC 5457')['id']
    assert get_entry('NGC0224')['id'] == 'M31'
    assert get_entry('NGC 7000')['id'] == 'C 20'
    assert search('Triangulum Galaxy')['items'][0]['id'] == 'M33'
    assert search('', 0, 5)['items'] != search('', 5, 5)['items']
    app = FastAPI(); app.include_router(router)
    with TestClient(app) as client:
        assert client.get('/objects/catalog/search?q=M101').json()['items'][0]['id'] == 'NGC5457'
        assert client.get('/objects/catalog/search?limit=101').status_code == 422


def test_alias_history_never_reopens_completed_goal_or_changes_input():
    history = {'M101': {'seconds': 7200}, 'NGC5457': {'seconds': 7200}}
    assert history_advice('NGC5457', history)['remaining_seconds'] == 0
    assert history['M101']['seconds'] == 7200
    # Previously uncataloged NGC alias had 4h, while legacy M31 has 7h.
    advice = history_advice('M31', {'NGC224': {'seconds': 14400}})
    assert advice['remaining_seconds'] == 0 and advice['goal_hours'] == 4


def test_local_alias_history_retains_verified_settings_and_completed_goal():
    from app.services.planner_service import _merge_local_alias_advice
    from app.services.advisor_service import get_catalog_exposure_advice
    advice = get_catalog_exposure_advice('NGC224')
    advice.update(current_integration_seconds=3600, recommended_sub_exposure_seconds=30,
                  recommended_gain=60, recommended_filter='Astro')
    with patch('app.services.planner_service.get_exposure_advice', return_value={'current_integration_seconds': 25200}):
        merged = _merge_local_alias_advice(None, 'NGC224', advice, ['M31', 'NGC224'])
    assert merged['remaining_seconds'] == 0
    assert merged['current_integration_seconds'] == 28800
    assert merged['recommended_sub_exposure_seconds'] == 30


def test_explicit_empty_targets_do_not_admit_unrelated_history():
    from import_plan_fixture import workflow
    from app.services.planner_service import get_tonight_plan
    with workflow(), patch('app.services.planner_service.get_distinct_targets', return_value=[]):
        plan = get_tonight_plan(None, target_names=[], use_capture_history=False,
                               capture_progress={'M27': {'seconds': 3600}})
    assert plan['schedule_candidates'] == []


def test_completed_alias_totals_removed_before_discovery_shortlist():
    from import_plan_fixture import workflow
    from app.services.planner_service import get_tonight_plan
    with workflow(), patch('app.services.planner_service.shortlist', return_value=[]) as sieve:
        get_tonight_plan(None, use_capture_history=False,
                        capture_progress={'M101': {'seconds': 7200}, 'NGC5457': {'seconds': 7200}})
    assert set(sieve.call_args.args[4]) == {'M101', 'NGC5457'}


def test_local_completed_totals_removed_before_discovery_shortlist():
    from import_plan_fixture import workflow
    from app.services.planner_service import get_tonight_plan
    from app.services.advisor_service import get_catalog_exposure_advice
    advice = get_catalog_exposure_advice('M101')
    advice.update(current_integration_seconds=14400, remaining_seconds=0, remaining_hours=0)
    with workflow(), patch('app.services.planner_service.shortlist', return_value=[]) as sieve, \
            patch('app.services.planner_service.get_distinct_targets', return_value=['M101']), \
            patch('app.services.planner_service.get_exposure_advice', return_value=advice):
        get_tonight_plan(None, use_capture_history=True)
    assert sieve.call_args.args[4] == ['M101']


def test_unknown_data_and_resolution_are_honest_but_size_does_not_exclude():
    rig = get_rig_profile('dwarf-mini')
    entry = {**get_entry('M33'), 'major_arcmin': 600, 'minor_arcmin': 500, 'v_magnitude': 8, 'surface_brightness': 22}
    assert automatic_exclusion(entry, rig) is None
    assert rig.assess_target_fit(10, 8).fits is False
    assert 'unknown' in automatic_exclusion({**entry, 'v_magnitude': None}, rig)
    assert 'pixels' in automatic_exclusion({**entry, 'major_arcmin': 0.01}, rig)


def test_ingestion_rejects_invalid_and_nonphysical_rows():
    rows = [dict(Name='NGC1', Type='G', RA='99:00:00', Dec='+00:00:00', NGC='', IC=''),
            dict(Name='NGC2', Type='*', RA='01:00:00', Dec='+00:00:00', NGC='', IC='')]
    assert parse_rows(rows)[0] == {}


def test_whole_night_prefilter_bounded_fast_and_late_risers_survive():
    context = ObservatoryContext('Phoenix', 33.4484, -112.074, 'America/Phoenix')
    start = datetime(2026, 10, 18, 2, 15, tzinfo=timezone.utc)
    begin = time.perf_counter()
    selected = shortlist(context, start, start+timedelta(hours=10), get_rig_profile('dwarf-mini'))
    assert len(selected) <= 21*6
    assert time.perf_counter()-begin < 5
    assert any(get_entry(name)['ra_degrees'] > 75 for name in selected)
    assert shortlist(context, start, start+timedelta(hours=10), get_rig_profile('dwarf-mini'), selected) != selected
