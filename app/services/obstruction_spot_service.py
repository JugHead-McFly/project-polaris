"""Owner-bound surveys. No default selection or implicit unobstructed fallback."""
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import update, delete
from app.core.obstruction_profile import ObstructionProfile
from app.models.obstruction_spot import ObstructionSpot
from app.models.hosted import HostedObservatory, utc_now


def reject(code, message):
    raise HTTPException(code, message, headers={"Cache-Control": "no-store"})


def home_binding(home):
    return {key: getattr(home, key) for key in
            ("latitude", "longitude", "elevation_m", "timezone_name", "rig_profile_key")}


def owned_home(db, user, home_id, *, lock=False):
    if user.auth_mode == "local":
        reject(409, "Saved setup spots currently require a hosted observing home.")
    query = db.query(HostedObservatory).filter_by(id=home_id, user_id=user.user_id)
    home = (query.with_for_update() if lock else query).one_or_none()
    if home is None:
        reject(404, "Observing home not found.")
    return home


def spot_query(db, user, home_id):
    return db.query(ObstructionSpot).filter_by(user_id=user.user_id, observatory_id=home_id)


def availability(spot, home):
    if spot.schema_version != 1 or spot.source_quality not in ("manual_measured", "synthetic"):
        return "Unsupported survey source or version; review is required."
    if spot.source_quality == "synthetic":
        return "Synthetic example: not available for Tonight."
    if spot.home_binding != home_binding(home):
        return "Observing home or rig changed; review and save the survey again."
    try:
        ObstructionProfile.model_validate(spot.profile)
    except (ValidationError, TypeError, ValueError):
        return "Survey is invalid; review and save it again."
    return None


def describe(spot, home):
    reason = availability(spot, home)
    return {"id": str(spot.id), "observatory_id": str(spot.observatory_id),
            "name": spot.name, "revision": spot.revision, "schema_version": spot.schema_version,
            "source_quality": spot.source_quality, "profile": spot.profile,
            "reviewed_at": spot.reviewed_at, "available_for_tonight": reason is None,
            "unavailable_reason": reason}


def save_spot(db, user, home_id, payload, spot_id=None):
    home = owned_home(db, user, home_id, lock=True)
    values = dict(name=payload.name, profile=payload.profile.model_dump(mode="json"),
                  source_quality=payload.source_quality, schema_version=1,
                  home_binding=home_binding(home), reviewed_at=utc_now(), updated_at=utc_now())
    if spot_id is None:
        if payload.expected_revision is not None:
            reject(422, "A new spot must not specify a revision.")
        if spot_query(db, user, home_id).count() >= 32:
            reject(409, "A home can save up to 32 setup spots.")
        spot = ObstructionSpot(user_id=user.user_id, observatory_id=home_id, **values)
        db.add(spot)
        db.flush()
    else:
        if payload.expected_revision is None:
            reject(422, "Include the revision being edited.")
        result = db.execute(update(ObstructionSpot).where(
            ObstructionSpot.id == spot_id, ObstructionSpot.user_id == user.user_id,
            ObstructionSpot.observatory_id == home_id,
            ObstructionSpot.revision == payload.expected_revision,
        ).values(**values, revision=ObstructionSpot.revision + 1))
        if result.rowcount != 1:
            reject(409, "Spot changed or is unavailable. Reload saved spots and review again.")
        spot = spot_query(db, user, home_id).filter_by(id=spot_id).one()
    db.commit()
    db.refresh(spot)
    return describe(spot, home)


def delete_spot(db, user, home_id, spot_id, revision):
    owned_home(db, user, home_id, lock=True)
    result = db.execute(delete(ObstructionSpot).where(
        ObstructionSpot.id == spot_id, ObstructionSpot.user_id == user.user_id,
        ObstructionSpot.observatory_id == home_id, ObstructionSpot.revision == revision))
    if result.rowcount != 1:
        reject(409, "Spot changed or is unavailable. Reload saved spots first.")
    db.commit()


def resolve_spot(db, user, home, spot_id, revision):
    if home is None:
        reject(409, "Observing home is unavailable. Reload your account.")
    spot = spot_query(db, user, home.id).filter_by(id=spot_id).one_or_none()
    if spot is None or spot.revision != revision:
        reject(409, "Selected spot changed or is unavailable. Review it or explicitly choose Off.")
    reason = availability(spot, home)
    if reason:
        reject(409, reason + " Choose Off explicitly to plan without local obstructions.")
    profile = ObstructionProfile.model_validate(spot.profile)
    provenance = {"mode": "applied", "spot_id": str(spot.id), "observatory_id": str(home.id), "name": spot.name,
                  "revision": spot.revision, "source_quality": spot.source_quality,
                  "schema_version": spot.schema_version, "reviewed_at": spot.reviewed_at.isoformat(),
                  "profile": profile.model_dump(mode="json")}
    return profile, provenance
