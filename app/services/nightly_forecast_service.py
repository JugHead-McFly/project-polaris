"""Prospective, owner-scoped dusk-to-dawn forecast comparisons.

No reconstruction of past forecasts. Two immutable snapshots, kept separate by
lead time and source mix; satellite observations use the exact saved window.
"""
from datetime import datetime, timedelta, timezone
import logging
from copy import deepcopy
from zoneinfo import ZoneInfo

from app.models import NightlyForecast
from app.services.astronomy_service import get_darkness_window_datetimes
from app.services.cloud_forecast_service import cloud_value
from app.services.hosted_account_service import planning_context_from_observatory
from app.services.satellite_cloud_service import fetch_reference, utc
from app.services.weather_service import get_weather_summary

LOGGER = logging.getLogger(__name__)
HORIZONS = {"afternoon": 6, "dusk": 0}
METHOD = "dark-window-v1"
MIN_NIGHTS = 30
MIN_COVERAGE = .9
CLEAR_LIMIT = 20  # Diagnostic threshold only, never a recommendation rule.


def forecast_window(weather, start, end, timezone_name):
    """Clip hourly values to darkness; reject overlapping provider intervals."""
    intervals = []
    for stamp, row in weather.get("hourly_forecast", {}).items():
        try:
            at = datetime.fromisoformat(stamp)
            if at.tzinfo is None:
                at = at.replace(tzinfo=ZoneInfo(timezone_name))
            at = utc(at)
        except (TypeError, ValueError):
            continue
        a, b = max(start, at), min(end, at + timedelta(hours=1))
        value = cloud_value(row.get("cloud_cover_percent"))
        if b <= a or value is None:
            continue
        intervals.append({"start": a.isoformat(), "end": b.isoformat(),
                          "cloud_cover_percent": value,
                          "sources": row.get("cloud_forecast_sources") or [{"provider": weather.get("provider") or "unknown", "cloud_cover_percent": value}]})
    intervals.sort(key=lambda r: r["start"])
    covered = weighted = 0
    previous = start
    for row in intervals:
        a, b = datetime.fromisoformat(row["start"]), datetime.fromisoformat(row["end"])
        if a < previous:
            raise ValueError("Overlapping forecast hours")
        duration = (b-a).total_seconds()
        covered += duration
        weighted += duration * row["cloud_cover_percent"]
        previous = b
    coverage = covered/(end-start).total_seconds()
    source_mix = sorted({"+".join(sorted(s["provider"] for s in row["sources"])) for row in intervals})
    return {"average": weighted/covered if covered and coverage >= MIN_COVERAGE else None,
            "coverage": coverage, "intervals": intervals,
            "source_mix": source_mix, "method": METHOD}


def observation_summary(cells):
    total = sum(cell["seconds"] for cell in cells)
    covered = weighted = gap = largest_gap = 0
    used_scans = set()
    for cell in cells:
        reference = cell.get("reference") or {}
        value = cloud_value(reference.get("cloud_cover_percent"))
        scan = reference.get("scan_midpoint")
        good = (reference.get("status") == "usable" and value is not None
                and reference.get("good_pixel_fraction", 0) >= .9
                and abs(reference.get("time_offset_seconds", 9999)) <= 180
                and reference.get("forecast_for") == cell["target"]
                and scan and scan not in used_scans)
        if good:
            used_scans.add(scan)
            covered += cell["seconds"]
            weighted += cell["seconds"] * value
            gap = 0
        else:
            gap += cell["seconds"]
            largest_gap = max(largest_gap, gap)
    coverage = covered/total if total else 0
    adequate = coverage >= MIN_COVERAGE and largest_gap <= 1800
    return {"average": weighted/covered if covered and adequate else None,
            "coverage": coverage, "largest_gap_minutes": largest_gap/60,
            "adequate": adequate, "method": METHOD}


