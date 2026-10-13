"""Import reviewed legacy metadata without awarding verified integration time.

No web upload endpoint is provided. The caller owns the transaction and must
provide the authenticated tenant context. No filesystem paths or notes are sent.
"""
import hashlib
import json
import math
import re
from uuid import UUID
from sqlalchemy import select
from app.database.database import TENANT_SESSION_KEY
from app.models import Profile, LegacyCapture
from app.schemas.capture_history import normalize_target


def import_legacy_records(db, user_id, records):
    user_id = UUID(str(user_id))
    if str(db.info.get(TENANT_SESSION_KEY)) != str(user_id):
        raise ValueError("Legacy import requires matching tenant context")
    # Serialize concurrent imports for this owner, including first insert.
    if db.scalar(select(Profile).where(Profile.user_id == user_id).with_for_update()) is None:
        raise ValueError("Owner does not exist")
    existing = {r.source_key: r for r in db.scalars(select(LegacyCapture).where(LegacyCapture.user_id == user_id))}
    pending = []
    seen = set()
    for record in records:
        key = record["source_key"]
        if not re.fullmatch(r"[a-f0-9]{64}", key) or key in seen:
            raise ValueError("Invalid or duplicate legacy source identity")
        seen.add(key)
        if record.get("basis") != "legacy_stack_metadata":
            raise ValueError("Expected legacy stack evidence")
        target = normalize_target(record["target"])
        stamp = record.get("original_observation_time")
        seconds = record.get("reported_integration_seconds")
        flags = record.get("flags", [])
        if not target or len(target) > 100 or (stamp is not None and (not isinstance(stamp, str) or len(stamp) > 80)):
            raise ValueError("Invalid legacy target or date")
        if seconds is not None and (isinstance(seconds, bool) or not isinstance(seconds, (float, int)) or not math.isfinite(seconds) or seconds <= 0):
            raise ValueError("Invalid reported integration")
        if not isinstance(flags, list) or any(not isinstance(f, str) or len(f) > 100 for f in flags):
            raise ValueError("Invalid review flags")
        values = dict(target=target, original_observation_time=stamp,
                      reported_integration_seconds=seconds, review_flags=sorted(set(flags)))
        evidence = hashlib.sha256(json.dumps(values, sort_keys=True, allow_nan=False).encode()).hexdigest()
        prior = existing.get(key)
        if prior is not None:
            if prior.evidence_hash != evidence:
                raise ValueError("Legacy record conflicts with existing evidence; review required")
            continue
        pending.append(LegacyCapture(user_id=user_id, source_key=key, evidence_hash=evidence, **values))
    # Validate the complete batch before adding anything; caller commits/rolls back.
    db.add_all(pending)
    db.flush()
    return {"records_added": len(pending), "records_unchanged": len(records) - len(pending), "verified_hours_added": 0}


def legacy_summary(db, user_id):
    rows = db.scalars(select(LegacyCapture).where(LegacyCapture.user_id == user_id).order_by(LegacyCapture.target, LegacyCapture.source_key)).all()
    targets = {}
    for row in rows:
        targets[row.target] = targets.get(row.target, 0) + 1
    return {"record_count": len(rows), "basis": "Older stack records; not added to verified imaging time.",
            "targets": [{"object": name, "record_count": count} for name, count in targets.items()]}
