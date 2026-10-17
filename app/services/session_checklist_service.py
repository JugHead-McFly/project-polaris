from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo


SCHEDULE_TIME_FORMAT = "%Y-%m-%d %I:%M %p"


def _parse_schedule_time(
    value: Optional[str],
    timezone_name: str,
) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value) if "T" in value else datetime.strptime(value, "%Y-%m-%d %I:%M:%S %p" if value.count(":") == 2 else SCHEDULE_TIME_FORMAT)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo(timezone_name))
        return parsed.astimezone(ZoneInfo(timezone_name))
    except (ValueError, TypeError):
        return None


def _time_label(value: Optional[datetime], plan_date: date) -> Optional[str]:
    if value is None:
        return None
    label = value.strftime("%I:%M:%S %p" if value.second else "%I:%M %p").lstrip("0")
    if value.date() > plan_date:
        return f"{label} next day"
    return label


def _step(
    key: str,
    label: str,
    instruction: str,
    *,
    at: Optional[datetime] = None,
    plan_date: date,
) -> Dict:
    return {
        "key": key,
        "label": label,
        "at": at.strftime("%Y-%m-%d %I:%M:%S %p" if at.second else SCHEDULE_TIME_FORMAT) if at else None,
        "time_label": _time_label(at, plan_date),
        "instruction": instruction,
    }


def _session_actions(dew_risk: Dict) -> List[str]:
    if dew_risk.get("level") in {"high", "watch"}:
        action = dew_risk.get("action")
        if action:
            return [str(action)]
    return []


def _unavailable_checklist(plan_date: date) -> Dict:
    return {
        "status": "unavailable",
        "summary": "Polaris does not have enough schedule data to time a session.",
        "steps": [
            _step(
                "setup",
                "Set up",
                "Setup time is unavailable.",
                plan_date=plan_date,
            ),
            _step(
                "start",
                "Start imaging",
                "Start time is unavailable.",
                plan_date=plan_date,
            ),
            _step(
                "stop",
                "Stop",
                "Stop time is unavailable.",
                plan_date=plan_date,
            ),
        ],
        "actions": ["Refresh the plan before committing to setup."],
    }


def build_session_checklist(
    *,
    schedule: Dict,
    recommended_target: Optional[Dict],
    backup_target: Optional[Dict],
    dew_risk: Dict,
    timezone_name: str,
) -> Dict:
    """Translate existing plan data into a short operational checklist."""
    try:
        plan_date = date.fromisoformat(schedule.get("date", ""))
    except (TypeError, ValueError):
        plan_date = datetime.now(ZoneInfo(timezone_name)).date()

    decision = schedule.get("decision") or "Conditions Unknown"
    if decision == "Do Not Image":
        reassess_target = backup_target or recommended_target
        reassess_at = _parse_schedule_time(
            (reassess_target or {}).get("recommended_start"),
            timezone_name,
        )
        return {
            "status": "wait",
            "summary": "Wait for conditions to improve before committing to setup.",
            "steps": [
                _step(
                    "reassess",
                    "Reassess",
                    (
                        "Recheck conditions before the fallback window; image only "
                        "if Polaris changes the recommendation."
                        if reassess_at
                        else "Recheck conditions before committing to setup."
                    ),
                    at=reassess_at,
                    plan_date=plan_date,
                ),
            ],
            "actions": [],
        }

    blocks = schedule.get("blocks") or []
    if not blocks:
        return _unavailable_checklist(plan_date)

    first_block = blocks[0]
    last_block = blocks[-1]
    if first_block.get("mosaic_required"):
        from app.services.mosaic_service import MOSAIC_NOTE
        return {"status": "caution", "summary": "Manual mosaic planning is required before imaging.",
                "steps": [_step("mosaic", "Plan mosaic manually", MOSAIC_NOTE,
                                at=_parse_schedule_time(first_block.get("start_at") or first_block.get("start"), timezone_name),
                                plan_date=plan_date),
                          _step("stop", "Opportunity ends", "Finish within the scheduled visibility window; mosaic completion is not predicted.",
                                at=_parse_schedule_time(first_block.get("end_at") or first_block.get("end"), timezone_name),
                                plan_date=plan_date)],
                "actions": _session_actions(dew_risk)}
    setup_at = _parse_schedule_time(first_block.get("start_at") or first_block.get("start"), timezone_name)
    stop_at = _parse_schedule_time(last_block.get("end_at") or last_block.get("end"), timezone_name)
    setup_minutes = first_block.get("setup_minutes")
    if (
        setup_at is None
        or stop_at is None
        or isinstance(setup_minutes, bool)
        or not isinstance(setup_minutes, (int, float))
        or setup_minutes < 0
    ):
        return _unavailable_checklist(plan_date)

    start_at = (setup_at.astimezone(timezone.utc) + timedelta(minutes=float(setup_minutes))).astimezone(ZoneInfo(timezone_name))
    if start_at.astimezone(timezone.utc) > stop_at.astimezone(timezone.utc):
        return _unavailable_checklist(plan_date)

    target_name = first_block.get("object") or (
        recommended_target or {}
    ).get("object")
    target_text = str(target_name) if target_name else "the scheduled target"
    status = "caution" if decision == "Use Caution" else "ready"
    summary = (
        "Tonight has a usable scheduled session with cautions."
        if status == "caution"
        else "Tonight has a usable scheduled session."
    )
    actions = _session_actions(dew_risk)
    if any(block.get("mosaic_required") for block in blocks):
        from app.services.mosaic_service import MOSAIC_NOTE
        actions.append(MOSAIC_NOTE)
        status = "caution"
        summary += " Later mosaic opportunities require manual planning."
    return {
        "status": status,
        "summary": summary,
        "steps": [
            _step(
                "setup",
                "Set up",
                f"Prepare {target_text} and complete the scheduled setup.",
                at=setup_at,
                plan_date=plan_date,
            ),
            _step(
                "start",
                "Start imaging",
                f"Begin imaging {target_text} after setup is complete.",
                at=start_at,
                plan_date=plan_date,
            ),
            _step(
                "stop",
                "Stop",
                "End tonight's final scheduled block.",
                at=stop_at,
                plan_date=plan_date,
            ),
        ],
        "actions": actions,
    }
