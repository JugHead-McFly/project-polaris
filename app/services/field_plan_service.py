"""Portable copies of actual scheduled blocks; no recomputation or calendar writes."""
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from zoneinfo import ZoneInfo

FORMAT = "%Y-%m-%d %I:%M %p"
LIMIT = 128 * 1024
NOTICE = "Advisory snapshot only. Recheck Polaris and live conditions before imaging. Downloads do not update automatically."


def clean(value):
    text = str(value if value is not None else "Unknown")
    if len(text) > 4000:
        raise ValueError("Plan text exceeds portable limits")
    return " ".join(text.split())


def instant(value, zone):
    local = datetime.strptime(value, FORMAT)
    choices = {candidate.astimezone(timezone.utc) for fold in (0, 1)
               if (candidate := local.replace(tzinfo=zone, fold=fold)).astimezone(timezone.utc)
               .astimezone(zone).replace(tzinfo=None) == local}
    if len(choices) != 1:
        raise ValueError("Calendar unavailable: a scheduled time is ambiguous or nonexistent in the observing timezone")
    return choices.pop()


def ics_text(value):
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace(";", "\\;").replace(",", "\\,")


def fold_line(line):
    lines, current = [], ""
    for char in line:
        if len((current + char).encode("utf-8")) > 75:
            lines.append(current)
            current = " "
        current += char
    return "\r\n".join([*lines, current])


