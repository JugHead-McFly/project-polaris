import sqlite3
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from app.api.tonight import _build_operator_message
from app.services.imaging_settings_service import apply_tonight_settings
from app.services.night_planner_service import build_night_plan
from app.services.night_rating_service import calculate_night_rating
from app.services.opportunity_score_service import calculate_opportunity_score
from app.services.opportunity_score_service import explain_opportunity_for_decision
from app.services.scheduler_service import build_tonight_schedule


TEST_BED_VERSION = "v1.11"


def _advisor(
    *,
    object_name: str,
    exposure_seconds: int,
    gain: float,
    filter_name: str,
    remaining_seconds: Optional[int] = None,
) -> Dict:
    return {
        "object": object_name,
        "recommended_sub_exposure_seconds": exposure_seconds,
        "recommended_gain": gain,
        "recommended_filter": filter_name,
        "recommendation_source": "capture_history",
        "remaining_seconds": remaining_seconds,
    }


def _candidate(scenario: Dict) -> Dict:
    target = scenario["target"]
    advisor = apply_tonight_settings(
        advisor=_advisor(
            object_name=target["object"],
            exposure_seconds=target["exposure_seconds"],
            gain=target["gain"],
            filter_name=target["filter"],
            remaining_seconds=target.get("remaining_seconds"),
        ),
        weather=scenario["weather"],
        moon=scenario["moon"],
        moon_warning=target.get("moon_warning"),
        moon_separation_degrees=target.get("moon_separation_degrees"),
        bortle_class=target.get("bortle_class"),
        equatorial_mode_enabled=scenario["equatorial_mode_enabled"],
        rig_profile_key=scenario["rig_profile_key"],
    )
    return {
        "advisor": advisor,
        "planner_score": target["planner_score"],
        "observable": True,
        "current_altitude": target["maximum_dark_altitude"],
        "maximum_dark_altitude": target["maximum_dark_altitude"],
        "recommended_start": target["start"],
        "recommended_end": target["end"],
        "moon_warning": target.get("moon_warning"),
        "moon_separation_degrees": target.get("moon_separation_degrees"),
    }


def _legacy_target(candidate: Dict) -> Dict:
    return {
        "object": candidate["advisor"]["object"],
        "recommended_start": candidate["recommended_start"],
        "recommended_end": candidate["recommended_end"],
        "next_action": "Continue imaging",
        "observable": candidate["observable"],
        "moon_warning": candidate.get("moon_warning"),
    }


def _planner(scenario: Dict, candidate: Dict) -> Dict:
    legacy_plan = build_night_plan(
        recommended_target=_legacy_target(candidate),
        backup_target=None,
        darkness=scenario["darkness"],
        weather=scenario["weather"],
    )
    decision = legacy_plan["decision"]
    return {
        "decision": decision,
        "recommended_target": (
            candidate
            if decision != "Do Not Image" and scenario["schedule_target"]
            else None
        ),
        "best_theoretical_target": candidate,
        "alternatives": [],
        "notes": legacy_plan["notes"],
        "weather": scenario["weather"],
        "moon": scenario["moon"],
        "darkness": scenario["darkness"],
    }


