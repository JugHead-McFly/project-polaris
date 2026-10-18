# Remaining request latency: October 18, 18:24 UTC

Branch codex/request-latency; deployed base440179e0630105308d33fa2df0cb551b4f09d259.
Historical review status: no merge/deployment was approved at that point; see the completed release record below. Prior rollback remains
5bea916b84a88e35ef0f0addcd892ecdb97af038 on codex/rollback-before-common-grid.

## Production evidence and attribution limits

Doug observed a signed-in reload16s and subsequent Refresh Plan11s at11:24 Arizona.
Supplied stages align in time/order, but lack request_complete totals. They are
not exact end-to-end browser traces, and the five-second difference is not a
measured single component. Stage timings nest/overlap and must not be summed.

| Stage (ms) | bf637d75a882 18:24:25 | 85f7ce5cd28a 18:24:51 |
| --- | ---: | ---: |
| Planner wall / thread CPU | 12269.4 /1598.1 | 8937.2 /1316.9 |
| Weather | 3041.3 | 1.3 cached |
| Altitude compute | 2581.9,55calls | 2428.4,55calls |
| Common grid | 696.4 | 599.4 |
| Geometry details | 1208.6 | 1207.0 |
| Moon | 2020.2 | 1623.6 |
| Darkness | 503.7 | 511.2 |
| Transit batch | 906.9 | 892.3 |
| Schedule | 1492.3 /210.7CPU | 1.7 |
| Forecast history /tracking | 372.5 /481 | 337.8 /387.8 |
| Save | 119.8 | 87.0 |

Warm Moon rise/set consumed704.7/696.9ms. Initial parallel account requests at
18:24:10 logged auth1304-1336ms, with profile92.6ms and observatories21.6ms.
The large wall/thread CPU gap spans multiple stages. It does not prove CPU
throttling. Resource quota/throttled time, queue waits and matching request totals
remain unmeasured. No paid hosting or security/authentication changes are made.

## Confirmed code paths and implemented changes

1. Moon next-rise and next-set use identical Astroplan altitude grids. A private
observer exists only for this pair and caches one exact grid up to1024 samples,
keyed by both Julian-date components, shape, scale and mask. Custom wavelength,
attached time-location and alternate gridding bypass reuse. Results are copied.
New requests always compute fresh moving-body data; no time rounding, interpolation
or cross-request ephemeris cache is used. Existing rise/set algorithms are unchanged.

2. Fixed catalog coordinate parsing repeats. A512-entry LRU caches only parsed
ICRS coordinates keyed by actual RA/Dec strings, with defensive copies for callers.
Changed catalog values immediately miss; aliases with identical values may share.
No account, plan, history, equipment, weather, site-dependent or moving geometry
is stored. Non-string inputs retain the original parsing path; failed parses are
not cached. Static ICRS parsing does not depend on Earth-orientation tables.

3. First schedule initializes and validates1000 artwork paths. Independent local
schedule measurement was341.237ms cold versus.090/.056ms warm with identical blocks.
This strongly supports the cold-artwork explanation but does not independently
attribute the entire production1492ms to it. Validation is retained, the root path
is resolved once per load, and existing startup preparation now includes a separate
art-catalog stage. Failure defers to the ordinary retry path. art_catalog_load timing
will expose cold request-time retries. Moving work before readiness does not remove
cold-wake cost.

## Frontend, weather and database findings

Normal loading is session restoration -> parallel profile/observatory/rig reads ->
one POST/tonight -> render. No confirmed duplicate normal-load request. Same-account
auth updates do not restart planning; refresh disables its buttons immediately.
Abort/supersession prevents stale rendering, but does not prove server computation
was cancelled. Optional rig retrieval also controls EQ availability, so removing
that dependency blindly would change equipment behavior.

Existing loading.js records local DevTools polaris:Secure session,
polaris:Observatory and polaris:Weather & plan measures. No duplicate diagnostics
or fake progress were added. Old plans remain explicitly labelled while refreshing.

