# Deeper latency investigation, 2026-10-18

Isolated branch: codex/deeper-latency, base d783e4bd0cb0b5fe37a6e2e11a0588e7b00544aa.
Application code is unchanged. Scripts are explicit opt-in synthetic experiments.
No paid upgrade, production load test, database changes or additional deployment.

## Measured critical path

The previously supplied production refresh f218c67e4795 took 14.127s, including
6.752s altitude compute. It predates the proposed common-grid release. No newer
production refresh trace is available. The separate reported 24s initial page
load cannot be equated with that request. A free-instance warning establishes
the hosting tier, not CPU throttling.

A local cProfile of the synthetic 50-target request after common-grid batching
found 92 altitude computations, 242 coordinate constructions, 50 Moon separations
and 162 SkyCoord transforms. The planner calls darkness calculation twice,
once for labels and again for datetime bounds. These implicit-now calls currently
use slightly different instants: combining them requires an explicit request-time
contract, not pretending they already have identical inputs.

Profiled planner wall time ~1.23s and process/thread CPU ~1.20s. Profiling roughly
doubles runtime and must not be used as an uninstrumented latency baseline.
Local native-worker CPU does not explain the production wall/thread gap. Production
CPU quota/throttled time, worker queueing and cold-start events remain unmeasured.
Process-wide CPU under concurrent requests also cannot be attributed to one request.

## Exact geometry prototype

scripts/probe_exact_geometry.py installs an experiment only when explicitly called.
It uses existing coarse samples to select the identical one-minute threshold
refinements, transforms the ragged coordinate/time pairs together, and batches
fixed-target Moon separations at the existing midpoint. Original per-target
current-time samples remain lazy. It introduces no cross-request cache.

Initial implementation repeatedly assembled coordinate objects and mostly erased
the benefit (~0.62s warm). Indexing one coordinate array instead yielded:

| Synthetic full POST | Common-grid reviewed | Indexed prototype |
| --- | ---: | ---: |
| First request after startup preparation | 1.025s | 0.909s |
| Warm 1 | 0.635s | 0.497s |
| Warm 2 | 0.643s | 0.497s |

This is about 22% additional local warm improvement, about 30% against the original
0.709-0.716s baseline. Identical fixture: memory SQLite, 300 synthetic sessions,
real astronomy, fixed weather and 2026-10-18 03:24 UTC. Targets and gaps matched.
Do not extrapolate this to a five-second production promise. First-request values
exclude startup preparation, network providers and Render cold wakes.

Reproduce from repository root with the project Python environment:

    python scripts/benchmark_exact_geometry.py .
    python scripts/profile_tonight_geometry.py .

Both scripts set test environment/memory database and disable IERS downloads for
the isolated experiment. Existing stale-table warnings limit absolute astronomical
accuracy; equality comparisons share the same table. No production reference-data
settings are changed.

Before production integration: bound paired arrays/chunks, preserve invalid/nonfinite
coordinate error behavior, share threshold-refinement logic instead of duplicating
it, add per-stage timing for new work, and test moving targets, chunk boundaries,
multiple disjoint intervals and changing reference-data conditions. Do not expose
the install monkeypatch as production code.

## Other concrete opportunities and constraints

Independent coordinate microbenchmark: 242 parses median59.97ms;50parses plus242
SkyCoord defensive copies median17.26ms across seven runs. Request-scoped static
coordinate reuse is worth integrating with the batching work. Defensive copies
prevent caller mutation. Moving coordinates must retain exact time/site inputs.

Frontend source shows session restoration -> parallel profile/observatory/rig
reads -> POST /tonight -> render. Optional rig retrieval gates the plan, but also
controls EQ availability; deferring it blindly could change equipment behavior.
Measure fixed-name performance marks for session/account/plan/JSON/render first.
Production contribution of that gate is unknown. Existing refresh keeps the prior
plan visible with an explicit updating label; initial load has no prior result.
Useful content in 2-3s may require a separately measured account/conditions view,
without inventing progress or presenting an old plan as current.

Avoid whole-plan or rounded-time geometry caches. Precise invalidation includes
reference tables, coordinates, full observatory context, sample instants/folds,
equipment/goals/history/weather and algorithm version. Night bounds themselves
currently depend on exact reference time, so a date-only cache is not equivalent.
Request-scoped reuse avoids these cross-request freshness hazards.

## Deployment gate

PR9 publication and rollback branch succeeded. Automatic approval review rejected
the merge that triggers Render: it judged supplied approval insufficiently explicit
for merge/deploy. That command did not execute. Parent must provide explicit
confirmation to merge PR9 and deploy Render before a retry. The later instruction
to keep digging authorizes this research, not additional deployment.

Evidence beside worktree: deeper-profile.txt, deeper-prototype-indexed-benchmark.txt,
deeper-indexed-tests.txt. Independent review follows separately.

## Review and guarded prototype

Independent review matched 249 complete visibility dictionaries and 249 midpoint
Moon separations (83 targets across New York DST, Sydney and north polar contexts).
Evidence: ../independent-exact-geometry-probe.txt. It correctly identified that the
prototype is not production-ready. Follow-up research guards now handle empty
inputs, invalid-coordinate lookup, nonfinite rows, duplicate install calls and
512-pair transform chunks. Full pair-list allocation and target-array size still
need explicit bounds for general callers, and the implicit coarse-grid/midpoint
API should be replaced during production integration. Error/concurrency tests
must cover that final API rather than just a monkeypatch.

The guarded prototype benchmark is 0.910s first prepared request and 0.513/0.518s
warm, about 19% faster than the reviewed common-grid candidate (not 22% for this
final guarded variant). Evidence: ../deeper-bounded-benchmark.txt. These are local
synthetic findings, not a production target guarantee. The application remains
unchanged and no new release is proposed by this research artifact.

Guarded prototype validation: 53 tests passed, including four exact whole-plan/schedule cases. Evidence: ../deeper-bounded-tests.txt.
