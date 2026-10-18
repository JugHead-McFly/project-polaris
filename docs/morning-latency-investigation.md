# Morning latency investigation — 2026-10-18

Verified production base: 5bea916b84a88e35ef0f0addcd892ecdb97af038.
Isolated branch: codex/morning-latency-investigation. Common-grid integration below.
No push, merge or deployment; no account/data/freshness/precision changes.

Doug reported a 24-second full load from an existing signed-in session at about
14:32 UTC. The supplied trace below is for a subsequent fresh Refresh Plan request.
This does not identify an authentication, cold-start or throttling cause, nor
establish a matched improvement over the preceding 31-second report.

## Evidence-backed candidates

1. Astroplan's next Moon rise and next Moon set both evaluate the same altitude
   grid. A local observer-scoped experiment reused only identical JD1/JD2 times,
   scale and arguments, retained the existing rise/set algorithms, and compared
   exact result JD components and masks. All seven cases passed, including
   Phoenix evening/morning, New York DST, Sydney, equator and polar cases.
   Warm baseline pairs took 0.083–0.095s; exact reuse took 0.044–0.050s, reducing
   two grid computations to one. This is a small part of a full request and
   does not eliminate downloads or explain the 24-second load on its own.

2. Fixed-target altitude transforms repeat a common night grid. A standalone
   matrix transform of 55 synthetic catalog targets × 41 identical instants
   matched every existing returned 0.1-degree altitude value, over three sites
   and three repetitions. Including fresh coordinate/time/frame construction,
   baseline took 0.225–0.236s; batching generally took 0.031–0.033s (one 0.057s
   run). This is a kernel experiment using the first 55 catalog entries, not
   Doug's exact selected targets or a full-plan benchmark. Per-target current
   instants and target-specific visibility-boundary refinements still require
   careful integration and may reduce the net benefit substantially. Moving
   and unknown targets must retain their existing paths. Do not simplify time
   sampling or freeze/reuse stale plans to obtain these gains.

Both probes use the project's pinned Astropy 6.0.1/Astroplan 0.10.1/NumPy 1.26.4
environment. They disable downloads only in isolated diagnostic processes;
the offline table emitted existing accuracy warnings. Comparisons use the same
table on both sides. They do not change or validate production reference-data
availability. Scripts contain assertions and are not imported by the app.

## Matched production trace and implementation

Fresh Refresh Plan request f218c67e4795 at 2026-10-18 14:41:39 UTC
returned POST /tonight 200 in 14,127.2ms. This is a separate request from the
reported 24-second initial page load. Altitude compute dominated at 6,751.6ms
(100 calls, 977.6ms thread CPU); planner totaled 13,039.1ms. Moon totaled
1,525.8ms, transit batching 1,016.3ms, darkness 602.7ms, cached weather 3.3ms.
Nested stages must not be summed. Wall/thread CPU ratios do not prove throttling.

The change batches fixed ICRS coordinates over the exact existing coarse night
grid and midpoint, in chunks of at most 64 targets. Results seed the existing
calculation-local exact-sample cache. Per-target current timestamps and visibility
threshold refinements remain computed at their original instants. Moving,
unknown and invalid-coordinate targets retain the existing per-target paths.
No change to goals, integration history, obstruction rules, equipment, setup,
weather, reference tables, stored data or cross-request caching is included.
Moon rise/set reuse remains a diagnostic experiment, outside this change.

## Validation and limits

Complete 55-candidate plan dictionaries and schedules are compared exactly with
both cache-disabled and deployed-behavior baselines. Cases cover Phoenix in
October/December, New York's DST fall-back night and Sydney in February, with a
completed M31 integration goal. Additional tests cover singleton/chunk boundaries,
empty grids, moving/unknown/invalid targets, repeated instants, DST folds, polar
and southern locations, request isolation and lazy current/refinement samples.
The planetary regression fixture now uses supported Jupiter; the earlier Mars
fixture exercised the unknown-target path.

Separate-process full POST measurements, after the existing reference startup
preparation, used 300 synthetic history sessions, memory SQLite, fixed weather,
real astronomy and the identical frozen 2026-10-18 03:24 UTC clock:

| Request | Deployed baseline | Common-grid batch |
| --- | ---: | ---: |
| First request in process | 1.117s | 1.025s |
| Warm 1 | 0.709s | 0.635s |
| Warm 2 | 0.716s | 0.643s |

Warm total improvement is about 10%; altitude work including batch preparation
fell from about 340-342ms to 264-267ms. Targets remained NGC7092, NGC1039 and
NGC2099; gap remained 0.8024867166666354 minutes. First-request measurements
exclude startup preparation and do not represent a cold Render wake or network
IERS download. Local timings cannot predict production latency. Offline tests
use the same reference table on both sides and emit existing IERS range warnings.
Production reference-data accuracy settings remain unchanged.

Evidence beside the worktree: altgrid-baseline-benchmark.txt,
altgrid-revised-benchmark.txt and altgrid-reviewed-tests.txt. Reproduction harness:
../benchmark_prepared_request.py, passed this worktree or ../polaris-long-dwell.
Final scheduler/history/request regression suite: 114 passed. Independent review also compared 14,560 exact outputs over 130 targets, four
contexts, 28 time samples and concurrent scopes.

Branch codex/morning-latency-investigation is based on live
5bea916b84a88e35ef0f0addcd892ecdb97af038. This candidate is not deployed.
Explicit deployment approval is still required; overnight approval is not reused.
All prior release and rollback branches remain intact.

Independent final review: no blocking findings; 69 regression tests passed.
Evidence: ../independent-common-grid-final.txt and ../independent-common-grid-edges.txt.
