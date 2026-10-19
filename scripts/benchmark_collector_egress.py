"""Offline SQLite returned-row/JSON-byte proxy; never connects to production.

Compares the deployed baseline functions with the working tree using identical
synthetic histories. Bytes exclude protocol overhead and are NOT billed egress.
"""
import json
import logging
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['POLARIS_DATABASE_URL'] = 'sqlite://'
os.environ['POLARIS_ENVIRONMENT'] = 'test'
os.environ['POLARIS_AUTH_MODE'] = 'local'
from sqlalchemy import create_engine, null
from sqlalchemy.orm import sessionmaker
from app.database.database import Base
from app.models import Profile, HostedObservatory, NightlyForecast, ForecastAccuracySnapshot
from app.services import nightly_forecast_service as nightly, satellite_cloud_service as satellite

BASELINE = 'f67a9237f22d7cc9988030a2b6c65cf4b51250c6'
NOW = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)
OWNER, OTHER, HOME, OTHER_HOME = map(UUID, ['00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000004'])


class Meter:
    enabled = False
    def reset(self):
        self.selects = self.rows = self.bytes = 0
        self.enabled = True
    def record(self, row):
        if self.enabled and row is not None:
            self.rows += 1
            self.bytes += len(json.dumps(row, default=str, separators=(',', ':')).encode())
        return row
    def result(self):
        self.enabled = False
        return dict(selects=self.selects, rows=self.rows, serialized_bytes=self.bytes)


def database():
    meter = Meter()
    class Cursor(sqlite3.Cursor):
        def execute(self, sql, parameters=()):
            if meter.enabled and sql.lstrip().upper().startswith('SELECT'):
                meter.selects += 1
            return super().execute(sql, parameters)
        def fetchone(self):
            return meter.record(super().fetchone())
        def fetchall(self):
            return [meter.record(row) for row in super().fetchall()]
        def fetchmany(self, size=None):
            rows = super().fetchmany() if size is None else super().fetchmany(size)
            return [meter.record(row) for row in rows]
    class Connection(sqlite3.Connection):
        def cursor(self, *args, **kwargs):
            return super().cursor(factory=Cursor)
    engine = create_engine('sqlite://', creator=lambda: sqlite3.connect(':memory:', factory=Connection))
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    for owner, home_id in [(OWNER, HOME), (OTHER, OTHER_HOME)]:
        db.add(Profile(user_id=owner))
        db.add(HostedObservatory(id=home_id, user_id=owner, name='Synthetic', latitude=33,
            longitude=-111, timezone_name='UTC'))
    db.commit()
    return db, meter


def reference(target, lat, lon):
    return dict(status='usable', cloud_cover_percent=20, scan_midpoint=target.isoformat(),
        forecast_for=target.isoformat(), good_pixel_fraction=1, evidence='x'*200)


def old_function(module, name):
    source = subprocess.check_output(['git', 'show', f'{BASELINE}:app/services/{module}.py'], cwd=ROOT, text=True)
    scope = {'__name__': f'app.services.{module}'}
    exec(compile(source, f'<baseline {module}>', 'exec'), scope)
    return scope[name]


