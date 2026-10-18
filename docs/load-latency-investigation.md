# Investigation of the reported 67-second load

Review branch: `codex/load-latency-investigation`, based on deployed
`b4d9f155fee41cdda1cc8d1a583930681cf5b14c`. No new release is authorized or deployed.

## Production evidence and blocker

Doug reported a 67-second full load at 2026-10-18 02:03:37 UTC. That is a user
observation, not a captured request trace. This executor has no Render connector,
Render CLI, exposed Render token environment variable, or browser-session tool.
No browser credential store was accessed and no new persistent access was created.
The earlier public shell timings cannot establish the authenticated load time.

The smallest useful input is the existing Render service log excerpt around
02:02–02:04 UTC containing `request_complete`, `planning_timing`, and any process
startup lines. A browser Network timing capture of the slow load, with request IDs
and Server-Timing but no cookies or Authorization headers, would separate the
document/session/account/plan stages. Parent handles this request to the user.

`render.yaml` specifies the free web-service plan. Render's documentation says
free services idle after 15 minutes without traffic and take about one minute to
wake: https://render.com/docs/free#spinning-down-on-idle . This is a plausible
hypothesis, not confirmation of the actual live plan or this request's delay.
No paid-plan, keep-alive, worker-count or deployment changes were made.

## Confirmed code finding and correction

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

Final combined validation: 233 Python tests passed (53 existing dependency/IERS
and polar-observation warnings), five Node loading tests passed, and headless
Chrome checks passed with no page errors across 15 viewport/target-count layouts.
The browser checks explicitly verify missing-settings wording, partial starting
exposure provenance, refresh/retry behavior and local Performance measures.

Capture recommendation corrections are documented separately in
`catalog-capture-settings-review.md`. Empty values say "Capture settings
unavailable". Partial category-based recommendations explicitly say to confirm
gain/filter on the device; no empirical calibration is invented.

## Remaining decision

Review and deployment approval are required for these changes. The production
67-second cause remains unresolved until the authenticated trace/log evidence is
available. These changes must not be presented as a verified resolution of that
reported incident.
