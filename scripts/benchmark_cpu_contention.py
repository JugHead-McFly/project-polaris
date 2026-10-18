"""Synthetic attribution experiment, never a production or capacity benchmark.

Usage: python scripts/benchmark_cpu_contention.py ROOT [--competitors N]
Same fixed clock/weather/memory database as benchmark_request_latency.py.
Optional competing Python threads demonstrate possible GIL/scheduling signatures;
they do not establish that production has those conditions.
"""
import argparse
import os
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('root')
parser.add_argument('--competitors', type=int, default=0, choices=range(4))
args = parser.parse_args()
root = Path(args.root).resolve()
os.chdir(root)
sys.path[:0] = [str(root), str(root / 'tests')]
os.environ['POLARIS_DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['POLARIS_ENVIRONMENT'] = 'test'
source = (root / 'scripts/benchmark_tonight.py').read_text()
injection = '''
from threading import Event, Thread, Timer
from time import process_time, thread_time
from app.services import astronomy_service as astronomy
from app.services.planning_runtime_service import prepare_planning_runtime
import importlib
api = importlib.import_module('app.api.tonight')
class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        at = datetime(2026,10,18,18,24,tzinfo=timezone.utc)
        return at.astimezone(tz) if tz else at.replace(tzinfo=None)
original['datetime'] = Clock
astronomy.datetime = Clock
prepare_planning_runtime()
original_plan = api.get_tonight_plan
def measured_plan(*a, **kw):
    stop.clear()
    threads = [Thread(target=compete, daemon=True) for _ in range(COMPETITORS)]
    for competitor in threads:
        competitor.start()
    # Limit deliberate contention even if a regression stalls the experiment.
    deadline = Timer(20, stop.set)
    deadline.start()
    wall, process, thread = time.perf_counter(), process_time(), thread_time()
    try:
        return original_plan(*a, **kw)
    finally:
        print(json.dumps({'cpu_experiment': True, 'competitors': COMPETITORS,
            'contention_deadline_reached': stop.is_set(),
            'planner_wall_seconds': time.perf_counter()-wall,
            'process_cpu_seconds': process_time()-process,
            'worker_thread_cpu_seconds': thread_time()-thread}), flush=True)
        stop.set()
        deadline.cancel()
        for competitor in threads:
            competitor.join(timeout=2)
api.get_tonight_plan = measured_plan
stop = Event()
def compete():
    while not stop.is_set():
        value = 0
        for i in range(8192):
            value = (value + i*i) % 100003
threads = []
'''.replace('COMPETITORS', str(args.competitors))
source = source.replace('results = []', injection + '\nresults = []').replace(
    "patch.object(scheduler, 'datetime', datetime)", "patch.object(scheduler, 'datetime', Clock)")
namespace = {'__file__': str(root / 'scripts/benchmark_tonight.py')}
try:
    exec(compile(source, str(root / 'scripts/benchmark_tonight.py'), 'exec'), namespace)
finally:
    if 'stop' in namespace:
        namespace['stop'].set()
        for thread in namespace['threads']:
            thread.join(timeout=2)
