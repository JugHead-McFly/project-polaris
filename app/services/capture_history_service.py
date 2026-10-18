import math
from datetime import datetime, timezone

from sqlalchemy import select
from app.models import Profile
from app.models.capture_history import HostedCaptureSession, LibrarySyncCredential
from app.schemas.capture_history import normalize_target
from app.services.advisor_service import get_catalog_exposure_advice, build_advisor_recommendation
from app.services.portfolio_service import build_portfolio_target


from app.core.request_timing import timed

def import_manifest(db, user_id, manifest):
    keys = [row.source_key for row in manifest.sessions]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate source sessions in manifest")
    # Serialize this account's syncs. Other accounts never share this lock.
    db.scalar(select(Profile).where(Profile.user_id == user_id).with_for_update())
    credential = db.scalar(select(LibrarySyncCredential).where(
        LibrarySyncCredential.user_id == user_id).with_for_update())
    existing = {row.source_key: row for row in db.scalars(select(HostedCaptureSession).where(
        HostedCaptureSession.user_id == user_id)).all()}
    changed = 0
    for item in manifest.sessions:
        row = existing.get(item.source_key)
        values = item.model_dump()
        if row is not None and row.evidence_hash == item.evidence_hash:
            # Evidence identity cannot be reused to silently alter its interpretation.
            if any(getattr(row, key) != value for key, value in values.items() if key != "captured_at"):
                raise ValueError("Session metadata differs for unchanged evidence")
            continue
        if row is None:
            row = HostedCaptureSession(user_id=user_id, **values)
            db.add(row)
        else:
            for key, value in values.items():
                setattr(row, key, value)
        changed += 1
    if credential is not None:
        credential.last_synced_at = datetime.now(timezone.utc)
    db.commit()
    return {"sessions_received": len(keys), "sessions_changed": changed}


@timed("capture_history")
def library_summary(db, user_id):
    from app.services.legacy_capture_service import legacy_summary
    rows = db.scalars(select(HostedCaptureSession).where(HostedCaptureSession.user_id == user_id)).all()
    totals = {}
    for row in rows:
        name = normalize_target(row.target)
        item = totals.setdefault(name, {"seconds": 0.0, "frames": 0, "sessions": 0, "filters": {}, "filter_progress": {}})
        item["seconds"] += row.integration_seconds
        item["frames"] += row.frame_count
        item["sessions"] += 1
        item["filters"][row.filter_name] = item["filters"].get(row.filter_name, 0) + row.integration_seconds
        by_filter = item["filter_progress"].setdefault(row.filter_name, {
            "filter": row.filter_name, "captured_seconds": 0.0, "captured_frames": 0,
            "quality_state": "unassessed", "accepted_seconds": None, "rejected_seconds": None,
            "accepted_frames": None, "rejected_frames": None,
            "goal_seconds": None, "goal_basis": "Shared target goal; no separate filter allocation",
        })
        by_filter["captured_seconds"] += row.integration_seconds
        by_filter["captured_frames"] += row.frame_count
    credential = db.get(LibrarySyncCredential, user_id)
    targets = []
    for name, item in sorted(totals.items()):
        item["filter_progress"] = [dict(values, unassessed_seconds=values["captured_seconds"],
            unassessed_frames=values["captured_frames"]) for _, values in sorted(item["filter_progress"].items())]
        progress = build_portfolio_target(name, item["seconds"] / 3600)
        targets.append({"object": name, **item, "hours": round(item["seconds"] / 3600, 2),
                        "goal_hours": progress["goal_hours"], "remaining_hours": progress["remaining_hours"],
                        "progress_percent": progress["progress_percent"]})
    return {"basis": "Verified raw exposures; excludes failed frames, calibration and duplicate stacks. Quality has not been graded.",
            "session_count": len(rows), "last_synced_at": credential.last_synced_at if credential else None,
            "targets": targets, "legacy": legacy_summary(db, user_id)}


def progress_map(summary):
    return {row["object"]: row for row in summary["targets"]}


def filter_progress_for_target(object_name, progress):
    from app.services.deep_sky_catalog import get_entry
    entry = get_entry(object_name)
    totals = {}
    for name, record in (progress or {}).items():
        other = get_entry(name)
        if normalize_target(name) != normalize_target(object_name) and not (entry and other and entry['id'] == other['id']):
            continue
        for row in record.get('filter_progress', []):
            item = totals.setdefault(row['filter'], dict(row, captured_seconds=0.0, captured_frames=0,
                unassessed_seconds=0.0, unassessed_frames=0))
            for field in ('captured_seconds', 'captured_frames', 'unassessed_seconds', 'unassessed_frames'):
                item[field] += row[field]
    return [totals[name] for name in sorted(totals)]


def history_advice(object_name, progress):
    from app.services.deep_sky_catalog import get_entry
    advice = get_catalog_exposure_advice(object_name)
    catalog_entry = get_entry(object_name)
    matches = []
    for name, item in (progress or {}).items():
        other = get_entry(name)
        if normalize_target(name) == normalize_target(object_name) or (catalog_entry and other and catalog_entry["id"] == other["id"]):
            matches.append((name, item))
    if not matches:
        return advice
    current = sum(item["seconds"] for _, item in matches)
    # Read-only alias reconciliation. Retain the smallest existing goal so a
    # newly recognized designation never reopens a completed project.
    retained_goal = min([advice["goal_hours"]] + [get_catalog_exposure_advice(name)["goal_hours"] for name, _ in matches])
    if retained_goal < advice["goal_hours"]:
        advice["goal_hours"] = retained_goal
        advice["integration_goal_note"] = "Existing lower integration goal retained across catalog aliases; observation records are unchanged."
    advice["goal_options"] = [{**option, "hours": retained_goal * factor} for option, factor in zip(advice["goal_options"], (0.5, 1, 2))]
    remaining = max(0, advice["goal_hours"] * 3600 - current)
    exposure = advice["recommended_sub_exposure_seconds"]
    frames = math.ceil(remaining / exposure) if exposure else None
    advice.update(current_integration_seconds=current, current_integration_hours=round(current / 3600, 2),
                  remaining_seconds=remaining, remaining_hours=round(remaining / 3600, 2),
                  additional_subframes_needed=frames, status="Goal Reached" if not remaining else "Continue Imaging")
    advice["recommendation"] = build_advisor_recommendation(
        object_name=object_name, remaining_hours=advice["remaining_hours"], additional_subframes=frames,
        sub_exposure_seconds=exposure, gain=advice["recommended_gain"], filter_name=advice["recommended_filter"])
    return advice
