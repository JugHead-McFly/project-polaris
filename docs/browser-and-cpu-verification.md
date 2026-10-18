# Browser verification and local/server timing attribution

Follow-up to next-critical-path-investigation.md. Application code remains
`c838b8c20176ddca2fc2e60dbf7e64d8a161c2e5`; this follow-up adds test/diagnostic
scripts and documentation only. No push, merge, deployment or access changes.

## Browser route and results

The supported app-browser execution tool was absent after discovery. However,
the existing Playwright installation and installed Chrome155.0.8059.80 worked
with a temporary headless profile. No software installation, persistent profile,
real account authentication or user's browser/session access was necessary.
The earlier statement that browser verification was blocked was too broad.

`tests/operator_map_browser.cjs` passed at1440x900 and390x900 with no page errors
or document-level horizontal overflow. It exercises the real page/scripts and
Leaflet against `tests/serve_import_plan_fixture.py`, an in-memory localhost
fixture with synthetic account, history and sky data:

- Hosted plan reaches ready without requesting Leaflet, even with that URL held.
- Same-origin dynamic library loads with nonce/self script CSP and no unsafe-inline.
- Failed library download preserves saved sites; refresh successfully retries.
- Map renders markers/rings/controls; clicking fills coordinates; capture map
  also initializes using the shared library.
- Locations -> Tonight -> Locations hides and reopens the map correctly.
- A library response completing after a new load generation cannot render stale sites.
- Real15-second timeout preserves site data; retry succeeds after the fixture
  terminates its deliberately dead connection and restores network responses.

All external requests are intercepted; map tiles are synthetic image responses.
This verifies application layout and tile integration, not availability or visual
content of the public OpenStreetMap service. Screenshots were inspected.
The synthetic plan's map coordinates are explicitly supplied as Phoenix so
distance/marker positioning checks do not depend on omitted fixture fields.

Evidence in workspace parent: map-browser-results.txt, map-hosted-1440.png,
map-hosted-390.png, map-local-1440.png, map-local-390.png. The existing loading
browser suite was also attempted against this fixture; its separate output is
next-critical-loading-browser.txt. Its slow-load/refresh/failure/retry checks
completed, but the whole suite did not pass: it expects missing capture settings
from its original8113 fixture, whereas the available8107 fixture supplies them.
An initial text assertion and then visibility assertion failed for that mismatch.
This is not counted as a passing full suite; the new dedicated browser suite
above is the completed verification. Existing screenshots were not overwritten.

To reproduce, start `python tests/serve_import_plan_fixture.py`, then run
`node tests/operator_map_browser.cjs` with the installed Playwright module path.
The script uses the installed Windows Chrome path; an alternate environment
only needs its own Chromium executable path plus Python dependencies/Playwright.
No live database credentials are needed.

## What the server timing gap establishes

The supplied pre-PR11 warm request85f7ce5cd28a had planner8937.2ms wall and
1316.9ms worker-thread CPU (14.7% CPU/wall). Weather was1.3ms cached. Its
fixed-target altitude compute stage was2428.4ms wall/378.8ms CPU, and geometry
details1207.0/183.5ms. Similar ratios recur in computation-heavy stages. Therefore
external weather latency alone cannot explain this warm trace. Nested stage
durations must not be added, and the browser stopwatch was not matched to it.

The local workload is not identical production: different CPU/OS/runtime,
synthetic history, in-memory SQLite, fixed weather/clock, diagnostic IERS data,
and different releases/candidate counts. Even worker CPU was substantially
higher in the server trace than locally. The elapsed gap has both a compute-cost
difference and much more time outside that worker's measured CPU; it is not
valid to label all of it network wait, database wait, or hosting throttling.

`scripts/benchmark_cpu_contention.py` measures wall, process and worker CPU
without cProfile. Local quiet warm planner results (seconds):

| Run | Wall | Process CPU | Worker CPU |
| --- | ---: | ---: | ---: |
| Quiet1 |0.3486|0.3438|0.3438|
| Quiet2 |0.3494|0.3438|0.3438|
| One competing Python thread1 |1.7406|1.7813|0.4688|
| One competing Python thread2 |1.8215|1.8125|0.3281|

All runs kept the same targets and gap duration. This controlled experiment
shows GIL/scheduling contention can produce a several-fold wall/worker-CPU gap
without external provider or database I/O. It does NOT establish that production
has this contention. Process CPU includes every thread and is not attributable
solely to a request; Windows CPU timer granularity can give small discrepancies.
The first contended call hit the deliberate20-second safety cutoff (20.3475s
wall/20.25s process/0.4375s worker); do not treat it as a steady-state benchmark.
An earlier two-thread experiment was stopped because it also contended synthetic
ingestion; the committed harness confines contention to planner calls and caps it.

Evidence: cpu-quiet-results.txt and cpu-contended-results.txt. Comparison excludes
profiler overhead. Local results do not establish a production speedup.

## Unknowns and exact remaining access limitation

Repository render.yaml specifies a free web service, one Uvicorn worker, and a
separate forecast cron service. This does not verify actual current allocation.
The application starts a background art refresh after readiness; its concurrency
with a slow request has not been observed. No production process-wide CPU,
thread-pool queue, cgroup throttle or host scheduling counters were supplied.

Current connected tools expose GitHub deployment status but no Render runtime
logs/shell/metrics. Thus live CPU/quota/queue attribution is **unavailable**, not
an approval denial or an uncertain write. No production operation was attempted.
The minimal next evidence is a matched server request interval with process CPU
delta in addition to existing worker CPU, concurrent request/background-task
activity, and container cpu.max/cpu.stat deltas (where available). Request-entry
and worker-entry timestamps distinguish queue time before the timed planner.
Process CPU rising with wall while worker CPU stays low supports competing work;
low process CPU plus increasing throttled time supports a quota limit; neither
can be concluded from the current logs. Wait/lock/I/O or OS scheduling remain
other possibilities until those measurements are available.

No additional Doug stopwatch testing, infrastructure change or deployment is
needed to retain these findings. New release still requires approval.
