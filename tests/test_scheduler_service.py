from app.services.scheduler_service import (
    _darkness_minutes,
    build_schedule_blocks,
)


def candidate(
    name,
    score,
    start,
    end,
    observable=True,
    exposure=None,
    gain=None,
    filter_name=None,
    additional_subframes=None,
    remaining_seconds=None,
):
    return {
        "advisor": {
            "object": name,
            "recommended_sub_exposure_seconds": exposure,
            "recommended_gain": gain,
            "recommended_filter": filter_name,
            "recommendation_source": "capture_history",
            "additional_subframes_needed": additional_subframes,
            "remaining_seconds": remaining_seconds,
        },
        "planner_score": score,
        "observable": observable,
        "recommended_start": start,
        "recommended_end": end,
    }


def test_schedule_selects_the_highest_ranked_target_in_each_window():
    blocks = build_schedule_blocks(
        [
            candidate("M42", 90, "2026-07-17 09:00 PM", "2026-07-18 01:00 AM"),
            candidate("M31", 100, "2026-07-17 10:00 PM", "2026-07-18 12:00 AM"),
        ]
    )

    assert [(block["object"], block["duration_minutes"]) for block in blocks] == [
        ("M42", 60),
        ("M31", 120),
        ("M42", 60),
    ]


def test_schedule_excludes_unobservable_and_short_windows():
    blocks = build_schedule_blocks(
        [
            candidate("M42", 90, "2026-07-17 09:00 PM", "2026-07-17 09:29 PM"),
            candidate("M31", 100, "2026-07-17 10:00 PM", "2026-07-17 11:00 PM", observable=False),
        ]
    )

    assert blocks == []


def test_schedule_avoids_a_low_value_equipment_change():
    blocks = build_schedule_blocks(
        [
            candidate(
                "M42",
                90,
                "2026-07-17 09:00 PM",
                "2026-07-18 01:00 AM",
                exposure=15,
                gain=60,
                filter_name="Astro",
            ),
            candidate(
                "M31",
                98,
                "2026-07-17 10:00 PM",
                "2026-07-18 12:00 AM",
                exposure=15,
                gain=100,
                filter_name="Duo-Band",
            ),
        ]
    )

    assert len(blocks) == 1
    assert blocks[0]["object"] == "M42"
    assert blocks[0]["duration_minutes"] == 240
    assert blocks[0]["reason"] == (
        "Retained to avoid a low-value equipment change."
    )


def test_schedule_includes_settings_setup_time_and_subframes():
    blocks = build_schedule_blocks(
        [
            candidate(
                "M57",
                120,
                "2026-07-17 09:00 PM",
                "2026-07-17 11:00 PM",
                exposure=15,
                gain=100,
                filter_name="Duo-Band",
                additional_subframes=1000,
            )
        ]
    )

    block = blocks[0]
    assert block["setup_minutes"] == 5
    assert block["imaging_minutes"] == 115
    assert block["planned_subframes"] == 460
    assert block["recommended_filter"] == "Duo-Band"
    assert "Select Duo-Band filter" in block["setup_changes"]


def test_schedule_moves_to_an_alternative_after_goal_is_met():
    blocks = build_schedule_blocks(
        [
            candidate(
                "M57",
                120,
                "2026-07-17 09:00 PM",
                "2026-07-18 01:00 AM",
                exposure=15,
                gain=100,
                filter_name="Duo-Band",
                additional_subframes=497,
                remaining_seconds=7455,
            ),
            candidate(
                "M27",
                110,
                "2026-07-17 09:00 PM",
                "2026-07-18 01:00 AM",
                exposure=15,
                gain=100,
                filter_name="Duo-Band",
            ),
        ]
    )

    assert [(block["object"], block["duration_minutes"]) for block in blocks] == [
        ("M57", 130),
        ("M27", 110),
    ]
    assert blocks[0]["planned_subframes"] == 497
    assert blocks[1]["setup_changes"] == ["Slew to and center M27"]


def test_darkness_duration_is_reported_in_minutes():
    assert _darkness_minutes(
        {
            "astronomical_darkness_start": "2026-07-17 09:14 PM",
            "astronomical_darkness_end": "2026-07-18 03:51 AM",
        }
    ) == 397
