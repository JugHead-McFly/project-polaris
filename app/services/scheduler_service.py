import math
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.observatory import TIMEZONE
from app.services.planner_service import get_tonight_plan


SCHEDULE_TIME_FORMAT = "%Y-%m-%d %I:%M %p"
MINIMUM_BLOCK_MINUTES = 30
MAXIMUM_BLOCKS = 4
SETUP_BUFFER_MINUTES = 5
EQUIPMENT_CHANGE_SCORE_MARGIN = 12.0


def _parse_schedule_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    return datetime.strptime(
        value,
        SCHEDULE_TIME_FORMAT,
    ).replace(tzinfo=ZoneInfo(TIMEZONE))


def _format_schedule_time(value: datetime) -> str:
    return value.strftime(SCHEDULE_TIME_FORMAT)


def _darkness_minutes(darkness: Dict) -> int:
    start = _parse_schedule_time(
        darkness.get("astronomical_darkness_start")
    )
    end = _parse_schedule_time(
        darkness.get("astronomical_darkness_end")
    )

    if start is None or end is None or end <= start:
        return 0

    return int((end - start).total_seconds() / 60)


def _candidate_windows(candidates: Iterable[Dict]) -> List[Dict]:
    windows = []

    for candidate in candidates:
        if not candidate or not candidate.get("observable"):
            continue

        start = _parse_schedule_time(candidate.get("recommended_start"))
        end = _parse_schedule_time(candidate.get("recommended_end"))

        if start is None or end is None or end <= start:
            continue

        windows.append(
            {
                "candidate": candidate,
                "start": start,
                "end": end,
            }
        )

    return windows


def _advisor_settings(candidate: Dict) -> Dict:
    advisor = candidate.get("advisor", {})
    return {
        "sub_exposure_seconds": advisor.get(
            "recommended_sub_exposure_seconds"
        ),
        "gain": advisor.get("recommended_gain"),
        "filter": advisor.get("recommended_filter"),
        "source": advisor.get("recommendation_source") or "none",
        "additional_subframes": advisor.get(
            "additional_subframes_needed"
        ),
    }


def _equipment_setting_changes(
    previous: Dict,
    selected: Dict,
) -> List[str]:
    previous_settings = _advisor_settings(previous)
    selected_settings = _advisor_settings(selected)
    changes = []

    comparisons = (
        ("filter", "Filter"),
        ("gain", "Gain"),
        ("sub_exposure_seconds", "Sub-exposure"),
    )
    for key, label in comparisons:
        old_value = previous_settings[key]
        new_value = selected_settings[key]

        if (
            old_value is not None
            and new_value is not None
            and old_value != new_value
        ):
            changes.append(
                f"{label}: {old_value} to {new_value}"
            )

    return changes


def _setup_changes(
    previous: Optional[Dict],
    selected: Dict,
) -> List[str]:
    settings = _advisor_settings(selected)
    object_name = selected["advisor"]["object"]
    changes = [f"Slew to and center {object_name}"]

    if previous is None:
        if settings["filter"] is not None:
            changes.append(
                f"Select {settings['filter']} filter"
            )
        if settings["gain"] is not None:
            changes.append(
                f"Set gain to {settings['gain']:g}"
            )
        if settings["sub_exposure_seconds"] is not None:
            changes.append(
                "Set sub-exposure to "
                f"{settings['sub_exposure_seconds']} seconds"
            )
    else:
        changes.extend(
            _equipment_setting_changes(previous, selected)
        )

    if (
        settings["filter"] is None
        or settings["gain"] is None
        or settings["sub_exposure_seconds"] is None
    ):
        changes.append(
            "Verify incomplete equipment settings manually"
        )

    return changes


def _planned_subframes(
    settings: Dict,
    imaging_minutes: int,
) -> Optional[int]:
    sub_exposure_seconds = settings["sub_exposure_seconds"]
    if sub_exposure_seconds is None or sub_exposure_seconds <= 0:
        return None

    capacity = int(
        imaging_minutes * 60 / sub_exposure_seconds
    )
    additional_needed = settings["additional_subframes"]

    if additional_needed is not None:
        return min(capacity, additional_needed)

    return capacity


def _remaining_imaging_minutes(candidate: Dict) -> Optional[int]:
    advisor = candidate.get("advisor", {})
    remaining_seconds = advisor.get("remaining_seconds")

    if remaining_seconds is not None:
        return math.ceil(max(remaining_seconds, 0) / 60)

    settings = _advisor_settings(candidate)
    if (
        settings["additional_subframes"] is not None
        and settings["sub_exposure_seconds"] is not None
    ):
        return math.ceil(
            settings["additional_subframes"]
            * settings["sub_exposure_seconds"]
            / 60
        )

    return None


