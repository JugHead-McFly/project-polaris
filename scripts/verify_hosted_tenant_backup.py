#!/usr/bin/env python3
"""Verify and rehearse a hosted tenant restore in disposable SQLite."""

import argparse
import json
import sys
from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.database.database import Base
from app.models import HostedObservatory
from app.models import Profile
from app.models import RecommendationFeedback
from app.models import RecommendationRun
from app.services.hosted_backup_service import restore_hosted_tenant
from app.services.hosted_backup_service import verify_hosted_tenant_export


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify a hosted tenant export and restore it into a disposable "
            "in-memory database without touching the live hosted project."
        )
    )
    parser.add_argument("backup", type=Path)
    arguments = parser.parse_args()

    backup_path = arguments.backup.expanduser().resolve()
    with backup_path.open(encoding="utf-8") as backup_file:
        document = json.load(backup_file)

    report = verify_hosted_tenant_export(document)
    if not report["valid"]:
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(1)

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    database_factory = sessionmaker(bind=engine)
    database = database_factory()
    try:
        restore_hosted_tenant(database, document=document)
        user_id = UUID(report["user_id"])
        restored_counts = {
            "profiles": database.query(Profile)
            .filter(Profile.user_id == user_id)
            .count(),
            "observatories": database.query(HostedObservatory)
            .filter(HostedObservatory.user_id == user_id)
            .count(),
            "recommendation_runs": database.query(RecommendationRun)
            .filter(RecommendationRun.user_id == user_id)
            .count(),
            "recommendation_feedback": database.query(
                RecommendationFeedback
            )
            .filter(RecommendationFeedback.user_id == user_id)
            .count(),
        }
    finally:
        database.close()
        engine.dispose()

    if restored_counts != report["counts"]:
        raise SystemExit(
            "Disposable restore counts did not match the export manifest."
        )

    print("Hosted tenant export is valid.")
    print("Disposable restore rehearsal passed.")
    print(f"Payload SHA-256: {report['payload_sha256']}")
    print(f"Restored counts: {json.dumps(restored_counts, sort_keys=True)}")


if __name__ == "__main__":
    main()