def _build(payload, generated, equatorial_mode_enabled=False):
    schedule = payload["schedule"]
    night = date.fromisoformat(payload["date"])
    if schedule["date"] != night.isoformat():
        raise ValueError("Plan and schedule dates disagree; refresh the plan")
    home = payload["observatory"]
    zone_name = home["timezone"]
    zone = ZoneInfo(zone_name)
    schedule_date = night
    darkness = schedule.get("darkness") or {}
    dusk, dawn = darkness.get("astronomical_darkness_start"), darkness.get("astronomical_darkness_end")
    dark_start = dark_end = None
    date_basis = "schedule date"
    if dusk or dawn:
        if not (dusk and dawn):
            raise ValueError("Incomplete darkness context; refresh the plan")
        dark_start, dark_end = instant(dusk, zone), instant(dawn, zone)
        if not timedelta(0) < dark_end - dark_start <= timedelta(hours=36):
            raise ValueError("Invalid darkness interval")
        night = dark_start.astimezone(zone).date()
        date_basis = "darkness-start date"
        if darkness.get("sunset"):
            sunset = instant(darkness["sunset"], zone)
            if not timedelta(0) <= dark_start - sunset <= timedelta(hours=24):
                raise ValueError("Sunset does not match the computed darkness window")
            night = sunset.astimezone(zone).date()
            date_basis = "sunset date"
        if schedule_date not in (night, night + timedelta(days=1)):
            raise ValueError("Schedule date does not match the computed darkness window")
    blocks = schedule["blocks"]
    if not isinstance(blocks, list) or len(blocks) > 64:
        raise ValueError("Too many scheduled blocks for portable export")
    decision = clean(schedule["decision"])
    if blocks and decision not in ("Proceed", "Use Caution"):
        raise ValueError("No usable imaging decision; refresh the plan")
    obstruction = payload.get("obstruction", {"mode": "off"})
    if obstruction.get("mode") == "off":
        spot = "Off — local obstructions are not applied"
    elif obstruction.get("mode") == "applied":
        spot = f'{clean(obstruction["name"])}; revision {clean(obstruction["revision"])}; source {clean(obstruction["source_quality"])}; reviewed {clean(obstruction["reviewed_at"])}'
    else:
        raise ValueError("Obstruction provenance unavailable")
    lines = ["POLARIS FIELD PLAN", f"Night reference: {night} (site-local {date_basis})",
             f'Site: {clean(home["name"])}', f"Timezone: {clean(zone_name)}",
             f'Rig: {clean(home.get("rig_profile_label"))}', f"Decision: {decision}",
             f'Plan run: {clean(payload.get("recommendation_run_id", "Not persisted"))}',
             f"Local obstructions: {spot}", NOTICE,
             f"EQ alignment confirmed for this calculation: {bool(equatorial_mode_enabled)}",
             f"Schedule calculation date (site local): {schedule_date}"]
    if dark_start is not None:
        lines.append(f"Astronomical darkness (site local): {clean(dusk)} → {clean(dawn)} ({clean(zone_name)})")
    header = lines.copy()
    events, previous = [], None
    for index, block in enumerate(blocks, 1):
        start, end = instant(block["start"], zone), instant(block["end"], zone)
        if end <= start or end - start > timedelta(hours=24) or (previous and start < previous):
            raise ValueError("Scheduled blocks overlap or have invalid duration")
        if dark_start is not None and (start < dark_start or end > dark_end):
            raise ValueError("Scheduled block falls outside the computed darkness window")
        if start.astimezone(zone).date() not in (night, night + timedelta(days=1)) or end.astimezone(zone).date() > night + timedelta(days=2):
            raise ValueError("Scheduled block does not belong to the observing night")
        if start.astimezone(zone).utcoffset() != end.astimezone(zone).utcoffset():
            raise ValueError("Calendar unavailable: scheduled block crosses a timezone clock change")
        previous = end
        title = f'{clean(block["object"])} — setup and capture (run {clean(block.get("run_number", 1))}/{clean(block.get("total_runs", 1))})'
        details = [title, f'{clean(block["start"])} → {clean(block["end"])} ({clean(zone_name)})',
                   f'Setup: {clean(block["setup_minutes"])} min; imaging: {clean(block["imaging_minutes"])} min',
                   f'Exposure: {clean(block.get("recommended_sub_exposure_seconds"))} s; gain: {clean(block.get("recommended_gain"))}; filter: {clean(block.get("recommended_filter"))}',
                   f'Settings source: {clean(block["recommendation_source"])}; confidence: {clean(block.get("settings_confidence"))}',
                   f'Reason: {clean(block["reason"])}']
        lines.extend(["", *details])
        events.append((title, start, end, details))
    if not blocks:
        lines.extend(["", "No scheduled imaging blocks. No calendar events are available."])
    notes = schedule.get("notes") or []
    if len(notes) > 64:
        raise ValueError("Too many plan notes")
    lines.extend(["", *[clean(note) for note in notes]])
    if schedule.get("end_reason"):
        lines.append("Plan ends: " + clean(schedule["end_reason"]))
    identity = sha256(json.dumps(lines, ensure_ascii=False).encode()).hexdigest()
    stamp = generated.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    text = "\n".join([*lines[:1], f"Snapshot generated UTC: {generated.isoformat()}", f"Snapshot: {identity[:16]}", *lines[1:]]) + "\n"
    calendar = None
    if events:
        content = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Polaris//Field Plan//EN", "CALSCALE:GREGORIAN"]
        for index, (title, start, end, details) in enumerate(events):
            description = "\n".join([*header[1:], f"Snapshot: {identity[:16]}", *details, *[clean(note) for note in notes]])
            content.extend(["BEGIN:VEVENT", f"UID:{identity}-{index}@polaris.invalid", f"DTSTAMP:{stamp}",
                            "DTSTART:" + start.strftime("%Y%m%dT%H%M%SZ"), "DTEND:" + end.strftime("%Y%m%dT%H%M%SZ"),
                            "SUMMARY:" + ics_text("Polaris: " + title), "DESCRIPTION:" + ics_text(description),
                            "STATUS:TENTATIVE", "TRANSP:TRANSPARENT", "END:VEVENT"])
        content.append("END:VCALENDAR")
        calendar = "\r\n".join(map(fold_line, content)) + "\r\n"
    if len(text.encode()) + len((calendar or "").encode()) > LIMIT:
        raise ValueError("Portable plan exceeds 128 KiB")
    return {"text": text, "calendar": calendar, "night": night.isoformat(), "snapshot_id": identity,
            "generated_at": generated.isoformat(), "unavailable_reason": None}


def build_field_plan(payload, *, equatorial_mode_enabled=False):
    """An export failure must not change or suppress the displayed recommendation."""
    try:
        return _build(payload, datetime.now(timezone.utc), equatorial_mode_enabled)
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        return {"text": None, "calendar": None, "unavailable_reason": str(error)}