def build_schedule_blocks(candidates: Iterable[Dict]) -> List[Dict]:
    """Build a non-overlapping, advisory schedule from Planner V2 windows."""
    windows = _candidate_windows(candidates)
    boundaries = sorted(
        {
            boundary
            for window in windows
            for boundary in (window["start"], window["end"])
        }
    )
    if len(boundaries) < 2:
        return []

    remaining_minutes = {
        window["candidate"]["advisor"]["object"]: (
            _remaining_imaging_minutes(window["candidate"])
        )
        for window in windows
    }
    blocks = []
    cursor = boundaries[0]

    while cursor < boundaries[-1]:
        next_boundary = min(
            boundary
            for boundary in boundaries
            if boundary > cursor
        )
        active = [
            window["candidate"]
            for window in windows
            if (
                window["start"] <= cursor
                and window["end"] > cursor
                and remaining_minutes[
                    window["candidate"]["advisor"]["object"]
                ] != 0
            )
        ]

        if not active:
            cursor = next_boundary
            continue

        highest_ranked = max(
            active,
            key=lambda candidate: candidate["planner_score"],
        )
        selected = highest_ranked
        equipment_hold = False

        if blocks:
            current_candidate = blocks[-1]["candidate"]
            current_object = current_candidate["advisor"]["object"]
            active_current = next(
                (
                    candidate
                    for candidate in active
                    if candidate["advisor"]["object"] == current_object
                ),
                None,
            )

            if (
                active_current is not None
                and highest_ranked["advisor"]["object"] != current_object
                and _equipment_setting_changes(
                    active_current,
                    highest_ranked,
                )
                and (
                    highest_ranked["planner_score"]
                    - active_current["planner_score"]
                    < EQUIPMENT_CHANGE_SCORE_MARGIN
                )
            ):
                selected = active_current
                equipment_hold = True

        selected_object = selected["advisor"]["object"]
        starting_new_block = (
            not blocks
            or blocks[-1]["object"] != selected_object
        )
        interval_minutes = int(
            (next_boundary - cursor).total_seconds() / 60
        )
        setup_minutes = (
            min(SETUP_BUFFER_MINUTES, interval_minutes)
            if starting_new_block
            else 0
        )
        available_imaging_minutes = max(
            interval_minutes - setup_minutes,
            0,
        )
        target_remaining = remaining_minutes[selected_object]
        imaging_minutes = (
            min(available_imaging_minutes, target_remaining)
            if target_remaining is not None
            else available_imaging_minutes
        )
        scheduled_minutes = setup_minutes + imaging_minutes

        if scheduled_minutes <= 0:
            remaining_minutes[selected_object] = 0
            continue

        block_end = cursor + timedelta(
            minutes=scheduled_minutes
        )

        if not starting_new_block:
            blocks[-1]["end_datetime"] = block_end
            blocks[-1]["imaging_minutes"] += imaging_minutes
            if equipment_hold:
                blocks[-1]["reason"] = (
                    "Retained to avoid a low-value equipment change."
                )
        else:
            blocks.append(
                {
                    "object": selected_object,
                    "candidate": selected,
                    "start_datetime": cursor,
                    "end_datetime": block_end,
                    "setup_minutes": setup_minutes,
                    "imaging_minutes": imaging_minutes,
                    "planner_score": selected["planner_score"],
                    "reason": (
                        "Highest-ranked observable target for this time window."
                    ),
                }
            )

        if target_remaining is not None:
            remaining_minutes[selected_object] = max(
                target_remaining - imaging_minutes,
                0,
            )

        cursor = block_end

    scheduled_blocks = []
    previous_candidate = None
    for block in blocks:
        duration_minutes = int(
            (block["end_datetime"] - block["start_datetime"])
            .total_seconds()
            / 60
        )
        if duration_minutes < MINIMUM_BLOCK_MINUTES:
            continue

        settings = _advisor_settings(block["candidate"])
        setup_minutes = block["setup_minutes"]
        imaging_minutes = block["imaging_minutes"]

        scheduled_blocks.append(
            {
                "object": block["object"],
                "start": _format_schedule_time(block["start_datetime"]),
                "end": _format_schedule_time(block["end_datetime"]),
                "duration_minutes": duration_minutes,
                "setup_minutes": setup_minutes,
                "imaging_minutes": imaging_minutes,
                "planner_score": block["planner_score"],
                "reason": block["reason"],
                "recommended_sub_exposure_seconds": settings[
                    "sub_exposure_seconds"
                ],
                "recommended_gain": settings["gain"],
                "recommended_filter": settings["filter"],
                "recommendation_source": settings["source"],
                "planned_subframes": _planned_subframes(
                    settings=settings,
                    imaging_minutes=imaging_minutes,
                ),
                "setup_changes": _setup_changes(
                    previous=previous_candidate,
                    selected=block["candidate"],
                ),
            }
        )
        previous_candidate = block["candidate"]

    return scheduled_blocks[:MAXIMUM_BLOCKS]


def get_tonight_schedule(db: Session) -> Dict:
    planner = get_tonight_plan(db)
    decision = planner["decision"]
    fallback = planner.get("best_theoretical_target")
    notes = list(planner["notes"])
    blocks = []

    if decision == "Do Not Image":
        notes.append(
            "The scheduler is advisory only and will not create imaging blocks "
            "while the weather decision is Do Not Image."
        )
    else:
        candidates = [planner.get("recommended_target"), *planner["alternatives"]]
        blocks = build_schedule_blocks(candidates)

        if not blocks:
            notes.append(
                "No schedule blocks met the 30-minute minimum duration."
            )

        if decision == "Use Caution":
            notes.append(
                "Review live conditions before starting any scheduled block."
            )

    allocated_minutes = sum(
        block["duration_minutes"]
        for block in blocks
    )
    unscheduled_dark_minutes = max(
        _darkness_minutes(planner["darkness"])
        - allocated_minutes,
        0,
    )

    if decision != "Do Not Image" and unscheduled_dark_minutes:
        notes.append(
            f"{unscheduled_dark_minutes} dark minute(s) remain unscheduled "
            "because no additional block met the target and minimum-duration "
            "requirements."
        )

    date = datetime.now(ZoneInfo(TIMEZONE)).date().isoformat()

    return {
        "date": date,
        "decision": decision,
        "advisory_only": True,
        "blocks": blocks,
        "allocated_minutes": allocated_minutes,
        "unscheduled_dark_minutes": unscheduled_dark_minutes,
        "weather": planner["weather"],
        "moon": planner["moon"],
        "darkness": planner["darkness"],
        "notes": notes,
        "fallback_target": (
            fallback["advisor"]["object"] if fallback else None
        ),
    }
