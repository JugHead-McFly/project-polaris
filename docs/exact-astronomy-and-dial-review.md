# Exact astronomy reuse and dashboard refinements

Base: deployed develop 547feb013ebf3b4c54f94ce5b7c285964ab6aa0a.
Feature branch: codex/exact-altitude-reuse. Not deployed.

## Evidence and changes

The October 18 post-release logs supplied by the operator show two different
requests: 51.070 seconds initially and 27.798 seconds warm. Warm planner
computation was 27.262 seconds, including 11.842 seconds in 210 altitude-series
calls. Weather was 2.3 milliseconds warm. These are elapsed times, not measured
CPU times. Cold Moon work was 16.101 seconds versus 1.759 seconds warm; the logs
alone cannot distinguish table initialization, IERS I/O, or CPU throttling.

An isolated fixed-time Phoenix fixture with 50 candidates and 300 synthetic
capture sessions found 100 duplicate altitude samples: midpoint/current-time
values were already in visibility batches and then recomputed individually.
Exact per-calculation reuse now preserves all sample times, timezone offsets,
DST folds, targets, and full observatory context. It returns fresh result lists,
retains vector evaluation for misses, and ends with the planner scope.

Fixed-target transits used the same Astroplan time grid in 50 separate calls.
They now broadcast coordinates across that identical grid once, then seed exact
per-calculation results. Moving/ephemeris targets retain their scalar path.
Single-target scalar return shape is explicitly handled. There are no changes
to candidate selection, integration goals, visibility sampling, IERS policy,
astro precision, or full-night scheduling rules.

Local warm planner wall time changed from 1.408/1.406 seconds to 0.705/0.694
seconds (about 50 percent). Full synthetic POST changed from 1.419/1.417 to
0.716/0.705 seconds. Altitude computation fell from 192 evaluations to 92;
transit batch took about 46 milliseconds versus roughly 530 milliseconds for
separate transit calls. Targets and the 0.802-minute residual gap were unchanged.
This fixture disables IERS downloads, uses fixed weather and a memory database,
and runs on Gamerig. It does not establish future Render runtime.

New transit/transit_batch and altitude_compute timings identify previously
unlabelled work. request_stage logs add thread_cpu_ms. Similar CPU/wall values
support CPU-bound execution; a large gap can indicate I/O, lock waits or CPU
quota/descheduling and is not proof of network latency. Render CPU/throttling
metrics plus download/error timestamps distinguish those possibilities. Thread
CPU excludes other worker threads; nested stage values must not be summed.
Windows timer resolution may make small aggregated CPU values exceed wall time.

## User interface

Opportunity score is again a percentage dial. Border, ring and subtle interior
fill use the same semantic band: excellent >=85, good >=70, fair >=55,
challenging >=35, poor below35. Visible labels and accessible percentage text
provide a non-color cue. Unavailable is neutral; a hard stop keeps STOP and its
reason rather than suggesting a good percentage authorizes imaging.

The display label changes ordinary Use Caution outcomes to Fair conditions.
Heat >=95F, wind >=15mph and humidity >=80 percent preserve caution and the
server explanation, including when current conditions are worse than forecast.
Stale/uncertain forecasts, high cloud and missing data have distinct labels.
Backend decision values, advisories and safety rules are unchanged.

Native details/summary disclosures now share one right-aligned chevron with
consistent dimensions and expanded rotation. This covers dynamically generated
details too. Native keyboard and accessibility expanded state are preserved.
Plus/minus disclosure glyphs and the separate confidence arrow were removed.

## Validation

107 astronomy/planner/scheduler/request-timing tests passed, including complete
55-candidate plan and schedule equality for October and December, scalar/batch
transit equality across latitude/season/single-target cases, DST folds, moving
targets, mutation isolation and unavailable targets. Dependency/IERS warnings
remain expected in isolated offline astronomy tests.

Dashboard asset tests, Node wording/loading tests, and headless Chrome checks
cover five score bands, unavailable/hard-stop states, five widths from 320 to
1440 pixels, keyboard Enter/Space toggling, chevron alignment, reduced motion,
and no horizontal overflow or page errors. Synthetic preview is port 8114.

No production records, observations, calibration output or backups were changed.
No new merge or deployment is authorized. Further release review/approval is
required before deploying this branch.

## Storage and feature inventory requested by the operator

Catalog facts are bundled files, not a target database table:
app/data/catalog/openngc.csv plus source.json and its license. The manifest
records 12,036 usable deep-sky entries and 12,935 aliases. catalog() verifies
the SHA256 and caches parsing once per process. Curated recipes and rig data
are app/data/targets.py, seasonal_targets.py and rig_profiles.py.

Account capture_history stores target, filter, frames, integration and source
identity. Integration goals derive from goal_engine_service/portfolio policies;
they are not independent persisted user goals per filter. profiles and
observatories store account/site configuration. recommendation_runs stores
primary target, explanations and input provenance; it is not a complete reusable
schedule/sky-geometry cache. Each load recomputes relevant geometry and the plan.
Weather already has freshness-bounded in-memory caching.

Existing: full-night schedule timeline, target altitude curves, Moon-aware filter
advice, rig field-of-view checks, cloud source spread and historical forecast
reliability evidence. Partial: manual mosaic advisory and filter-level history.
Not found in current implementation: executable mosaic panel coordinates or
sequence export, interactive rotation/framing simulator, user skyline model,
favorites/future best-night watchlist, target swap/lock controls, explicit replan
from now, seven-night comparison, DWARF app capture handoff, or accepted-frame
integration goals separately per filter. Forecast model agreement is measured;
it is not a calibrated probability of clear skies. No extra features were added.
