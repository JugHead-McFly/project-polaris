from app.services.scheduler_service import build_schedule_blocks


def candidate(name, score, start, end, observable=True):
    return {
        "advisor": {"object": name},
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
