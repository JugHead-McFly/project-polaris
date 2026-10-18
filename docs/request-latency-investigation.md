# Remaining request latency: October 18, 18:24 UTC

Branch codex/request-latency; deployed base440179e0630105308d33fa2df0cb551b4f09d259.
No merge/deployment approved or attempted for this work. Prior rollback remains
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
