"""Matched synthetic full-POST overhead run; no live database/provider access.

python scripts/benchmark_runtime_diagnostics.py ROOT [--enabled]
The harness forces every iteration to sample, deliberately exceeding production
sampling frequency to measure the worst normal per-sampled-request overhead.
"""
import os
import sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
os.chdir(root)
sys.path[:0]=[str(root),str(root/'tests')]
os.environ['POLARIS_DATABASE_URL']='sqlite:///:memory:'
os.environ['POLARIS_ENVIRONMENT']='test'
enabled='--enabled' in sys.argv
os.environ['POLARIS_RUNTIME_DIAGNOSTICS']='true' if enabled else 'false'
source=(root/'scripts/benchmark_tonight.py').read_text()
injection='''
from app.core import runtime_diagnostics as diagnostics
from app.services import astronomy_service as astronomy
from app.services.planning_runtime_service import prepare_planning_runtime
class Clock(datetime):
    @classmethod
    def now(cls,tz=None):
        at=datetime(2026,10,18,18,24,tzinfo=timezone.utc)
        return at.astimezone(tz) if tz else at.replace(tzinfo=None)
original['datetime']=Clock
astronomy.datetime=Clock
prepare_planning_runtime()
'''
source=source.replace('results = []',injection+'\nresults = []').replace(
    "patch.object(scheduler, 'datetime', datetime)","patch.object(scheduler, 'datetime', Clock)")
source=source.replace('for iteration in range(3):',
    'for iteration in range(12):\n        diagnostics._last = None\n        diagnostics._samples = 0')
namespace={'__file__':str(root/'scripts/benchmark_tonight.py')}
exec(compile(source,str(root/'scripts/benchmark_tonight.py'),'exec'),namespace)
import json
from statistics import median
print(json.dumps({'diagnostics_enabled':enabled,'warm_runs':10,
    'median_full_post_seconds':median(row['seconds'] for row in namespace['results'][2:])}))
