import os,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
os.chdir(root)
sys.path[:0]=[str(root),str(root/'tests')]
os.environ['POLARIS_DATABASE_URL']='sqlite:///:memory:'
os.environ['POLARIS_ENVIRONMENT']='test'
source=(root/'scripts/benchmark_tonight.py').read_text()
injection='''
from app.services import astronomy_service as astronomy
from app.services.planning_runtime_service import prepare_planning_runtime
class Clock(datetime):
    @classmethod
    def now(cls,tz=None):
        at=datetime(2026,10,18,18,24,tzinfo=timezone.utc)
        return at.astimezone(tz) if tz else at.replace(tzinfo=None)
original['datetime']=Clock
astronomy.datetime=Clock
preparation_started=time.perf_counter()
prepare_planning_runtime()
print(json.dumps({'preparation_seconds':time.perf_counter()-preparation_started}),flush=True)
'''
source=source.replace('results = []',injection+'\nresults = []').replace("patch.object(scheduler, 'datetime', datetime)","patch.object(scheduler, 'datetime', Clock)")
exec(compile(source,str(root/'scripts/benchmark_tonight.py'),'exec'),{'__file__':str(root/'scripts/benchmark_tonight.py')})

