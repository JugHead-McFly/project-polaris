import hashlib
import json
from datetime import datetime
from datetime import timezone
from typing import Dict
from typing import List
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy import Uuid
from sqlalchemy.orm import Session

from app.models import HostedObservatory
from app.models import Profile
from app.models import RecommendationFeedback
from app.models import RecommendationRun


BACKUP_FORMAT = "polaris-hosted-tenant"
BACKUP_FORMAT_VERSION = 1
BACKUP_MODELS = (
    ("profiles", Profile),
    ("observatories", HostedObservatory),
    ("recommendation_runs", RecommendationRun),
    ("recommendation_feedback", RecommendationFeedback),
)


class HostedBackupError(RuntimeError):
    """Raised when an export cannot be trusted or restored safely."""


def _serialize(value):
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _record(model_instance) -> Dict:
    return {
        column.name: _serialize(getattr(model_instance, column.name))
        for column in model_instance.__table__.columns
    }


def _payload(document: Dict) -> Dict:
    return {
        "format": document["format"],
        "format_version": document["format_version"],
        "user_id": document["user_id"],
        "tables": document["tables"],
    }


def _payload_checksum(document: Dict) -> str:
    canonical = json.dumps(
        _payload(document),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def export_hosted_tenant(
    db: Session,
    *,
    user_id: UUID,
    exported_at: datetime = None,
) -> Dict:
    """Create a complete, tenant-scoped hosted-data export document."""
    tables = {}
    for table_name, model in BACKUP_MODELS:
        rows = (
            db.query(model)
            .filter(model.user_id == user_id)
            .order_by(*model.__table__.primary_key.columns)
            .all()
        )
        tables[table_name] = [_record(row) for row in rows]

    document = {
        "format": BACKUP_FORMAT,
        "format_version": BACKUP_FORMAT_VERSION,
        "exported_at": (
            exported_at or datetime.now(timezone.utc)
        ).isoformat(),
        "user_id": str(user_id),
        "tables": tables,
    }
    document["payload_sha256"] = _payload_checksum(document)
    return document


def verify_hosted_tenant_export(document: Dict) -> Dict:
    """Validate ownership, relationships, and checksum without restoring."""
    errors: List[str] = []
    expected_tables = {name for name, _ in BACKUP_MODELS}

    if document.get("format") != BACKUP_FORMAT:
        errors.append("Backup format is not recognized.")
    if document.get("format_version") != BACKUP_FORMAT_VERSION:
        errors.append("Backup format version is not supported.")

    try:
        user_id = UUID(str(document.get("user_id", "")))
    except ValueError:
        user_id = None
        errors.append("Backup user_id is not a valid UUID.")

    tables = document.get("tables")
    if not isinstance(tables, dict):
        tables = {}
        errors.append("Backup tables payload is missing.")
    elif set(tables) != expected_tables:
        errors.append("Backup table inventory is incomplete or unexpected.")

    supplied_checksum = document.get("payload_sha256")
    try:
        expected_checksum = _payload_checksum(document)
    except (KeyError, TypeError, ValueError):
        expected_checksum = None
        errors.append("Backup payload could not be checksummed.")
    if expected_checksum and supplied_checksum != expected_checksum:
        errors.append("Backup checksum does not match its payload.")

    for table_name in expected_tables:
        records = tables.get(table_name, [])
        if not isinstance(records, list):
            errors.append(f"{table_name} is not a record list.")
            continue
        for record in records:
            if not isinstance(record, dict):
                errors.append(f"{table_name} contains a malformed record.")
                continue
            if user_id and record.get("user_id") != str(user_id):
                errors.append(
                    f"{table_name} contains a record owned by another user."
                )

    profiles = tables.get("profiles", [])
    if len(profiles) != 1:
        errors.append("Backup must contain exactly one profile.")

    observatory_ids = {
        record.get("id")
        for record in tables.get("observatories", [])
        if isinstance(record, dict)
    }
    run_ids = {
        record.get("id")
        for record in tables.get("recommendation_runs", [])
        if isinstance(record, dict)
    }
    for record in tables.get("recommendation_runs", []):
        if (
            isinstance(record, dict)
            and record.get("observatory_id") not in observatory_ids
        ):
            errors.append(
                "A recommendation run references a missing observatory."
            )
    for record in tables.get("recommendation_feedback", []):
        if not isinstance(record, dict):
            continue
        if record.get("observatory_id") not in observatory_ids:
            errors.append(
                "Recommendation feedback references a missing observatory."
            )
        if record.get("recommendation_run_id") not in run_ids:
            errors.append(
                "Recommendation feedback references a missing run."
            )

    counts = {
        table_name: len(tables.get(table_name, []))
        if isinstance(tables.get(table_name, []), list)
        else 0
        for table_name in expected_tables
    }
    return {
        "valid": not errors,
        "user_id": str(user_id) if user_id else None,
        "payload_sha256": supplied_checksum,
        "counts": counts,
        "errors": errors,
    }


def _deserialize_record(model, record: Dict) -> Dict:
    values = {}
    for column in model.__table__.columns:
        value = record.get(column.name)
        if value is not None and isinstance(column.type, Uuid):
            value = UUID(value)
        elif value is not None and isinstance(column.type, DateTime):
            value = datetime.fromisoformat(value)
        values[column.name] = value
    return values


def restore_hosted_tenant(
    db: Session,
    *,
    document: Dict,
) -> Dict:
    """Restore one verified tenant into an empty target tenant boundary."""
    report = verify_hosted_tenant_export(document)
    if not report["valid"]:
        raise HostedBackupError(
            "Hosted tenant export failed verification: "
            + "; ".join(report["errors"])
        )

    user_id = UUID(report["user_id"])
    existing = db.query(Profile).filter(Profile.user_id == user_id).first()
    if existing is not None:
        raise HostedBackupError(
            "Restore target already contains this tenant profile."
        )

    try:
        for table_name, model in BACKUP_MODELS:
            for record in document["tables"][table_name]:
                db.add(model(**_deserialize_record(model, record)))
        db.commit()
    except Exception:
        db.rollback()
        raise

    return report
