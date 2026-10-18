import os,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
os.chdir(root)
sys.path[:0]=[str(root),str(root/'tests')]
os.environ['POLARIS_DATABASE_URL']='sqlite:///:memory:'
os.environ['POLARIS_ENVIRONMENT']='test'
source=(root/'scripts/benchmark_tonight.py').read_text()
injection='''
import cProfile,pstats,io
from time import process_time, thread_time
from app.services import astronomy_service as astronomy
from app.services.planning_runtime_service import prepare_planning_runtime
import importlib
api=importlib.import_module('app.api.tonight')
class Clock(datetime):
    @classmethod
    def now(cls,tz=None):
        at=datetime(2026,10,18,3,24,tzinfo=timezone.utc)
        return at.astimezone(tz) if tz else at.replace(tzinfo=None)
original['datetime']=Clock
astronomy.datetime=Clock
prepare_planning_runtime()
original_plan=api.get_tonight_plan
def measured_plan(*args,**kwargs):
    profile=cProfile.Profile()
    wall=time.perf_counter(); process=process_time(); thread=thread_time()
    try:
        return profile.runcall(original_plan,*args,**kwargs)
    finally:
        print(json.dumps({'planner_wall':time.perf_counter()-wall,'process_cpu':process_time()-process,'thread_cpu':thread_time()-thread}))
        pstats.Stats(profile).strip_dirs().sort_stats('cumulative').print_stats(35)
api.get_tonight_plan=measured_plan
'''
source=source.replace('results = []',injection+'\nresults = []').replace("patch.object(scheduler, 'datetime', datetime)","patch.object(scheduler, 'datetime', Clock)")
exec(compile(source,str(root/'scripts/benchmark_tonight.py'),'exec'),{'__file__':str(root/'scripts/benchmark_tonight.py')})
