import math
from datetime import datetime, timezone

from sqlalchemy import select
from app.models import Profile
from app.models.capture_history import HostedCaptureSession, LibrarySyncCredential
from app.schemas.capture_history import normalize_target
from app.services.advisor_service import get_catalog_exposure_advice, build_advisor_recommendation
from app.services.portfolio_service import build_portfolio_target


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


def library_summary(db, user_id):
    rows = db.scalars(select(HostedCaptureSession).where(HostedCaptureSession.user_id == user_id)).all()
    totals = {}
    for row in rows:
        name = normalize_target(row.target)
        item = totals.setdefault(name, {"seconds": 0.0, "frames": 0, "sessions": 0, "filters": {}})
        item["seconds"] += row.integration_seconds
        item["frames"] += row.frame_count
        item["sessions"] += 1
        item["filters"][row.filter_name] = item["filters"].get(row.filter_name, 0) + row.integration_seconds
    credential = db.get(LibrarySyncCredential, user_id)
    targets = []
    for name, item in sorted(totals.items()):
        progress = build_portfolio_target(name, item["seconds"] / 3600)
        targets.append({"object": name, **item, "hours": round(item["seconds"] / 3600, 2),
                        "goal_hours": progress["goal_hours"], "remaining_hours": progress["remaining_hours"],
                        "progress_percent": progress["progress_percent"]})
    return {"basis": "Verified raw exposures; excludes failed frames, calibration and duplicate stacks. Quality has not been graded.",
            "session_count": len(rows), "last_synced_at": credential.last_synced_at if credential else None,
            "targets": targets}


def progress_map(summary):
    return {row["object"]: row for row in summary["targets"]}


def history_advice(object_name, progress):
    advice = get_catalog_exposure_advice(object_name)
    entry = (progress or {}).get(normalize_target(object_name))
    if entry is None:
        return advice
    current = entry["seconds"]
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
