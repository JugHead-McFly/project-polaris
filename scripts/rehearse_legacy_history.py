"""Rehearse a review artifact in memory. Never connects to a hosted database."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database.database import Base, TENANT_SESSION_KEY
from app.models import Profile
from app.services.legacy_capture_service import import_legacy_records
from app.services.capture_history_service import library_summary, progress_map
from app.services.hosted_backup_service import export_hosted_tenant, restore_hosted_tenant


def rehearse(path):
    path = Path(path).resolve()
    before_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    try:
        connection.execute('PRAGMA query_only=ON')
        if connection.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('Review database integrity failed')
        owners = connection.execute('SELECT owner_id FROM review_metadata').fetchall()
        if len(owners) != 1:
            raise ValueError('Expected one review owner')
        rows = connection.execute('SELECT owner_id,payload FROM legacy_review').fetchall()
        if any(owner != owners[0][0] for owner, _ in rows):
            raise ValueError('Review contains mixed owners')
        records = [json.loads(payload) for _,payload in rows]
    finally:
        connection.close()
    engines = [create_engine('sqlite://'), create_engine('sqlite://')]
    try:
        for engine in engines:
            Base.metadata.create_all(engine)
        with Session(engines[0]) as source, Session(engines[1]) as restored:
            # Deliberately remap personal attribution to a disposable synthetic owner.
            owner = uuid4()
            source.add(Profile(user_id=owner)); source.commit()
            source.info[TENANT_SESSION_KEY] = owner
            before = progress_map(library_summary(source,owner))
            first = import_legacy_records(source,owner,records); source.commit()
            backup = export_hosted_tenant(source,user_id=owner)
            restore_hosted_tenant(restored,document=backup)
            restored.info[TENANT_SESSION_KEY] = owner
            repeat = import_legacy_records(restored,owner,records)
            assert first['records_added'] == len(records)
            assert repeat['records_added'] == 0
            assert progress_map(library_summary(restored,owner)) == before
            assert export_hosted_tenant(restored,user_id=owner)['tables'] == backup['tables']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == before_hash
            return dict(legacy_records=len(records), targets=len({r['target'] for r in records}),
                        restored_records=repeat['records_unchanged'], repeated_import_added=0,
                        verified_hours_added=0, source_unchanged=True,
                        production_copy_used=False, production_rows_written=0)
    finally:
        for engine in engines:
            engine.dispose()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('review',type=Path)
    print(json.dumps(rehearse(parser.parse_args().review),indent=2))
