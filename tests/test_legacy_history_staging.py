import hashlib
import json
import sqlite3
from uuid import uuid4

import pytest

from scripts.stage_legacy_history import prepare, stage


def backup(path, *, enriched=True, extra=False, seconds=3600):
    with sqlite3.connect(path) as db:
        db.executescript('''CREATE TABLE sessions(id INTEGER, notes TEXT);
          CREATE TABLE captures(id INTEGER, polaris_id TEXT, object_name TEXT,
            filename TEXT, observation_utc TEXT, total_integration_seconds REAL,
            subframe_count INTEGER, sub_exposure_seconds REAL);
          CREATE TABLE capture_analyses(id INTEGER, capture_id INTEGER, quality_score REAL);
          INSERT INTO sessions VALUES (1,'preserve original note');
          INSERT INTO capture_analyses VALUES (1,1,80);''')
        db.execute('INSERT INTO captures VALUES (1,?,?,?,?,?,?,?)',
                   ('stable', 'M 31', 'stacked.fits', '2026-06-12T05:32:03',
                    seconds if enriched else None, 240 if enriched else None, 15 if enriched else None))
        if extra:
            db.execute("INSERT INTO captures SELECT 2,'other',object_name,'renamed.fits',observation_utc,total_integration_seconds,subframe_count,sub_exposure_seconds FROM captures")
    return path


def test_merge_backup_versions_without_double_count_or_source_changes(tmp_path):
    first=backup(tmp_path/'a.db',enriched=False); second=backup(tmp_path/'b.db')
    before=[hashlib.sha256(p.read_bytes()).hexdigest() for p in [first,second]]
    report=stage([first,second,second],tmp_path/'review.db',uuid4())
    assert report['unique_captures']==1 and report['source_backups']==2
    assert report['verified_hours_added']==0
    with sqlite3.connect(tmp_path/'review.db') as db:
        row=json.loads(db.execute('SELECT payload FROM legacy_review').fetchone()[0])
        assert row['reported_integration_seconds']==3600
        assert row['basis']=='legacy_stack_metadata'
        assert row['flags']==['timezone_unconfirmed']
        originals=[json.loads(r[0]) for r in db.execute('SELECT original_rows FROM source_snapshots')]
        assert all(r['capture_analyses'][0]['quality_score']==80 for r in originals)
        assert all(r['sessions'][0]['notes']=='preserve original note' for r in originals)
    assert before==[hashlib.sha256(p.read_bytes()).hexdigest() for p in [first,second]]


def test_potential_duplicate_is_held_not_discarded(tmp_path):
    _,rows=prepare([backup(tmp_path/'a.db',extra=True)])
    assert len(rows)==2
    assert all('possible_same_night_overlap' in r['flags'] for r in rows)
    assert all(r['verified_integration_seconds']==0 for r in rows)


def test_conflicting_evidence_is_preserved_and_flagged(tmp_path):
    _,rows=prepare([backup(tmp_path/'a.db'),backup(tmp_path/'b.db',seconds=7200)])
    assert len(rows)==1 and len(rows[0]['versions'])==2
    assert 'conflicting_total_integration_seconds' in rows[0]['flags']


def test_missing_integration_is_not_guessed_from_sub_exposure(tmp_path):
    _,rows=prepare([backup(tmp_path/'a.db',enriched=False)])
    assert rows[0]['reported_integration_seconds'] is None
    assert 'integration_unknown' in rows[0]['flags']


def test_never_overwrites_an_existing_destination(tmp_path):
    source=backup(tmp_path/'a.db'); before=source.read_bytes()
    with pytest.raises(FileExistsError):stage([source],source,uuid4())
    assert source.read_bytes()==before


def test_owner_is_explicit_and_cannot_mix_accounts(tmp_path):
    source=backup(tmp_path/'a.db'); owners=[str(uuid4()),str(uuid4())]
    for i,owner in enumerate(owners):
        dest=tmp_path/f'{i}.db';stage([source],dest,owner)
        with sqlite3.connect(dest) as db:
            assert db.execute('SELECT DISTINCT owner_id FROM legacy_review').fetchall()==[(owner,)]
    with pytest.raises(ValueError):stage([source],tmp_path/'bad.db','not-an-owner')
    assert not (tmp_path/'bad.db').exists()


def test_missing_source_does_not_create_database(tmp_path):
    with pytest.raises(FileNotFoundError):stage([tmp_path/'missing.db'],tmp_path/'out.db',uuid4())
    assert not (tmp_path/'missing.db').exists() and not (tmp_path/'out.db').exists()