def collect_nightly(db, *, user_id, observatory, now=None,
                    weather_fetch=get_weather_summary, satellite_fetch=fetch_reference,
                    darkness=get_darkness_window_datetimes, clock=lambda: datetime.now(timezone.utc)):
    if observatory.user_id != user_id:
        raise ValueError("Observatory owner mismatch")
    now = utc(now or clock())
    context = planning_context_from_observatory(observatory)
    _, dusk, dawn = darkness(reference_datetime=now, observatory=context)
    start, end = utc(dusk), utc(dawn)
    if end <= start or end-start > timedelta(hours=24):
        raise ValueError("No valid astronomical darkness window")
    day = start.astimezone(ZoneInfo(observatory.timezone_name)).date()
    row = db.query(NightlyForecast).filter_by(user_id=user_id, observatory_id=observatory.id, night_date=day).with_for_update().one_or_none()
    if row is None:
        row = NightlyForecast(user_id=user_id, observatory_id=observatory.id, night_date=day,
            window_start=start, window_end=end, latitude=observatory.latitude,
            longitude=observatory.longitude, timezone_name=observatory.timezone_name,
            forecasts={}, observation={})
        db.add(row)
        db.commit()
    start, end = utc(row.window_start), utc(row.window_end)
    snapshots = dict(row.forecasts)
    report = {"snapshots_saved": 0, "satellite_samples": 0, "completed_nights": 0}
    for horizon, lead in HORIZONS.items():
        if horizon in snapshots:
            continue
        due = start-timedelta(hours=lead)
        if (row.latitude, row.longitude) != (observatory.latitude, observatory.longitude):
            snapshots[horizon] = {"status": "location_changed", "scheduled_at": due.isoformat()}
        elif now > due:
            snapshots[horizon] = {"status": "missed", "scheduled_at": due.isoformat()}
        elif due-timedelta(minutes=10) <= now <= due:
            weather = weather_fetch(context.postal_code or "", observatory=context)
            captured = utc(clock())
            # Never save a late forecast under an earlier lead-time label.
            if captured > due:
                snapshots[horizon] = {"status": "missed", "scheduled_at": due.isoformat()}
                continue
            fetched = datetime.fromisoformat(weather.get("fetched_at", "").replace("Z", "+00:00"))
            if fetched.tzinfo is None or not timedelta(0) <= captured-utc(fetched) <= timedelta(minutes=10):
                raise ValueError("Forecast freshness cannot be established")
            snapshot = forecast_window(weather, start, end, row.timezone_name)
            snapshot.update(status="saved" if snapshot["average"] is not None else "insufficient_forecast",
                            captured_at=captured.isoformat(), fetched_at=fetched.isoformat(),
                            scheduled_at=due.isoformat(), lead_hours=(start-captured).total_seconds()/3600)
            snapshots[horizon] = snapshot
            report["snapshots_saved"] += 1
    row.forecasts = snapshots
    db.commit()

    # Catch up after dawn, across restarts. Stored coordinates never follow later
    # changes to the home. No raw satellite files accumulate on the server.
    pending = db.query(NightlyForecast).filter(
        NightlyForecast.user_id == user_id, NightlyForecast.observatory_id == observatory.id,
        NightlyForecast.window_end < now-timedelta(minutes=30),
        NightlyForecast.window_end > now-timedelta(days=14),
    ).order_by(NightlyForecast.window_start).all()
    budget = 24
    for night in pending:
        if night.observation.get("complete"):
            continue
        observation = deepcopy(night.observation)
        cells = observation.get("cells")
        if cells is None:
            cells = []
            at, finish = utc(night.window_start), utc(night.window_end)
            while at < finish:
                stop = min(finish, at+timedelta(minutes=5))
                cells.append({"target": (at+(stop-at)/2).isoformat(),
                              "seconds": (stop-at).total_seconds(), "attempts": 0})
                at = stop
        for cell in cells:
            if cell.get("reference") or cell["attempts"] >= 3 or budget <= 0:
                continue
            budget -= 1
            cell["attempts"] += 1
            try:
                cell["reference"] = satellite_fetch(datetime.fromisoformat(cell["target"]), night.latitude, night.longitude)
                scan = datetime.fromisoformat(cell["reference"]["scan_midpoint"])
                if not utc(night.window_start) <= utc(scan) < utc(night.window_end):
                    cell["reference"] = {**cell["reference"], "status": "outside_darkness_window"}
                report["satellite_samples"] += 1
            except Exception:
                cell.pop("reference", None)
                LOGGER.exception("Nightly satellite sample will retry within its retry budget")
            # Persist each result so an interrupted batch is resumable.
            night.observation = {"cells": cells, "complete": False}
            db.commit()
        complete = all(c.get("reference") or c["attempts"] >= 3 for c in cells)
        night.observation = {"cells": cells, "complete": complete,
                             **observation_summary(cells), "updated_at": utc(clock()).isoformat()}
        db.commit()
        if complete:
            report["completed_nights"] += 1
        if budget <= 0:
            break
    return report


def nightly_summary(db, *, user_id, observatory_id):
    rows = db.query(NightlyForecast).filter_by(user_id=user_id, observatory_id=observatory_id).order_by(NightlyForecast.window_start.desc()).limit(120).all()
    horizons = []
    details = []
    for horizon in HORIZONS:
        candidates = [(row, row.forecasts.get(horizon, {})) for row in rows]
        current = next(((r.latitude, r.longitude, f.get("source_mix"), f.get("method")) for r, f in candidates if f.get("status") == "saved"), None)
        errors = []
        missed_clear = unexpected_cloud = 0
        for row, forecast in candidates:
            observation = row.observation
            comparable = (current is not None and forecast.get("status") == "saved"
                and (row.latitude, row.longitude, forecast.get("source_mix"), forecast.get("method")) == current
                and observation.get("complete") and observation.get("adequate")
                and observation.get("method") == METHOD)
            error = forecast["average"]-observation["average"] if comparable else None
            details.append({"night": row.night_date.isoformat(), "horizon": horizon,
                "forecast": forecast.get("average"), "observed": observation.get("average") if observation.get("complete") else None,
                "coverage": observation.get("coverage", 0), "comparable": bool(comparable),
                "status": "compared" if comparable else forecast.get("status", "scheduled"),
                "start": utc(row.window_start).isoformat(), "end": utc(row.window_end).isoformat()})
            if comparable:
                errors.append(error)
                missed_clear += forecast["average"] > CLEAR_LIMIT >= observation["average"]
                unexpected_cloud += forecast["average"] <= CLEAR_LIMIT < observation["average"]
        horizons.append({"horizon": horizon, "count": len(errors),
            "within_10": sum(abs(e) <= 10 for e in errors),
            "bias": sum(errors)/len(errors) if errors else None,
            "missed_clear": missed_clear, "unexpected_cloud": unexpected_cloud,
            "review_ready": len(errors) >= MIN_NIGHTS})
    return {"review_after": MIN_NIGHTS, "horizons": horizons, "nights": details,
            "clear_threshold": CLEAR_LIMIT,
            "completed_nights": sum(bool(r.observation.get("complete") and r.observation.get("adequate")) for r in rows)}
