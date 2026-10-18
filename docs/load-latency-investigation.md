# Investigation of the reported 67-second load

Review branch: `codex/load-latency-investigation`, based on deployed
`b4d9f155fee41cdda1cc8d1a583930681cf5b14c`. No new release is authorized or deployed.

## Production evidence

Doug supplied the relevant production log excerpt, read from Library file
`libfile_0f330e5c3a788191a40e4d6834c2153f`. At 02:03:20 UTC it records
`weather_ms=2645.3 computation_ms=62112.8 candidates=55`; at 02:03:23 it records
POST `/tonight`, request `3a2bec7c3d98`, duration 70898.8 ms. The matching incident
is dominated by planner computation, not weather. This bucket can include
astronomy-library I/O and CPU throttling; it is not a process CPU-time measurement.

The app was already healthy at 02:01:20. The document took 1.6 ms, account requests
1.3–1.5 seconds each in parallel, and health requests slowed during planning then
returned to about 10 ms. No IERS warnings or startup messages appear in the
provided excerpt. No browser credentials or new persistent access were used.

The earlier free-service wake-up hypothesis is superseded for this incident by
the healthy-before-request evidence. No paid-plan, keep-alive, worker-count or
deployment changes were made. Actual service CPU allocation/throttling and
production astronomy substages remain unmeasured.

## Confirmed code finding and correction

Independent profiling of the incident's date/time and a synthetic 50-candidate
workflow found 51 Moon-information calculations, 100 Moon separations and 153
body ephemerides. Every candidate recomputed the same midpoint Moon state, and
its warning recomputed the separation already obtained by the planner.

The planner now reuses exact Moon state and separation only within one calculation.
Keys include exact time (offset and DST fold), target where relevant, and the full
immutable observatory context. No approximate astronomy, cross-request plan cache,
IERS policy change, ranking change or candidate pruning is introduced. The cache
is released on normal return and exceptions. Two real-astronomy 55-candidate tests
compare the entire planner and scheduler outputs with reuse disabled: exact
equality, with body calls reduced from at least 165 to at most three per run.

The independent reviewer also reproduced repeated IERS primary/mirror attempts
when Astropy 6.0.1 downloads fail immediately (mocked, no network). The pinned
table is older than the incident date; silently disabling downloads is not an
accuracy-preserving correction. This remains a possible contributing path, not
an established production cause. The existing local benchmark disables those
downloads and runs on Gamerig, so it cannot predict Render latency.

After a successful primary or fallback weather response, 7Timer astronomy and
NWS cloud enrichment ran sequentially although their inputs are independent.
They now overlap using one short-lived worker, with all payload mutation on the
request thread and both results joined before caching or returning. Cache hits,
stale fallback, primary retry rules, provider timeouts, data freshness and
unavailable-value semantics remain unchanged. No provider is removed.

The controlled reproduction supplies identical synthetic provider responses and
300 ms / 400 ms delays. Sequential elapsed time was 0.701 s; parallel elapsed time
was 0.408 s, with identical returned data. This proves avoidable serial waiting;
it does not reproduce or explain the full 67 seconds.

## Diagnostic changes

Each request now collects fixed-name, aggregate stage durations and call counts,
correlated with its existing X-Request-ID. Logs and Server-Timing include auth,
account context/profile/observatories, capture history, weather primary/fallback,
7Timer/NWS, catalog load/shortlist, moon/darkness/altitude series, planner,
scheduling, recommendation persistence and forecast history/tracking.
Only internal labels, elapsed times and counts are recorded, never arguments,
coordinates, account identifiers, tokens, SQL or returned data. Failed requests
retain available timing evidence. Worker threads explicitly inherit the request
collector; concurrent requests remain isolated.

Stages overlap and nest: they must not be summed. Account/history stages include
their database work, not a separate SQL/pool transport breakdown. Time before
the app middleware runs (platform queue, process startup) is outside app timing.
Render startup logs and browser document timing are still needed to distinguish
those costs. IERS downloads remain inside astronomy stages; policy is unchanged.

The browser records one local Performance measure per loading stage under
`polaris:Secure session`, `polaris:Observatory`, and `polaris:Weather & plan`.
No telemetry transmission is added. Normal browser Navigation/Resource timings
provide document and request timings; the new measures cover session restoration
and response parsing too. Diagnostic failures cannot interrupt loading.

## Representative validation

The synthetic full hosted POST benchmark uses 300 capture sessions and 960
forecast records in an in-memory database, real astronomy and fixed weather.
With timing middleware enabled it measured 3.309 s first request and 2.525 / 2.602 s
warm. This is not a Render cold start and excludes remote providers, remote DB
transport and hosted JWT verification. Stage headers/log correlations were
verified. The warm synthetic request remains within the existing six-second
budget. The benchmark date advances with real time; target changes between runs
at different times are not themselves an output-equivalence test.

Regression coverage includes provider overlap and unchanged payload, provider
failure/cache behavior, thread propagation, concurrent request isolation,
exception cleanup, failed-request headers, browser timings without private data,
full-night visibility/goal constraints, and responsive UI/error/retry behavior.

Final combined validation after independent review: 244 Python tests passed (57 dependency/IERS
and polar-observation warnings), five Node loading tests passed, and headless
Chrome checks passed with no page errors across 15 viewport/target-count layouts.
The browser checks explicitly verify missing-settings wording, partial starting
exposure provenance, refresh/retry behavior and local Performance measures.

Capture recommendation corrections are documented separately in
`catalog-capture-settings-review.md`. Empty values say "Capture settings
unavailable". Partial category-based recommendations explicitly say to confirm
gain/filter on the device; no empirical calibration is invented.

## Remaining decision

Independent review passed after corrections. Deployment approval is still required.
The dominant production stage is confirmed, but the improvement on Render remains
unverified until an approved release is measured there. These changes must not
be presented as a verified resolution of the full reported incident.

Independent fixed-date after-profile: warm planner 4.773 to 2.327 seconds and
4.879 to 2.370 seconds (about 51% lower); cold 5.247 to 2.916 seconds. These
include profiling overhead. Moon-information calls fell from 51 to two, Moon
separation calls from 100 to 50, and total body ephemerides from 153 to four
(including observer rise/set calculations). Selected objects and coverage matched.
