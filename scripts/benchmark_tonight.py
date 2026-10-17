"""Full hosted POST benchmark: memory DB, 300 synthetic sessions, real astronomy.

Weather is a fixed clear fixture; provider I/O is deliberately excluded/reported.
No live database, account or telescope access. Run from repository root.
"""
import sys, json, time
from pathlib import Path
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / 'tests')]
from astropy.utils import iers
iers.conf.auto_download = False
from fastapi.testclient import TestClient
from import_plan_fixture import workflow, manifest, ALICE
from app.database.database import get_db
from app.models import HostedObservatory, ForecastAccuracySnapshot
from app.core.planning_context import ObservatoryContext
from app.services import planner_service as planner
from app.services import scheduler_service as scheduler

names = ['TARGETS', 'shortlist', 'get_moon_info', 'get_darkness_info',
         'get_darkness_window_datetimes', 'get_dark_visibility', 'get_altitude_at',
         'get_moon_separation_at', 'get_moon_warning_at', 'get_transit_time', 'datetime']
original = {name: getattr(planner, name) for name in names}
context = ObservatoryContext('Synthetic Phoenix', 33.4484, -112.074, 'America/Phoenix',
                             elevation_meters=331, bortle_class=8, rig_profile_key='dwarf-mini')
results = []
with workflow() as flow, ExitStack() as stack, TestClient(flow.app) as client:
    for name, value in original.items():
        stack.enter_context(patch.object(planner, name, value))
    stack.enter_context(patch.object(scheduler, 'datetime', datetime))
    stack.enter_context(patch('app.api.tonight.get_planning_context', return_value=context))
    for batch in range(3):
        sessions = [manifest(.01, key=f'bench-{i}', target=['M31','M33','M42'][i % 3])['sessions'][0]
                    for i in range(batch*100, (batch+1)*100)]
        response = flow.sync(client, {'sessions':sessions})
        assert response.status_code == 200, response.text
    if '--forecast-history' in sys.argv:
        database = flow.app.dependency_overrides[get_db]()
        db = next(database)
        try:
            home = db.query(HostedObservatory).filter(HostedObservatory.user_id == ALICE).one()
            now = datetime.now(timezone.utc)
            for i in range(960):
                at = now - timedelta(minutes=15*(i+1))
                db.add(ForecastAccuracySnapshot(user_id=ALICE, observatory_id=home.id,
                    forecast_for=at, forecast_created_at=at-timedelta(hours=3), forecast_lead_hour=3,
                    forecast_cloud_cover_percent=10, observed_cloud_cover_percent=12,
                    status='matched', expires_at=now+timedelta(days=1), observed_at=at,
                    satellite_cloud_observation={'status':'usable','forecast_for':at.isoformat(),
                        'scan_midpoint':at.isoformat(),'cloud_cover_percent':12,'good_pixel_fraction':1}))
            db.commit()
        finally:
            database.close()
    for iteration in range(3):
        start = time.perf_counter()
        response = client.post('/tonight')
        elapsed = time.perf_counter()-start
        assert response.status_code == 200, response.text
        body = response.json()
        result = {'iteration':iteration, 'seconds':round(elapsed,3),
                  'targets':[b['object'] for b in body['schedule']['blocks']],
                  'gap_minutes':body['schedule']['unscheduled_dark_minutes']}
        results.append(result)
        print(json.dumps(result), flush=True)
print(json.dumps({'scope':'Full hosted POST, 300 synthetic sessions; fixed weather; real astronomy; in-memory SQLite; no provider/network latency',
                  'forecast_records':960 if '--forecast-history' in sys.argv else 0, 'runs':results}))
if '--check-budget' in sys.argv:
    assert max(row['seconds'] for row in results[1:]) < 6, 'Warm synthetic full-request budget exceeded (6 seconds)'
