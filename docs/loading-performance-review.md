# Loading, performance and observing UI review

Branch `codex/initial-loading`, based on deployed merge
`f16cbef570daba1f83444f17b2f7c2e70ae740ae`. Review only: no push, merge or deployment.

## Measured performance

The reported production page load was approximately three minutes. We have not
reproduced that entire delay or obtained its authenticated production request
trace, so neither Render cold start nor one specific provider is a confirmed
explanation for all three minutes.

A confirmed CPU bottleneck was fixed: `get_altitudes_at` transformed every sample
individually. A 52-candidate profile made 2,973 scalar transforms. Under cProfile,
visibility took 13.69 seconds of the planner's 18.68 seconds. Those instrumented
times are not the uninstrumented request measurements below.

Fixed deep-sky coordinates now broadcast over the identical sample times in one
Astropy transform per series. Rounding remains one decimal place. Moving and
ephemeris targets keep their existing time-dependent path. No candidate is
removed and no visibility floor, time zone, date, location, rig or goal changes.
No cross-request plan cache or user-data cache was introduced.

Full hosted POST `/tonight` benchmark on Gamerig, including database history,
planning, scheduling, recommendation persistence, forecast summary and response
serialization, using an isolated in-memory database and 300 synthetic captures:

| Version | First request | Warm requests |
|---|---:|---:|
| Before vectorization | 8.639 s | 7.830 / 7.931 s |
| After vectorization | 3.084 s | 2.403 / 2.470 s |
| Final build | 3.194 s | 2.418 / 2.477 s |
| Final with 960 additional forecast records | 3.138 s | 2.461 / 2.483 s |

All runs selected NGC7092, NGC1039 and NGC2099 and retained the same full-night
coverage, with about 0.802 minutes of rounded boundaries. The tiny difference in
boundary fractions between runs comes from current time, not a changed cutoff.
The warm synthetic request budget is six seconds, explicitly checked by
`scripts/benchmark_tonight.py --check-budget`. Add `--forecast-history` for the
larger history case. These are local machine measurements, not a Render SLA.

The benchmark fixes clear weather and disables IERS downloads; it excludes live
provider latency, remote PostgreSQL transport, hosted JWT verification and web
service startup. A separate public-provider probe on Gamerig measured weather
retrieval at 2.975 seconds cold / 0.001 seconds cached and a single real astronomy
query with normal IERS behavior at 0.294 / 0.003 seconds. This does not prove
Render had the same cache or network conditions during Doug's slow request.

Additional changes:

- Account/profile, observatory and rig-profile reads begin in parallel.
- POST no longer computes forecast history twice: the updated summary returned
  after recording the forecast is used. GET behavior remains unchanged.
- Existing full-request logs gain a matching `Server-Timing: app` response header.
  Planner logs separate weather elapsed time, computation time and candidate
  count. Logs contain no coordinates, account IDs, tokens or capture details.
- No security settings, database migrations, paid resources, provider freshness
  settings or production IERS policy changed.

Existing possible latency sources still include two primary weather attempts at
10 seconds each plus retry delay, secondary providers, Earth-rotation table
retrieval, remote database latency, CPU allocation and startup. Authentication
already caches JWKS for 300 seconds with a five-second network timeout. No
evidence supports disabling those checks or changing infrastructure here.

## Loading behavior

The initial view has a plain dark background, teal indeterminate rings and real
waiting/loading/ready/error states. There are no invented percentages. Hosted
session restoration is followed by Observatory and Weather & plan stages.
Weather, history and planning are bundled in `/tonight`, so the UI does not claim
independent completion. Local mode tracks its three real requests separately.

Header/account controls remain available. Empty cards and zero/unknown placeholder
metrics stay hidden until useful data arrives. Refresh retains the previous plan
and adds a small updating message; errors explicitly say the previous plan has
not refreshed. Requests are bounded at 90 seconds with retry. Superseded requests
are aborted and their responses ignored. Signing out or changing accounts clears
display ownership. Reduced motion stops ring animation. Retry restores focus to
the loaded plan heading, and errors/status text are accessible.

## Requested observing UI changes

- Removed catalog search UI; the full backend catalog and automatic discovery
  remain intact.
- Removed redundant date/rig/time-zone line and imaging-progress disclosure from
  the heading. Importer/history access is in existing account settings.
- Removed Forecast details, Planner notes, target ranking/debug exposition,
  repeated live-sky reminders and horizon boilerplate. Real dew/mosaic/error
  states remain concise.
- Opportunity score and all eight metrics are visible in the first card without
  expanding anything. Missing metric inputs say Unavailable.
- Forecast history reports a factual number of nights recorded, or History
  unavailable; qualification remains inside the history section. No clock icon
  or Collecting label implies a load in progress.
- Target cards have no Setup & details disclosure or repeated wide warning.
  Known settings remain inline; unknown settings get one short Settings not
  configured line. Empty exposure/gain/filter fields are omitted, not invented.
- One through four cards share one row when readable on a wide desktop. Five
  wrap; tablet and phone layouts adapt. Real altitude charts and chronological
  order remain intact.

## Validation and remaining release check

184 Python regressions passed, including exact scalar/vector equality across
three dates/latitudes and three targets, moving-target handling, seasonal nights,
goals, API/import/account isolation, forecast history and auth. Thirteen Node
tests passed, including delayed/out-of-order results, partial failure, abort,
timeout and retry.

The browser harness `tests/operator_loading_browser.cjs` uses only the synthetic
local fixture. It checks desktop/mobile loading, reduced motion, failure/retry,
retaining a good plan, sign-out before a late response, local partial failure,
visible metrics, absent debug/search/header content, omitted empty settings and
all 15 combinations of 1–5 cards at 1536/900/390 pixels. No JavaScript errors or
horizontal overflow. Screenshots were inspected locally.

Preview remains http://127.0.0.1:8113/operator on Gamerig. It is synthetic and
does not access Doug's live history. Screenshots and timing output are in the
parent task workspace. Live observations, calibration output and backups were
not changed. Production still runs f16cbef until a separately approved release.

After approval, measure a signed-in production cold load and refresh using the
new Server-Timing and existing request IDs/logs. That is needed to attribute the
unreproduced remainder of the three-minute delay and confirm deployed latency.