def _scenarios() -> List[Dict]:
    return [
        {
            "key": "documented_monsoon_hold",
            "name": "Documented monsoon hold",
            "provenance": (
                "Sanitized inputs from the hosted plan verified on 2026-08-30; "
                "private location details are omitted."
            ),
            "truth_basis": "Documented historical outcome and product safety rule",
            "timezone_name": "America/Phoenix",
            "rig_profile_key": "dwarf-mini",
            "equatorial_mode_enabled": True,
            "schedule_target": False,
            "weather": {
                "observing_rating": 1,
                "planned_cloud_cover_percent": 100,
                "planned_humidity_percent": 37,
                "planned_wind_speed_mph": 11.5,
                "planned_transparency_index": 2,
                "planned_transparency_forecast_at": "2026-08-30 08:00 PM",
                "planned_seeing_index": 3,
                "planned_seeing_forecast_at": "2026-08-30 08:00 PM",
            },
            "moon": {
                "illumination_percent": 92.5,
                "above_horizon": True,
            },
            "darkness": {
                "astronomical_darkness_start": "2026-08-30 08:20 PM",
                "astronomical_darkness_end": "2026-08-31 04:34 AM",
            },
            "target": {
                "object": "M57",
                "planner_score": 120,
                "start": "2026-08-30 08:20 PM",
                "end": "2026-08-31 02:35 AM",
                "maximum_dark_altitude": 88.6,
                "moon_warning": "Bright Moon",
                "moon_separation_degrees": 80,
                "bortle_class": 7,
                "exposure_seconds": 15,
                "gain": 60,
                "filter": "Duo-Band",
            },
            "expected": {
                "decision": "Do Not Image",
                "block_count": 0,
                "night_quality": "Very Poor",
                "opportunity_score": 38.2,
                "recommended_exposure_seconds": 15,
                "recommended_filter": "Duo-Band",
            },
            "message_contains": "cloud cover is 100%",
        },
        {
            "key": "clear_eq_nebula",
            "name": "Clear EQ nebula night",
            "provenance": (
                "Deterministic fixture based on existing M57 capture history and "
                "the verified clear-night planner example."
            ),
            "truth_basis": "Existing capture history and documented settings rules",
            "timezone_name": "America/Phoenix",
            "rig_profile_key": "dwarf-mini",
            "equatorial_mode_enabled": True,
            "schedule_target": True,
            "weather": {
                "observing_rating": 5,
                "planned_cloud_cover_percent": 10,
                "planned_humidity_percent": 25,
                "planned_wind_speed_mph": 4,
                "planned_transparency_index": 3,
                "planned_transparency_forecast_at": "2026-07-17 09:00 PM",
                "planned_seeing_index": 4,
                "planned_seeing_forecast_at": "2026-07-17 09:00 PM",
            },
            "moon": {
                "illumination_percent": 15,
                "above_horizon": True,
                "next_moonset": "2026-07-17 09:57 PM",
            },
            "darkness": {
                "astronomical_darkness_start": "2026-07-17 09:14 PM",
                "astronomical_darkness_end": "2026-07-18 03:51 AM",
            },
            "target": {
                "object": "M57",
                "planner_score": 149.6,
                "start": "2026-07-17 09:14 PM",
                "end": "2026-07-18 01:00 AM",
                "maximum_dark_altitude": 81.9,
                "moon_warning": "None",
                "moon_separation_degrees": 80,
                "bortle_class": 7,
                "exposure_seconds": 15,
                "gain": 100,
                "filter": "Duo-Band",
                "remaining_seconds": 4 * 3600,
            },
            "expected": {
                "decision": "Proceed",
                "block_count": 1,
                "block_objects": ["M57"],
                "night_quality": "Excellent",
                "opportunity_score": 85.7,
                "recommended_exposure_seconds": 30,
                "recommended_filter": "Duo-Band",
            },
            "message_contains": "Conditions currently support imaging",
        },
        {
            "key": "dwarf_long_run_split",
            "name": "DWARF long-run split",
            "provenance": (
                "Deterministic long C20 session using the recorded DWARF 3 "
                "single-run limit."
            ),
            "truth_basis": "Official rig limit and existing C20 capture history",
            "timezone_name": "America/Phoenix",
            "rig_profile_key": "dwarf-3",
            "equatorial_mode_enabled": False,
            "schedule_target": True,
            "weather": {
                "observing_rating": 5,
                "planned_cloud_cover_percent": 5,
                "planned_humidity_percent": 30,
                "planned_wind_speed_mph": 3,
                "planned_transparency_index": 3,
                "planned_transparency_forecast_at": "2026-06-26 09:00 PM",
                "planned_seeing_index": 3,
                "planned_seeing_forecast_at": "2026-06-26 09:00 PM",
            },
            "moon": {
                "illumination_percent": 20,
                "above_horizon": False,
            },
            "darkness": {
                "astronomical_darkness_start": "2026-06-26 09:00 PM",
                "astronomical_darkness_end": "2026-06-27 04:00 AM",
            },
            "target": {
                "object": "C 20",
                "planner_score": 140,
                "start": "2026-06-26 09:00 PM",
                "end": "2026-06-27 04:00 AM",
                "maximum_dark_altitude": 75,
                "moon_warning": "None",
                "moon_separation_degrees": 90,
                "bortle_class": 7,
                "exposure_seconds": 15,
                "gain": 60,
                "filter": "Duo-Band",
                "remaining_seconds": 7 * 3600,
            },
            "expected": {
                "decision": "Proceed",
                "block_count": 2,
                "block_objects": ["C 20", "C 20"],
                "run_frames": [999, 661],
                "recommended_exposure_seconds": 15,
                "recommended_filter": "Duo-Band",
            },
            "message_contains": "Conditions currently support imaging",
        },
        {
            "key": "bright_moon_broadband_caution",
            "name": "Bright-Moon broadband caution",
            "provenance": (
                "Deterministic M31 case using existing target history and the "
                "documented bright-Moon rule."
            ),
            "truth_basis": "Existing capture history and documented Moon rules",
            "timezone_name": "America/Phoenix",
            "rig_profile_key": "dwarf-3",
            "equatorial_mode_enabled": True,
            "schedule_target": True,
            "weather": {
                "observing_rating": 3,
                "planned_cloud_cover_percent": 35,
                "planned_humidity_percent": 60,
                "planned_wind_speed_mph": 4,
                "planned_transparency_index": 4,
                "planned_transparency_forecast_at": "2026-07-20 10:00 PM",
                "planned_seeing_index": 5,
                "planned_seeing_forecast_at": "2026-07-20 10:00 PM",
            },
            "moon": {
                "illumination_percent": 90,
                "above_horizon": True,
            },
            "darkness": {
                "astronomical_darkness_start": "2026-07-20 10:00 PM",
                "astronomical_darkness_end": "2026-07-21 02:00 AM",
            },
            "target": {
                "object": "M31",
                "planner_score": 100,
                "start": "2026-07-20 10:00 PM",
                "end": "2026-07-21 02:00 AM",
                "maximum_dark_altitude": 70,
                "moon_warning": "Strong Moon interference",
                "moon_separation_degrees": 15,
                "bortle_class": 7,
                "exposure_seconds": 30,
                "gain": 80,
                "filter": "Duo-Band",
                "remaining_seconds": 4 * 3600,
            },
            "expected": {
                "decision": "Use Caution",
                "block_count": 1,
                "block_objects": ["M31"],
                "night_quality": "Poor",
                "recommended_exposure_seconds": 15,
                "recommended_filter": "Astro",
            },
            "message_contains": "Use caution",
        },
        {
            "key": "weather_unavailable_fail_safe",
            "name": "Missing-weather fail-safe",
            "provenance": (
                "Deterministic provider-outage fixture with no invented weather "
                "measurements."
            ),
            "truth_basis": "Documented fail-safe product rule",
            "timezone_name": "America/Phoenix",
            "rig_profile_key": "dwarf-mini",
            "equatorial_mode_enabled": False,
            "schedule_target": False,
            "weather": {"observing_rating": 0},
            "moon": {},
            "darkness": {
                "astronomical_darkness_start": "2026-07-12 09:00 PM",
                "astronomical_darkness_end": "2026-07-13 03:00 AM",
            },
            "target": {
                "object": "M13",
                "planner_score": 110,
                "start": "2026-07-12 09:00 PM",
                "end": "2026-07-13 01:00 AM",
                "maximum_dark_altitude": 78,
                "moon_warning": None,
                "moon_separation_degrees": None,
                "bortle_class": 7,
                "exposure_seconds": 15,
                "gain": 60,
                "filter": "Astro",
            },
            "expected": {
                "decision": "Do Not Image",
                "block_count": 0,
                "night_quality": "Unavailable",
                "recommended_exposure_seconds": 15,
                "recommended_filter": "Astro",
                "unavailable_components": [
                    "cloud",
                    "moon",
                    "visibility",
                    "seeing",
                ],
            },
            "message_contains": "live weather data is unavailable",
        },
    ]


