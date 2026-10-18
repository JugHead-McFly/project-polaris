"""Isolated synthetic Moon cold/warm probe; no accounts, DB or image access."""
import os, sys, json, time, tempfile, importlib
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
os.environ['POLARIS_DATABASE_URL']='sqlite:///:memory:'
os.environ['POLARIS_ENVIRONMENT']='test'
from astropy.config.paths import set_temp_cache
from astropy.utils import iers
from app.services import astronomy_service as astronomy
from app.core.planning_context import ObservatoryContext
from astroplan import Observer
context=ObservatoryContext('Synthetic Phoenix',33.4484,-112.074,'America/Phoenix',elevation_meters=331)
class FixedClock(datetime):
    @classmethod
    def now(cls,tz=None):
        at=datetime(2026,10,18,3,24,tzinfo=timezone.utc)
        return at.astimezone(tz) if tz else at.replace(tzinfo=None)
astronomy.datetime=FixedClock
mode=sys.argv[1] if len(sys.argv)>1 else 'offline'
iers.conf.auto_download=mode.startswith('network')
downloads=[]
module=importlib.import_module('astropy.utils.iers.iers')
original_download=module.download_file
def download(*args,**kwargs):
    wall=time.perf_counter(); status='success'
    try: return original_download(*args,**kwargs)
    except Exception as e:
        status=type(e).__name__; raise
    finally:
        downloads.append({'seconds':round(time.perf_counter()-wall,4),'status':status})
module.download_file=download
original_current=astronomy.get_moon_info_at
original_rise=Observer.moon_rise_time
original_set=Observer.moon_set_time
stages={}
def measured(label,func):
    def run(*args,**kwargs):
        w,t,p=time.perf_counter(),time.thread_time(),time.process_time()
        try:return func(*args,**kwargs)
        finally:stages[label]={'wall_s':round(time.perf_counter()-w,4),'thread_cpu_s':round(time.thread_time()-t,4),'process_cpu_s':round(time.process_time()-p,4)}
    return run
cache=tempfile.mkdtemp(prefix='polaris-moon-iers-')
with set_temp_cache(cache,delete=False),patch.object(astronomy,'get_moon_info_at',measured('current',original_current)),patch.object(Observer,'moon_rise_time',measured('rise',original_rise)),patch.object(Observer,'moon_set_time',measured('set',original_set)):
    if mode.endswith('-prepared'):
        from app.services.planning_runtime_service import prepare_planning_runtime
        print(json.dumps({'mode':mode,'startup':prepare_planning_runtime(),'downloads':downloads}),flush=True)
    for iteration in range(3):
        stages.clear();w,t,p=time.perf_counter(),time.thread_time(),time.process_time()
        result=astronomy.get_moon_info(context)
        print(json.dumps({'mode':mode,'iteration':iteration,'wall_s':round(time.perf_counter()-w,4),'thread_cpu_s':round(time.thread_time()-t,4),'process_cpu_s':round(time.process_time()-p,4),'stages':stages,'downloads':downloads,'result':result}),flush=True)

