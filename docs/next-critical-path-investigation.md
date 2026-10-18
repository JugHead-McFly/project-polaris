# Remaining startup and planner critical path

## Status and provenance

Isolated branch `codex/next-critical-path`, base production merge
`3a1e279fed12265712a411d5c2f4da72a7c290d5`. No merge, push or deployment is
authorized for this new work. The original E: checkout, observations, calibration
output and databases were not modified. Prior rollback remains
`codex/rollback-before-request-latency` at `440179e0630105308d33fa2df0cb551b4f09d259`.
The prior detailed release record is retained in request-latency-investigation.md,
including its post-release documentation-only changes.

Doug's October18 **18:40:16UTC** observation was **reload14s / RefreshPlan8s**.
This is the first user-observed pair after confirmed deployment18:37:48UTC. It
has no matched server trace, and one trial cannot establish a reliable gain.
No further user stopwatch tests have been requested.

## Verified findings and changes

1. Every planner invocation computed darkness twice: once for presentation and
   again for scheduling. Each implicitly sampled the current clock. Besides
   duplicate work, crossing dawn between calls could select different nights.
   The planner now calculates one window and passes that exact tuple to the
   formatter. Standalone callers still calculate normally. The darkness timing
   decorator now measures the physical calculation, not the formatter. Polar
   missing-window behavior and DST offsets are retained. No cached night,
   rounded timestamp, changed IERS policy or cross-request/account reuse.
2. A148KB Leaflet script was the first deferred script in the document, ahead of
   authentication/loading/operator code, despite hosted tonight never rendering
   a map. It now loads only when a map consumer needs it. Single-flight loading,
  15-second timeout, error cleanup and retry preserve local maps. Saved site
   lists/directions still render if the library fails; this was corrected after
   independent review. Stale load generations cannot render after awaiting the
   library. Existing Leaflet CSS and CSP remain unchanged. Actual production
   startup benefit is unmeasured.

## Evidence

All Python checks used in-memory synthetic data, no live history or external
weather providers. Astronomy diagnostics disable IERS download only in the
isolated harness; stale-range and polar warnings are expected and limit claims.

- 77 Python tests passed: single-window, full-night scheduling, calculation cache,
  request latency and seasonal catalog. Includes complete frozen plans, DST,
  polar no-window, same formatter output and a simulated dawn-boundary race.
- 15 dashboard tests passed, including local assets/security assertions.
- 10 Node tests passed: loading coordinator, lazy library, one shared request,
  error/missing-global/timeout retry, saved-site fallback and stale render guard.
- Independent review:61 overlapping Python tests and10 Node tests passed;
  no remaining blocking code findings. These are not additional unique tests.
- Matched local full-POST benchmark at2026-10-18T18:24UTC: production code
  first/warm0.470/0.399/0.400s; revised0.441/0.355/0.365s. Same targets
  NGC6871,NGC1039,NGC2099 and gap0.652367383333285minutes. Roughly10% warm
  reduction on this machine; not a hosted latency prediction. cProfile was used
  only for attribution because its instrumentation adds overhead.

Evidence files in parent workspace: next-critical-profile.txt,
next-critical-baseline.txt, next-critical-benchmark.txt, next-critical-tests.txt,
next-critical-dashboard-tests.txt, next-critical-js-tests.txt,
independent-single-window-tests.txt, independent-map-loader-tests.txt.

Reproduce backend measurements with the repository Python environment:
`python scripts/benchmark_request_latency.py .`.
Reproduce focused frontend checks with
`node --test tests/operator_map_loading.test.cjs tests/operator_loading.test.cjs`.

## Remaining work and constraints

- Browser verification is now complete using the installed standalone Playwright
  runtime and temporary headless Chrome; see browser-and-cpu-verification.md.
  The app-browser tool remains unavailable, but that is no longer a verification
  blocker. No user's Chrome session was accessed.
- Remaining warm planner cost is dominated by per-target current altitude
  transforms. Fresh per-target timestamps are preserved. Replacing them with a
  common timestamp or interpolation would require a deliberate contract change;
  this work does neither.
- Secure session -> parallel account/profile/rig reads -> plan remains the hosted
  dependency chain. Rigs affect equipment eligibility. Combining endpoints has
  no proven benefit: fewer auth/DB transactions might help, sequential queries
  might offset it. No speculative endpoint rewrite was made.
- Startup astronomy preparation was12.87s wall/0.94s thread CPU in supplied
  production logs. This establishes a cost, not a CPU-throttling diagnosis.
  The NASA background refresher still supplies reference-image metadata and
  was not removed. Runtime CPU quota/queue data and request logs are unavailable
  through current connected tools. No infrastructure change was attempted.
- New merge/deployment needs parent/user approval after reviewing this branch.
  Existing production and rollback remain untouched.