def _evaluate_scenario(scenario: Dict) -> Dict:
    candidate = _candidate(scenario)
    planner = _planner(scenario, candidate)
    schedule = build_tonight_schedule(
        planner,
        timezone_name=scenario["timezone_name"],
        rig_profile_key=scenario["rig_profile_key"],
    )
    night_rating = calculate_night_rating(
        scenario["weather"],
        scenario["moon"],
        candidate,
    )
    opportunity = calculate_opportunity_score(
        weather=scenario["weather"],
        moon=scenario["moon"],
        darkness=scenario["darkness"],
        target=candidate,
    )
    message = _build_operator_message(schedule)
    opportunity = explain_opportunity_for_decision(
        opportunity,
        schedule["decision"],
    )
    actual = {
        "decision": schedule["decision"],
        "block_count": len(schedule["blocks"]),
        "block_objects": [block["object"] for block in schedule["blocks"]],
        "run_frames": [
            block["planned_subframes"] for block in schedule["blocks"]
        ],
        "night_quality": night_rating["quality"],
        "opportunity_score": opportunity["total"],
        "opportunity_label": opportunity["label"],
        "recommended_exposure_seconds": candidate["advisor"][
            "recommended_sub_exposure_seconds"
        ],
        "recommended_filter": candidate["advisor"]["recommended_filter"],
        "unavailable_components": [
            component["key"]
            for component in opportunity["components"]
            if component["points"] is None
        ],
        "operator_message": message,
    }
    checks = [
        {
            "field": field,
            "expected": expected,
            "actual": actual[field],
            "passed": actual[field] == expected,
        }
        for field, expected in scenario["expected"].items()
    ]
    checks.append(
        {
            "field": "operator_message_contains",
            "expected": scenario["message_contains"],
            "actual": message,
            "passed": scenario["message_contains"] in message,
        }
    )
    return {
        "key": scenario["key"],
        "name": scenario["name"],
        "provenance": scenario["provenance"],
        "truth_basis": scenario["truth_basis"],
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "actual": actual,
    }


