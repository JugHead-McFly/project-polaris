import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.observatory import TIMEZONE
from app.core.planning_context import ObservatoryContext
from app.core.planning_context import use_observatory_context
from app.data.rig_profiles import get_rig_profile
from app.data.targets import get_target_common_name
from app.services.planner_service import get_tonight_plan


SCHEDULE_TIME_FORMAT = "%Y-%m-%d %I:%M %p"
MINIMUM_BLOCK_MINUTES = 30
SETUP_BUFFER_MINUTES = 5
EQUIPMENT_CHANGE_SCORE_MARGIN = 12.0
DWARF_MAXIMUM_SUBFRAMES_PER_RUN = 999


def _parse_schedule_time(
    value: Optional[str],
    timezone_name: str = TIMEZONE,
) -> Optional[datetime]:
    if not value:
        return None

    parsed = datetime.fromisoformat(value) if "T" in value else datetime.strptime(value, SCHEDULE_TIME_FORMAT)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(timezone_name))
    return parsed.astimezone(timezone.utc)


def _format_schedule_time(
    value: datetime,
    timezone_name: Optional[str] = None,
) -> str:
    if timezone_name:
        value = value.astimezone(ZoneInfo(timezone_name))
    return value.strftime("%Y-%m-%d %I:%M:%S %p" if value.second else SCHEDULE_TIME_FORMAT)


def _darkness_minutes(
    darkness: Dict,
    timezone_name: str = TIMEZONE,
) -> float:
    start = _parse_schedule_time(
        darkness.get("astronomical_darkness_start_at") or darkness.get("astronomical_darkness_start"),
        timezone_name=timezone_name,
    )
    end = _parse_schedule_time(
        darkness.get("astronomical_darkness_end_at") or darkness.get("astronomical_darkness_end"),
        timezone_name=timezone_name,
    )

    if start is None or end is None or end <= start:
        return 0

    return (end - start).total_seconds() / 60


def _candidate_windows(
    candidates: Iterable[Dict],
    timezone_name: str = TIMEZONE,
) -> List[Dict]:
    windows = []

    for candidate in candidates:
        if not candidate or not candidate.get("observable"):
            continue

        intervals = candidate.get("schedule_windows")
        if intervals is None:
            intervals = [{"start": candidate.get("recommended_start"), "end": candidate.get("recommended_end")}]
        for interval in intervals:
            start = _parse_schedule_time(interval.get("start"), timezone_name)
            end = _parse_schedule_time(interval.get("end"), timezone_name)
            if start is not None and (start.second or start.microsecond):
                start = start.replace(second=0, microsecond=0) + timedelta(minutes=1)
            if end is not None:
                end = end.replace(second=0, microsecond=0)
            if start is not None and end is not None and end > start:
                windows.append({"candidate": candidate, "start": start, "end": end})

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
        "confidence_label": advisor.get("settings_confidence"),
        "reasons": advisor.get("settings_reasons") or [],
        "setup_guidance": advisor.get("settings_setup_guidance") or [],
        "adjustments": advisor.get("settings_adjustments") or [],
    }