Weather already has site-keyed freshness caching and parallel supplementary work;
the warm trace confirms a cache hit. Database-related forecast stages remain visible
but their exact network/query contribution is unproven. Whole-plan caching was
rejected because current visibility, history/goals, weather and equipment require
fresh evaluation. Darkness is calculated twice at slightly different implicit-now
instants; combining those calls needs an explicit request-time contract and was
not silently treated as exact reuse in this patch.

## Validation and representative isolated timing

145 relevant tests passed before the added18:24 complete-plan case. Exact whole-plan
and schedule comparisons disable the new coordinate cache and Moon-event reuse for
the baseline. Moon comparisons check both JD parts and masks, including polar/DST
cases. Cache tests cover changed coordinates, caller mutation, bounded eviction,
concurrency and missing/invalid fallback. Startup tests cover independent art failure
and retry without logging failure details. Existing artwork safety tests pass.
Independent review separately compared24site/date Moon pairs against plain Observer.

At the reported18:24 UTC clock,300 synthetic history sessions, fixed weather,
memory SQLite, real astronomy and existing reference preparation:

| Measurement | Deployed | Revised |
| --- | ---: | ---: |
| Preparation | .293s | .557s |
| First request after preparation | .884s | .477s |
| Warm1 | .499s | .404s |
| Warm2 | .493s | .399s |

About19% local warm improvement. First-request gain includes relocating art loading
into preparation. TargetsNGC6871/NGC1039/NGC2099 and gap.652367383333285minutes match.
This excludes provider/network delays and is not proof of a five-second production
refresh. Offline tests use the same IERS table on both sides and emit existing range
warnings; production freshness/precision policy is unchanged.

Reproduce: python scripts/benchmark_request_latency.py <repository-root>
Use the previous worktree to measure the unchanged deployed application baseline.
Evidence beside worktree: request-day-baseline.txt, request-day-revised.txt,
request-final-tests.txt, request-day-plan-tests.txt, independent-schedule-art-cold.txt,
independent-moon-grid-pairs.txt. These are synthetic-only runs, not production load tests.

## Access and remaining evidence

No callable Render application-log connector or signed-in browser-control tool was
available. GitHub deployment records do not include application request logs. The
parent supplied sufficient stage logs to proceed; no credentials or repeated log
paste are needed. A future production validation should correlate request_complete
and stages by request ID, plus existing browser stage measures if assessing reload.
No production improvement for this unshipped change has been measured.

Final verification: all five complete-plan cases passed, including18:24UTC (146 distinct relevant cases across the broad and focused runs). Independent review found no blocking issues after88 distinct regression cases plus24 independent exact Moon comparisons. Evidence independent-request-guards.txt resolves the earlier test-only unit-assignment failure.

## Release completed and subsequent evidence (updated October 18)

This change is now deployed through PR11:
https://github.com/JugHead-McFly/project-polaris/pull/11

- Reviewed source: `4d831fa77c298525aae222a5f5ab2ce4d2e01a87`.
- Final live merge: `3a1e279fed12265712a411d5c2f4da72a7c290d5`.
- Render deployment record: `7158911587`.
- Render success: **2026-10-18 18:37:48 UTC**.
- Live and ready endpoints: HTTP200, exact final SHA; operator HTTP200.
- loading.js, operator.js and operator.css: byte-identical to reviewed source.
- Rollback: `440179e0630105308d33fa2df0cb551b4f09d259`, verified remotely
  on `codex/rollback-before-request-latency`.

The earlier references to this change as unshipped describe its review state;
this release record supersedes those status statements. No rollback was performed.

### User observations and the cutover boundary

| Report time (UTC) | User-observed reload | User-observed Refresh Plan | Attribution |
| --- | ---: | ---: | --- |
| October18 18:24 | 16s | 11s | Before PR11; stage logs below/above, no request_complete total |
| October18 18:36:04 | 12s | 12s | Before PR11 completed; corresponding supplied stages at18:35 |

