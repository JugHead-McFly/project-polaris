from datetime import datetime
from typing import Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.observatory import TIMEZONE
from app.services.planner_service import get_tonight_plan


SCHEDULE_TIME_FORMAT = "%Y-%m-%d %I:%M %p"
MINIMUM_BLOCK_MINUTES = 30
MAXIMUM_BLOCKS = 4


def _parse_schedule_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    return datetime.strptime(
        value,
        SCHEDULE_TIME_FORMAT,
    ).replace(tzinfo=ZoneInfo(TIMEZONE))


def _format_schedule_time(value: datetime) -> str:
    return value.strftime(SCHEDULE_TIME_FORMAT)


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
    blocks = []

    for start, end in zip(boundaries, boundaries[1:]):
        active = [
            window["candidate"]
            for window in windows
            if window["start"] <= start and window["end"] >= end
        ]

        if not active:
            continue

        selected = max(
            active,
            key=lambda candidate: candidate["planner_score"],
        )

        if blocks and blocks[-1]["object"] == selected["advisor"]["object"]:
            blocks[-1]["end_datetime"] = end
            continue

        blocks.append(
            {
                "object": selected["advisor"]["object"],
                "start_datetime": start,
                "end_datetime": end,
                "planner_score": selected["planner_score"],
                "reason": "Highest-ranked observable target for this time window.",
            }
        )

    scheduled_blocks = []
    for block in blocks:
        duration_minutes = int(
            (block["end_datetime"] - block["start_datetime"])
            .total_seconds()
            / 60
        )
        if duration_minutes < MINIMUM_BLOCK_MINUTES:
            continue

        scheduled_blocks.append(
            {
                "object": block["object"],
                "start": _format_schedule_time(block["start_datetime"]),
                "end": _format_schedule_time(block["end_datetime"]),
                "duration_minutes": duration_minutes,
                "planner_score": block["planner_score"],
                "reason": block["reason"],
            }
        )

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

    date = datetime.now(ZoneInfo(TIMEZONE)).date().isoformat()

    return {
        "date": date,
        "decision": decision,
        "advisory_only": True,
        "blocks": blocks,
        "weather": planner["weather"],
        "moon": planner["moon"],
        "darkness": planner["darkness"],
        "notes": notes,
        "fallback_target": (
            fallback["advisor"]["object"] if fallback else None
        ),
    }