def _equipment_setting_changes(
    previous: Dict,
    selected: Dict,
) -> List[str]:
    previous_settings = _advisor_settings(previous)
    selected_settings = _advisor_settings(selected)
    changes = []

    comparisons = (
        ("filter", "filter"),
        ("gain", "gain"),
        ("sub_exposure_seconds", "sub-exposure"),
    )
    for key, label in comparisons:
        old_value = previous_settings[key]
        new_value = selected_settings[key]

        if (
            old_value is not None
            and new_value is not None
            and old_value != new_value
        ):
            if key == "gain":
                old_display = f"{float(old_value):g}"
                new_display = f"{float(new_value):g}"
            elif key == "sub_exposure_seconds":
                old_display = f"{float(old_value):g} seconds"
                new_display = f"{float(new_value):g} seconds"
            else:
                old_display = str(old_value)
                new_display = str(new_value)
            changes.append(
                f"Change {label} to {new_display} (from {old_display})"
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

    changes.extend(settings["setup_guidance"])

    return changes


def _planned_subframes(
    settings: Dict,
    imaging_minutes: float,
) -> Optional[int]:
    sub_exposure_seconds = settings["sub_exposure_seconds"]
    if sub_exposure_seconds is None or sub_exposure_seconds <= 0:
        return None

    capacity = int(
        (imaging_minutes * 60 + 1e-7) / sub_exposure_seconds
    )
    additional_needed = settings["additional_subframes"]

    if additional_needed is not None:
        return min(capacity, additional_needed)

    return capacity


def _subframe_runs(
    planned_subframes: Optional[int],
    frame_limit: Optional[int] = DWARF_MAXIMUM_SUBFRAMES_PER_RUN,
) -> List[int]:
    """Split a scheduled run when the selected rig has a known frame limit."""
    if (
        planned_subframes is None
        or planned_subframes <= 0
        or frame_limit is None
        or frame_limit <= 0
    ):
        return []

    full_runs, remainder = divmod(
        planned_subframes,
        frame_limit,
    )
    runs = [frame_limit] * full_runs
    if remainder:
        runs.append(remainder)
    return runs


def _dwarf_run_blocks(
    block: Dict,
    settings: Dict,
    planned_subframes: Optional[int],
    setup_changes: List[str],
    frame_limit: Optional[int] = DWARF_MAXIMUM_SUBFRAMES_PER_RUN,
    frame_limit_label: Optional[str] = "DWARF",
    timezone_name: str = TIMEZONE,
) -> List[Dict]:
    """Turn an oversized block into individually startable rig-limited runs."""
    subframe_runs = _subframe_runs(planned_subframes, frame_limit)
    exposure_seconds = settings["sub_exposure_seconds"]
    frame_limit_reason = (
        f"{frame_limit_label or 'This rig'} has a recorded "
        f"{frame_limit}-frame single-run limit."
        if frame_limit is not None
        else None
    )

    base_block = {
        "object": block["object"],
        "common_name": get_target_common_name(block["object"]),
        "planner_score": block["planner_score"],
        "recommended_sub_exposure_seconds": exposure_seconds,
        "recommended_gain": settings["gain"],
        "recommended_filter": settings["filter"],
        "recommendation_source": settings["source"],
        "settings_confidence": settings["confidence_label"],
        "settings_reasons": settings["reasons"],
        "settings_adjustments": settings["adjustments"],
        "total_planned_subframes": planned_subframes,
        "frame_limit": frame_limit,
        "frame_limit_label": frame_limit_label,
        "frame_limit_reason": frame_limit_reason,
    }

    if len(subframe_runs) <= 1 or not exposure_seconds:
        return [
            {
                **base_block,
                "start_at": block["start_datetime"].isoformat(),
                "end_at": block["end_datetime"].isoformat(),
                "start": _format_schedule_time(
                    block["start_datetime"],
                    timezone_name=timezone_name,
                ),
                "end": _format_schedule_time(
                    block["end_datetime"],
                    timezone_name=timezone_name,
                ),
                "duration_minutes": (
                    (
                        block["end_datetime"]
                        - block["start_datetime"]
                    ).total_seconds()
                    / 60
                ),
                "setup_minutes": block["setup_minutes"],
                "imaging_minutes": block["imaging_minutes"],
                "reason": block["reason"],
                "planned_subframes": planned_subframes,
                "subframe_runs": subframe_runs,
                "run_number": 1,
                "total_runs": 1,
                "setup_changes": setup_changes,
            }
        ]

    run_blocks = []
    imaging_start = block["start_datetime"] + timedelta(
        minutes=block["setup_minutes"],
    )

    for index, run_subframes in enumerate(subframe_runs, start=1):
        run_start = (
            block["start_datetime"]
            if index == 1
            else imaging_start
        )
        run_end = imaging_start + timedelta(
            seconds=run_subframes * exposure_seconds,
        )
        imaging_minutes = run_subframes * exposure_seconds / 60
        setup_minutes = block["setup_minutes"] if index == 1 else 0

        run_blocks.append(
            {
                **base_block,
                "start_at": run_start.isoformat(),
                "end_at": run_end.isoformat(),
                "start": _format_schedule_time(
                    run_start,
                    timezone_name=timezone_name,
                ),
                "end": _format_schedule_time(
                    run_end,
                    timezone_name=timezone_name,
                ),
                "duration_minutes": setup_minutes + imaging_minutes,
                "setup_minutes": setup_minutes,
                "imaging_minutes": imaging_minutes,
                "reason": (
                    block["reason"]
                    if index == 1
                    else (
                        "Continue after the recorded "
                        f"{frame_limit_label or 'rig'} "
                        f"{frame_limit}-frame run limit."
                    )
                ),
                "planned_subframes": run_subframes,
                "subframe_runs": [run_subframes],
                "run_number": index,
                "total_runs": len(subframe_runs),
                "setup_changes": (
                    setup_changes
                    if index == 1
                    else [
                        "When the previous run completes, start "
                        f"run {index} with {run_subframes} frames."
                    ]
                ),
            }
        )
        imaging_start = run_end

    return run_blocks


def _remaining_imaging_minutes(candidate: Dict) -> Optional[float]:
    advisor = candidate.get("advisor", {})
    remaining_seconds = advisor.get("remaining_seconds")

    settings = _advisor_settings(candidate)
    budgets = [max(remaining_seconds, 0)] if remaining_seconds is not None else []
    if (
        settings["additional_subframes"] is not None
        and settings["sub_exposure_seconds"] is not None
    ):
        budgets.append(
            settings["additional_subframes"]
            * settings["sub_exposure_seconds"]
        )
    if not budgets:
        return None
    seconds = min(budgets)
    exposure = settings["sub_exposure_seconds"]
    if exposure and exposure > 0:
        seconds = math.floor(seconds / exposure) * exposure
    return seconds / 60


def build_schedule_blocks(
    candidates: Iterable[Dict],
    timezone_name: str = TIMEZONE,
    rig_profile_key: Optional[str] = None,
    dark_start: Optional[datetime] = None,
    dark_end: Optional[datetime] = None,
) -> List[Dict]:
    """Build a non-overlapping, advisory schedule from Planner V2 windows."""
    windows = _candidate_windows(
        candidates,
        timezone_name=timezone_name,
    )
    for window in windows:
        if dark_start is not None:
            window["start"] = max(window["start"], dark_start)
        if dark_end is not None:
            window["end"] = min(window["end"], dark_end)
    windows = [window for window in windows if window["end"] > window["start"]]
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

    def viable(window):
        name = window["candidate"]["advisor"]["object"]
        continuing = bool(blocks and blocks[-1]["object"] == name and blocks[-1]["end_datetime"] == cursor)
        setup = 0 if continuing else SETUP_BUFFER_MINUTES
        available = (window["end"] - cursor).total_seconds() / 60 - setup
        budget = remaining_minutes[name]
        if budget is not None:
            available = min(available, budget)
        exposure = _advisor_settings(window["candidate"])["sub_exposure_seconds"]
        if exposure and exposure > 0:
            available = math.floor((available * 60 + 1e-7) / exposure) * exposure / 60
        return available > 0 and (continuing or setup + available >= MINIMUM_BLOCK_MINUTES)

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
                and viable(window)
            )
        ]

        if not active:
            cursor = next_boundary
            continue

        highest_ranked = max(
            active,
            key=lambda candidate: candidate["planner_score"],
        )
        # Preserve finite integration on flexible targets for later hours when
        # another suitable target's window will have closed.
        def active_end(candidate):
            return max(window["end"] for window in windows
                       if window["candidate"] is candidate and window["start"] <= cursor < window["end"])

        if remaining_minutes[highest_ranked["advisor"]["object"]] is not None:
            highest_ranked = min(active, key=lambda candidate: (active_end(candidate), -candidate["planner_score"]))
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
                and (remaining_minutes[current_object] is None
                     or active_end(active_current) <= active_end(highest_ranked))
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
            or blocks[-1]["end_datetime"] != cursor
        )
        # Commit a viable minimum block before considering another rising target.
        # Previously short allocations were charged to the goal then discarded.
        exposure = _advisor_settings(selected)["sub_exposure_seconds"]
        setup = SETUP_BUFFER_MINUTES if starting_new_block else 0
        minimum_imaging_seconds = (MINIMUM_BLOCK_MINUTES - setup) * 60 if starting_new_block else 0
        if exposure and exposure > 0:
            minimum_imaging_seconds = max(exposure, math.ceil(minimum_imaging_seconds / exposure) * exposure)
        next_boundary = min(active_end(selected), max(next_boundary, cursor + timedelta(seconds=setup * 60 + minimum_imaging_seconds)))
        interval_minutes = (next_boundary - cursor).total_seconds() / 60
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
        if exposure and exposure > 0:
            imaging_minutes = math.floor((imaging_minutes * 60 + 1e-7) / exposure) * exposure / 60
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
    rig_profile = get_rig_profile(rig_profile_key or "")
    frame_limit = (
        rig_profile.frame_limit
        if rig_profile is not None
        else (None if rig_profile_key else DWARF_MAXIMUM_SUBFRAMES_PER_RUN)
    )
    frame_limit_label = (
        f"{rig_profile.manufacturer} {rig_profile.model}"
        if rig_profile is not None
        else (None if rig_profile_key else "DWARF")
    )
    for block in blocks:
        duration_minutes = (
            (block["end_datetime"] - block["start_datetime"])
            .total_seconds()
            / 60
        )
        if duration_minutes < MINIMUM_BLOCK_MINUTES:
            continue

        settings = _advisor_settings(block["candidate"])
        setup_minutes = block["setup_minutes"]
        imaging_minutes = block["imaging_minutes"]

        planned_subframes = _planned_subframes(
            settings=settings,
            imaging_minutes=imaging_minutes,
        )

        scheduled_blocks.extend(
            _dwarf_run_blocks(
                block=block,
                settings=settings,
                planned_subframes=planned_subframes,
                setup_changes=_setup_changes(
                    previous=previous_candidate,
                    selected=block["candidate"],
                ),
                frame_limit=frame_limit,
                frame_limit_label=frame_limit_label,
                timezone_name=timezone_name,
            )
        )
        previous_candidate = block["candidate"]

    return scheduled_blocks