A direct health read at **18:37:26.2924022 UTC** still returned previous SHA
`440179e0630105308d33fa2df0cb551b4f09d259`, with Render in_progress. Thus the
18:35 logs and report at18:36 cannot be used to judge PR11. These are user-observed
end-to-end times; no exact request-to-browser association or request_complete total
was supplied. No post-cutover authenticated fresh-plan trace is recorded yet.

### Additional pre-cutover production stages

All durations below are milliseconds. Nested stages overlap; do not sum them.

| Stage | ef54901fb274 at18:35:34 | 9e81097546bd at18:35:56 |
| --- | ---: | ---: |
| Planner wall / thread CPU | 8646.3 /1276.3 | 8932.9 /1324.8 |
| Weather | 1.3 cached | 1.3 cached |
| Altitude series | 3019.3 | 2874.6 |
| Altitude compute | 2335.8,55calls | 2340.0,55calls |
| Common grid | 602.1 | 715.0 |
| Geometry details | 1197.0 | 1374.9 |
| Moon | 1623.3 | 1619.0 |
| Darkness | 599.3 | 505.7 |
| Transit batch | 803.5 | 896.9 |
| Forecast history | 442.7 | 1474.9 /218.5CPU |
| Forecast tracking | 514.0 | 1581.0 /226.9CPU |
| Schedule | 1.8 | 88.1 /1.9CPU |

Initial account requests at18:35:25 ran in parallel:

- ee88ae62992e: auth1105.6ms /58.6ms thread CPU.
- a418fbe8faa1: auth1100.3ms /56.4CPU; observatories95.9ms /2.7CPU.
- 2fa0adb637c6: auth1180.2ms /52.8CPU; profile94.5ms /2.1CPU.

Do not add these parallel auth durations or label authentication the whole
bottleneck. Forecast history/tracking variability is a remaining investigation
candidate; the trace alone does not establish a database or network root cause.

### New startup reference logs

| Logged at (UTC) | Stage | Status | Wall ms | Thread CPU ms |
| --- | --- | --- | ---: | ---: |
| 18:37:42 | astronomy_reference | ready | 12871.3 | 937.7 |
| 18:37:46 | catalog_reference | ready | 3492.4 | 517.5 |
| 18:37:47 | art_catalog_reference | ready | 900.4 | 136.2 |

These are preparation stage completion logs for the new startup, consistent with
Render success at18:37:48. They confirm artwork preparation succeeded. They do not
separate downloads, native CPU, scheduling or throttling. The preparation cost is
paid before readiness; cold wake remains a distinct latency concern.

### Resume here; avoid repeating completed work

1. Keep deployed SHA3a1e279 as the reference; confirm a later measurement's release
   before comparing performance. Capture the request ID and total when available.
2. Use existing browser polaris:* measures for session/account/plan phases. No
   confirmed duplicate normal-load request exists; do not add redundant diagnostics.
3. Investigate remaining55 current-time transforms and duplicate darkness work
   only while preserving exact/current-time semantics or explicitly defining a
   reviewed consistent request-time contract. Do not introduce rounded-time reuse.
4. Separate forecast-history/tracking waits, process/native CPU, queueing and host
   resource evidence before claiming database latency or CPU throttling.
5. Preserve all live observations, calibration output and backups. No paid upgrade,
   credential/security change, migration, production load test, broad NAS grading
   or additional deployment is authorized by documentation/performance research.
6. Maintain independent review and release approval for subsequent app changes.

Useful-page2-3s and fresh-plan roughly5s remain goals, not verified outcomes.
Existing code, fixture scripts and evidence should be reused rather than repeating
whole completed investigations. Detailed prior release records are indexed in
`../overnight-release-handoff.md` in the task workspace.