def measure_nightly(fn, completed, active):
    db, meter = database()
    for index in range(completed):
        start = NOW-timedelta(days=index+1, hours=12)
        cells = [dict(target=(start+timedelta(minutes=5*i)).isoformat(), seconds=300,
            attempts=1, reference=reference(start+timedelta(minutes=5*i), 33, -111)) for i in range(120)]
        db.add(NightlyForecast(user_id=OWNER, observatory_id=HOME, night_date=start.date(),
            window_start=start, window_end=start+timedelta(hours=10), latitude=33, longitude=-111,
            timezone_name='UTC', forecasts={}, observation=dict(cells=cells, complete=True)))
    start = NOW-timedelta(hours=5)
    if active:
        db.add(NightlyForecast(user_id=OWNER, observatory_id=HOME, night_date=start.date(),
            window_start=start, window_end=start+timedelta(hours=2), latitude=33, longitude=-111,
            timezone_name='UTC', forecasts={}, observation={}))
    db.add(NightlyForecast(user_id=OTHER, observatory_id=OTHER_HOME, night_date=start.date(),
        window_start=start, window_end=start+timedelta(hours=2), latitude=1, longitude=2,
        timezone_name='UTC', forecasts={}, observation={}))
    db.commit()
    home = db.get(HostedObservatory, HOME)
    calls = []
    def fetch(target, lat, lon):
        calls.append((target.isoformat(), lat, lon))
        if target.minute == 2:
            raise ValueError('Synthetic missing scan')
        return reference(target, lat, lon)
    meter.reset()
    report = fn(db, user_id=OWNER, observatory=home, now=NOW, clock=lambda: NOW,
        weather_fetch=lambda *a, **kw: (_ for _ in ()).throw(AssertionError('No forecast due')),
        satellite_fetch=fetch, darkness=lambda **kw: (NOW, NOW+timedelta(hours=8), NOW+timedelta(hours=10)))
    metrics = meter.result()
    state = [(str(r.user_id), str(r.night_date), r.forecasts, r.observation) for r in
        db.query(NightlyForecast).order_by(NightlyForecast.user_id, NightlyForecast.night_date)]
    db.close()
    return metrics, (report, calls, state)


def measure_satellite(fn, completed):
    db, meter = database()
    for index in range(completed+6):
        target = NOW-timedelta(hours=index+1)
        for lead in (1, 2):
            db.add(ForecastAccuracySnapshot(user_id=OWNER, observatory_id=HOME,
                forecast_for=target, forecast_created_at=target-timedelta(hours=lead),
                forecast_lead_hour=lead, expires_at=NOW, status='expired',
                satellite_cloud_observation=(reference(target, 33, -111) if index < completed else
                    null() if lead == 1 else None)))
    target = NOW-timedelta(hours=2)
    db.add(ForecastAccuracySnapshot(user_id=OTHER, observatory_id=OTHER_HOME, forecast_for=target,
        forecast_created_at=target-timedelta(hours=1), forecast_lead_hour=1, expires_at=NOW, status='expired'))
    db.commit()
    home = db.get(HostedObservatory, HOME)
    calls = []
    def fetch(target, lat, lon):
        calls.append((target.isoformat(), lat, lon))
        if len(calls) == 2:
            raise ValueError('Synthetic missing scan')
        result = reference(target, lat, lon)
        if len(calls) == 3:
            result['status'] = 'insufficient_quality'
        return result
    meter.reset()
    report = fn(db, user_id=OWNER, observatory=home, fetch=fetch, now=NOW, limit=4)
    metrics = meter.result()
    state = [(str(r.user_id), str(r.forecast_for), r.forecast_lead_hour, r.status, r.satellite_cloud_observation)
        for r in db.query(ForecastAccuracySnapshot).order_by(ForecastAccuracySnapshot.user_id,
            ForecastAccuracySnapshot.forecast_for, ForecastAccuracySnapshot.forecast_lead_hour)]
    db.close()
    return metrics, (report, calls, state)


def compare():
    logging.disable(logging.CRITICAL)
    old_nightly = old_function('nightly_forecast_service', 'collect_nightly')
    old_satellite = old_function('satellite_cloud_service', 'collect_satellite_references')
    results = []
    for size in (0, 7, 13):
        for active in (False, True):
            before, old_state = measure_nightly(old_nightly, size, active)
            after, new_state = measure_nightly(nightly.collect_nightly, size, active)
            assert old_state == new_state, ('nightly behavior changed', size, active)
            results.append(dict(scenario='nightly_active' if active else 'nightly_idle', completed=size,
                before=before, after=after, identical_outputs_and_history=True))
    for size in (0, 100, 1000):
        before, old_state = measure_satellite(old_satellite, size)
        after, new_state = measure_satellite(satellite.collect_satellite_references, size)
        assert old_state == new_state, ('satellite behavior changed', size)
        results.append(dict(scenario='satellite_mixed', completed_targets=size,
            before=before, after=after, identical_outputs_and_history=True))
    return results


if __name__ == '__main__':
    print(json.dumps(dict(baseline=BASELINE, measurement='SQLite SELECT results; serialized byte proxy, not billed wire traffic',
        results=compare()), indent=2))
