"""Offline restore/repeat-import rehearsal; no application configuration loaded."""
from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.database import Base, TENANT_SESSION_KEY
from app.models import Profile, HostedCaptureSession, HostedObservatory, NightlyForecast
from app.services.hosted_backup_service import (
    export_hosted_tenant, restore_hosted_tenant, verify_hosted_tenant_export,
    _payload_checksum, V1_BACKUP_MODELS,
)
from app.services.legacy_capture_service import import_legacy_records
from app.services.capture_history_service import library_summary, progress_map


def test_backup_restore_and_repeat_merge_preserve_verified_progress():
    source_engine = create_engine('sqlite://')
    target_engine = create_engine('sqlite://')
    for engine in (source_engine, target_engine):
        Base.metadata.create_all(engine)
    user, other = uuid4(), uuid4()
    stamp = datetime(2026, 10, 8, tzinfo=timezone.utc)
    records = [dict(source_key='a'*64, target='M31', basis='legacy_stack_metadata',
                    original_observation_time='2026-06-12T05:32:03',
                    reported_integration_seconds=3600, flags=['timezone_unconfirmed'])]
    try:
        with Session(source_engine) as source, Session(target_engine) as target:
            source.add_all([Profile(user_id=user), Profile(user_id=other)])
            source.flush()
            home = HostedObservatory(user_id=user, name='Synthetic', latitude=33,
                                     longitude=-112, timezone_name='America/Phoenix')
            source.add(home); source.flush()
            source.add(NightlyForecast(user_id=user, observatory_id=home.id,
                night_date=date(2026,10,8), window_start=stamp, window_end=stamp,
                latitude=33, longitude=-112, timezone_name='America/Phoenix'))
            for owner in (user, other):
                source.add(HostedCaptureSession(user_id=owner, source_key='a'*64,
                    target='M31', session_name='synthetic', captured_at=stamp,
                    filter_name='Astro', frame_count=120, integration_seconds=3600,
                    evidence_hash='b'*64))
            source.commit()
            before = progress_map(library_summary(source, user))
            source.info[TENANT_SESSION_KEY] = user
            import_legacy_records(source, user, records); source.commit()
            document = export_hosted_tenant(source, user_id=user)
            assert verify_hosted_tenant_export(document)['valid']
            assert len(document['tables']['capture_history']) == 1
            assert len(document['tables']['legacy_capture_history']) == 1
            restore_hosted_tenant(target, document=document)
            target.info[TENANT_SESSION_KEY] = user
            assert import_legacy_records(target, user, records)['records_unchanged'] == 1
            assert progress_map(library_summary(target,user)) == before
            assert library_summary(target,user)['legacy']['record_count'] == 1
            assert target.query(Profile).count() == 1
            assert target.query(NightlyForecast).one().night_date == date(2026,10,8)
            restored = export_hosted_tenant(target, user_id=user)
            assert restored['tables'] == document['tables']
            # Old exports remain readable without pretending they contain history.
            v1 = dict(document, format_version=1,
                      tables={name:document['tables'][name] for name,_ in V1_BACKUP_MODELS})
            v1['payload_sha256'] = _payload_checksum(v1)
            assert verify_hosted_tenant_export(v1)['valid']
    finally:
        source_engine.dispose(); target_engine.dispose()
