#!/usr/bin/env python3
"""Export one tenant's hosted Polaris records without bypassing RLS."""

import argparse
import json
import os
import sys
from pathlib import Path
from uuid import UUID


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.database.database import SessionLocal
from app.database.database import TENANT_SESSION_KEY
from app.services.hosted_backup_service import export_hosted_tenant
from app.services.hosted_backup_service import verify_hosted_tenant_export


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Export one user's hosted Polaris profile, observatories, "
            "recommendation runs, and feedback to a protected JSON file."
        )
    )
    parser.add_argument("user_id", type=UUID)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()

    output_path = arguments.output.expanduser().resolve()
    if not output_path.parent.is_dir():
        raise SystemExit(
            f"Output folder does not exist: {output_path.parent}"
        )

    database = SessionLocal()
    database.info[TENANT_SESSION_KEY] = arguments.user_id
    try:
        document = export_hosted_tenant(
            database,
            user_id=arguments.user_id,
        )
    finally:
        database.close()

    report = verify_hosted_tenant_export(document)
    if not report["valid"]:
        raise SystemExit(
            "Export failed verification: " + "; ".join(report["errors"])
        )

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(output_path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        json.dump(document, output, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())

    print(f"Hosted tenant export created: {output_path}")
    print(f"Payload SHA-256: {report['payload_sha256']}")
    print(f"Record counts: {json.dumps(report['counts'], sort_keys=True)}")


if __name__ == "__main__":
    main()