def _plan_end_reason(blocks, candidates):
    if not blocks:
        return None
    last = blocks[-1]
    candidate = next((item for item in candidates if item and item["advisor"]["object"] == last["object"]), None)
    if candidate is None:
        return "End of selected plan; this is not a weather cutoff."
    remaining = _remaining_imaging_minutes(candidate)
    planned = sum(block["imaging_minutes"] for block in blocks if block["object"] == last["object"])
    if remaining is not None and planned >= remaining:
        return f"{last['object']}'s remaining integration goal is allocated. No further blocks are selected; this is not a weather cutoff."
    return "End of selected plan. Additional dark time may remain; check target visibility and current conditions before extending it."


def build_tonight_schedule(
    planner: Dict,
    timezone_name: str = TIMEZONE,
    rig_profile_key: Optional[str] = None,
) -> Dict:
    """Build the advisory schedule from one Planner V3 result."""
    decision = planner["decision"]
    fallback = planner.get("best_theoretical_target")
    notes = list(planner["notes"])
    blocks = []
    candidates = planner.get("schedule_candidates", [planner.get("recommended_target"), *planner["alternatives"]])
    dark_start = _parse_schedule_time(planner["darkness"].get("astronomical_darkness_start_at") or planner["darkness"].get("astronomical_darkness_start"), timezone_name)
    dark_end = _parse_schedule_time(planner["darkness"].get("astronomical_darkness_end_at") or planner["darkness"].get("astronomical_darkness_end"), timezone_name)

    if decision == "Do Not Image":
        notes.append(
            "The scheduler is advisory only and will not create imaging blocks "
            "while the weather decision is Do Not Image."
        )
    elif dark_start is None or dark_end is None or dark_end <= dark_start:
        notes.append("No valid astronomical-darkness interval is available; no imaging blocks were created.")
    else:
        blocks = build_schedule_blocks(
            candidates,
            timezone_name=timezone_name,
            rig_profile_key=rig_profile_key,
            dark_start=dark_start,
            dark_end=dark_end,
        )

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
        _darkness_minutes(
            planner["darkness"],
            timezone_name=timezone_name,
        )
        - allocated_minutes,
        0,
    )
    gaps = []
    if dark_start is not None and dark_end is not None and dark_end > dark_start:
        cursor = dark_start
        intervals = [(datetime.fromisoformat(b["start_at"]), datetime.fromisoformat(b["end_at"])) for b in blocks]
        for start, end in [*intervals, (dark_end, dark_end)]:
            if start > cursor:
                reason = (
                    "Imaging withheld by the weather safety decision."
                    if decision == "Do Not Image" else
                    "No block selected under the remaining integration-goal, visibility and 30-minute minimum-block constraints."
                )
                gaps.append({"start": _format_schedule_time(cursor, timezone_name=timezone_name),
                             "end": _format_schedule_time(start, timezone_name=timezone_name),
                             "minutes": (start - cursor).total_seconds() / 60, "reason": reason})
            cursor = max(cursor, end)
        unscheduled_dark_minutes = max(_darkness_minutes(planner["darkness"], timezone_name) - allocated_minutes, 0)
    if gaps and decision != "Do Not Image":
        notes.append(f"{unscheduled_dark_minutes} dark minutes remain unallocated under the current target, visibility, goal and minimum-block constraints.")
    end_reason = _plan_end_reason(blocks, candidates)
    if blocks and dark_end is not None and datetime.fromisoformat(blocks[-1]["end_at"]) >= dark_end:
        end_reason = "Plan reaches the end of astronomical darkness."

    date = datetime.now(ZoneInfo(timezone_name)).date().isoformat()

    return {
        "date": date,
        "decision": decision,
        "advisory_only": True,
        "blocks": blocks,
        "allocated_minutes": allocated_minutes,
        "unscheduled_dark_minutes": unscheduled_dark_minutes,
        "end_reason": end_reason,
        "gaps": gaps,
        "weather": planner["weather"],
        "moon": planner["moon"],
        "darkness": planner["darkness"],
        "notes": notes,
        "fallback_target": (
            fallback["advisor"]["object"] if fallback else None
        ),
    }


def get_tonight_schedule(
    db: Session,
    observatory: Optional[ObservatoryContext] = None,
    *,
    use_capture_history: bool = True,
    capture_progress: Optional[Dict] = None,
) -> Dict:
    context = use_observatory_context(observatory)
    return build_tonight_schedule(
        get_tonight_plan(
            db,
            observatory=context,
            use_capture_history=use_capture_history,
            capture_progress=capture_progress,
        ),
        timezone_name=context.timezone_name,
        rig_profile_key=context.rig_profile_key,
    )