def inspect_local_evidence(database_path: Path) -> Dict:
    path = database_path.expanduser().resolve()
    if not path.is_file():
        return {
            "status": "unavailable",
            "read_only": True,
            "message": "The local Polaris database was not found.",
        }

    try:
        connection = sqlite3.connect(
            f"{path.as_uri()}?mode=ro",
            uri=True,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
        counts = {
            "captures": connection.execute(
                "SELECT COUNT(*) FROM captures"
            ).fetchone()[0],
            "sessions": connection.execute(
                "SELECT COUNT(*) FROM sessions"
            ).fetchone()[0],
            "quality_analyses": connection.execute(
                "SELECT COUNT(*) FROM capture_analyses"
            ).fetchone()[0],
            "targets": connection.execute(
                "SELECT COUNT(DISTINCT object_name) FROM captures"
            ).fetchone()[0],
        }
        integration_seconds = connection.execute(
            "SELECT SUM(COALESCE(total_integration_seconds, 0)) FROM captures"
        ).fetchone()[0]
        quality_v2 = connection.execute(
            "SELECT COUNT(*) FROM capture_analyses WHERE scoring_version = '2.0'"
        ).fetchone()[0]
        session_dates = [
            row[0]
            for row in connection.execute("SELECT date FROM sessions").fetchall()
        ]
    except sqlite3.Error as error:
        return {
            "status": "unavailable",
            "read_only": True,
            "message": f"The local evidence inventory could not be read: {error}",
        }
    finally:
        if "connection" in locals():
            connection.close()

    invalid_session_dates = 0
    for value in session_dates:
        try:
            date.fromisoformat(value or "")
        except ValueError:
            invalid_session_dates += 1

    return {
        "status": "ready" if quick_check == "ok" else "unhealthy",
        "read_only": True,
        "database_label": path.name,
        "integrity_check": quick_check,
        **counts,
        "integration_hours": round((integration_seconds or 0) / 3600, 2),
        "quality_v2_analyses": quality_v2,
        "invalid_session_dates": invalid_session_dates,
        "privacy_note": (
            "No filenames, paths, coordinates, account identifiers, or raw "
            "capture data are included."
        ),
    }


def build_existing_data_test_bed_report(
    database_path: Optional[Path] = None,
) -> Dict:
    scenarios = [_evaluate_scenario(scenario) for scenario in _scenarios()]
    evidence = (
        inspect_local_evidence(database_path)
        if database_path is not None
        else {
            "status": "not_requested",
            "read_only": True,
            "message": "Local evidence inventory was not requested.",
        }
    )
    passed_scenarios = sum(scenario["passed"] for scenario in scenarios)
    evidence_ready = evidence["status"] in {"ready", "not_requested"}
    return {
        "test_bed_version": TEST_BED_VERSION,
        "ready": passed_scenarios == len(scenarios) and evidence_ready,
        "scenario_count": len(scenarios),
        "passed_scenarios": passed_scenarios,
        "scenarios": scenarios,
        "local_evidence": evidence,
    }
