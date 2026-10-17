from dataclasses import replace
from unittest.mock import patch
import pytest
from app.services.deep_sky_catalog import get_entry, imaging_suitability, automatic_exclusion
from app.data.rig_profiles import get_rig_profile
from app.services.planner_service import build_target_plan
from import_plan_fixture import workflow, START, END
from app.core.planning_context import ObservatoryContext

RIG = get_rig_profile('dwarf-mini')


def test_physical_pixel_scale_and_galaxy_detail_limit():
    quality = imaging_suitability(get_entry('NGC7217'), RIG, 8)
    assert quality['major_pixels'] == pytest.approx(68.0, abs=0.1)
    assert quality['minor_pixels'] == pytest.approx(57.8, abs=0.1)
    assert quality['adjustment'] < 0
    assert any('urban' in reason for reason in quality['reasons'])


def test_equal_visibility_favors_better_image_footprint_and_brightness():
    small = get_entry('NGC7217')
    large = {**small, 'major_arcmin': 20, 'minor_arcmin': 15, 'v_magnitude': 6}
    assert imaging_suitability(large, RIG, 8)['adjustment'] > imaging_suitability(small, RIG, 8)['adjustment']
    # Exercise actual final planner scoring with identical mocked visibility.
    context = ObservatoryContext('Synthetic', 0, 0, 'UTC', rig_profile_key='dwarf-mini', bortle_class=8)
    with workflow(), patch('app.services.planner_service.get_entry', return_value=small):
        small_plan = build_target_plan(None, 'M27', START, END, observatory=context, use_capture_history=False)
    with workflow(), patch('app.services.planner_service.get_entry', return_value=large):
        large_plan = build_target_plan(None, 'M27', START, END, observatory=context, use_capture_history=False)
    assert large_plan['planner_score'] > small_plan['planner_score']
    assert 'not an image-quality guarantee' in large_plan['selection_reason']


def test_unknowns_are_not_favorable_evidence():
    known = {**get_entry('NGC7217'), 'major_arcmin': 20, 'minor_arcmin': 15, 'v_magnitude': 6, 'surface_brightness': 22}
    missing = {**known, 'v_magnitude': None, 'minor_arcmin': None, 'surface_brightness': None}
    assert imaging_suitability(missing, RIG, 8)['adjustment'] < imaging_suitability(known, RIG, 8)['adjustment']
    assert any('unknown' in reason for reason in imaging_suitability(missing, RIG, 8)['reasons'])


@pytest.mark.parametrize('field', ['minor_arcmin', 'major_arcmin', 'surface_brightness', 'v_magnitude'])
def test_removing_unfavorable_measurement_cannot_improve_ranking(field):
    difficult = {**get_entry('NGC7217'), 'surface_brightness': 23.8}
    assert imaging_suitability({**difficult, field: None}, RIG, 8)['adjustment'] <= imaging_suitability(difficult, RIG, 8)['adjustment']
    assert imaging_suitability(None, RIG, 8)['adjustment'] <= imaging_suitability(difficult, RIG, 8)['adjustment']


def test_unknown_scale_or_sky_does_not_improve_difficult_galaxy():
    entry = get_entry('NGC7217')
    missing_scale = replace(RIG, focal_length_mm=None)
    assert imaging_suitability(entry, missing_scale, 8)['adjustment'] <= imaging_suitability(entry, RIG, 8)['adjustment']
    assert imaging_suitability(entry, RIG, None)['adjustment'] <= imaging_suitability(entry, RIG, 8)['adjustment']


def test_alias_equivalence_and_equipment_scale_change():
    assert imaging_suitability(get_entry('M33'), RIG, 8) == imaging_suitability(get_entry('NGC598'), RIG, 8)
    larger_scale = replace(RIG, focal_length_mm=600)
    assert imaging_suitability(get_entry('NGC7217'), larger_scale, 8)['adjustment'] > imaging_suitability(get_entry('NGC7217'), RIG, 8)['adjustment']


def test_size_reward_saturates_and_mosaics_remain_eligible():
    normal = {**get_entry('NGC7217'), 'major_arcmin': 20, 'minor_arcmin': 15}
    huge = {**normal, 'major_arcmin': 600, 'minor_arcmin': 400}
    assert imaging_suitability(huge, RIG, 8)['adjustment'] == imaging_suitability(normal, RIG, 8)['adjustment']
    assert automatic_exclusion(huge, RIG) is None
    assert RIG.assess_target_fit(10, 400/60).fits is False


def test_integrated_brightness_does_not_erase_faint_surface_brightness():
    bright = {**get_entry('M33'), 'surface_brightness': 22}
    faint = {**bright, 'surface_brightness': 23.8}
    assert imaging_suitability(faint, RIG, 8)['adjustment'] < imaging_suitability(bright, RIG, 8)['adjustment']
