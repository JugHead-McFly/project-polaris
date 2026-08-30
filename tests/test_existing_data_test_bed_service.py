import hashlib
import sqlite3

from app.services.existing_data_test_bed_service import (
    build_existing_data_test_bed_report,
)
from scripts.nightly_test_bed_report import render_text_report


def test_named_nightly_scenarios_cover_single_user_decisions():
    report = build_existing_data_test_bed_report()

    assert report["ready"] is True
    assert report["scenario_count"] == 5
    assert report["passed_scenarios"] == 5

    scenarios = {scenario["key"]: scenario for scenario in report["scenarios"]}
    assert scenarios["documented_monsoon_hold"]["actual"][
        "opportunity_score"
    ] == 50.2
    assert scenarios["clear_eq_nebula"]["actual"][
        "recommended_exposure_seconds"
    ] == 30
    assert scenarios["dwarf_long_run_split"]["actual"]["run_frames"] == [
        999,
        661,
    ]
    assert scenarios["bright_moon_broadband_caution"]["actual"][
        "recommended_filter"
    ] == "Astro"
    assert scenarios["weather_unavailable_fail_safe"]["actual"][
        "block_count"
    ] == 0


def test_local_evidence_inventory_is_read_only_and_privacy_safe(tmp_path):
    database_path = tmp_path / "polaris.db"
    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE captures (
            object_name TEXT,
            total_integration_seconds INTEGER
        );
        CREATE TABLE sessions (date TEXT);
        CREATE TABLE capture_analyses (scoring_version TEXT);
        INSERT INTO captures VALUES ('M57', 3600), ('M57', 1800), ('M31', 900);
        INSERT INTO sessions VALUES ('2026-07-17'), ('not-a-date');
        INSERT INTO capture_analyses VALUES ('2.0'), ('2.0'), ('1.0');
        """
    )
    connection.commit()
    connection.close()
    before = hashlib.sha256(database_path.read_bytes()).hexdigest()

    report = build_existing_data_test_bed_report(database_path)

    after = hashlib.sha256(database_path.read_bytes()).hexdigest()
    evidence = report["local_evidence"]
    assert report["ready"] is True
    assert before == after
    assert evidence["read_only"] is True
    assert evidence["captures"] == 3
    assert evidence["targets"] == 2
    assert evidence["integration_hours"] == 1.75
    assert evidence["quality_v2_analyses"] == 2
    assert evidence["invalid_session_dates"] == 1
    assert "filenames, paths, coordinates" in evidence["privacy_note"]


def test_text_report_is_plain_english_and_flags_existing_date_cleanup(tmp_path):
    database_path = tmp_path / "polaris.db"
    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE captures (
            object_name TEXT,
            total_integration_seconds INTEGER
        );
        CREATE TABLE sessions (date TEXT);
        CREATE TABLE capture_analyses (scoring_version TEXT);
        INSERT INTO captures VALUES ('M57', 3600);
        INSERT INTO sessions VALUES ('bad-date');
        INSERT INTO capture_analyses VALUES ('2.0');
        """
    )
    connection.commit()
    connection.close()

    text = render_text_report(
        build_existing_data_test_bed_report(database_path)
    )

    assert "5 of 5 nightly scenarios passed" in text
    assert "Documented monsoon hold: Do Not Image" in text
    assert "1 session date value(s) need cleanup" in text
    assert text.endswith("Overall: READY")
