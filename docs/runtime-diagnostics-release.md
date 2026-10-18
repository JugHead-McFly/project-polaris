# Proposed bounded runtime diagnostic release

Base production:6d43796ae6032d5361d28e092f0e76b014466594.
Branch:codex/runtime-diagnostics. This is instrumentation to locate latency,
not a performance fix. No deployment/publication or configuration change is
authorized or performed by this implementation task.

## Implemented scope

`POLARIS_RUNTIME_DIAGNOSTICS=true` opts in at process start. Default is off;
other values remain off. The first enabled request or art-worker start begins
a30-minute monotonic window. At most20 /tonight requests are sampled, at least
60seconds apart. A process restart resets this budget/window. No remote I/O,
cgroup reads, extra dependencies, timers, per-target logs or public endpoint.

Each sampled request emits one server-only `runtime_diagnostic` JSON record:

- Generated request ID, wall and process CPU for the request scope.
- Monotonic offsets for request/auth/route/planner entry, planner end, response
  headers ready (only when a response was constructed), and unconditional scope end.
- Planner wall, process CPU, worker CPU and returned flag.
- Boundary samples of active HTTP requests, active art workers and art-worker
  start count. These are sampled counts, not a high-water mark. Short overlaps
  between samples can be missed; art-start count helps identify intervening starts.

The actual art worker emits start/end records and its wall/process/thread CPU;
the returned flag distinguishes normal return from exception/cancellation.
Existing refresh behavior and errors are preserved. No tokens, user IDs,
coordinates, targets, request arguments, query/body content, raw paths or exception
text are added to these records. Existing application logs are unchanged.

New clock/snapshot/serialization/log failures are ignored without changing
application return values or exceptions. Counters and diagnostic context clean
up on cancellation and failures. Unsampled nested requests cannot mutate their
caller's diagnostic record. Context is propagated to ordinary worker execution.

When the capture window expires, new requests stop being counted. An already
sampled in-flight request may finish afterward; its late concurrency samples
then omit new arrivals. Do not infer concurrency after the capture deadline.
Process CPU includes all process threads; overlapping requests cannot each claim
it. Request wall includes scope cleanup/logging; headers-ready offset separately
identifies when the response was constructed, not network delivery to the client.
Auth/route offsets include dependencies and scheduling, not pure queue duration.

## Deliberate limit

This first diagnostic release implements the independent review's initial
phase/process/concurrency/background measurements. Optional cgroup counters are
deferred until the actual runtime mapping/access is verified. This code cannot
prove quota throttling or differentiate every lock/I/O/OS scheduling wait. It
must not label low worker CPU as hosting throttling. No access settings are changed.

## Verification

Regression coverage: sampling interval/count/expiry, disabled mode, failing
clocks/logger/snapshot, cancellation, failed authentication, background errors,
worker-side CPU placement, concurrent request counts, nested context isolation,
sensitive-string exclusion and unchanged complete synthetic plan response.
Existing request timing and full astronomical plan/cache regressions also pass.
There are42 distinct passing tests across these suites:41 passed before the
final nested-context guard; all20 focused diagnostics/timing tests passed after
that guard, including its new regression. Independent code review found no
remaining blocking defects. The reviewer's separate test execution stalled
before collection and its outside-sandbox retry remained unconfirmed at handoff;
it is not counted as a pass. This does not replace the completed author tests.
An overhead guard requires1000 forced sampled boundary cycles to finish under1s
on the test machine; it is a loose regression guard, not a hosted latency claim.

Matched synthetic full-POST benchmark uses fixed2026-10-18T18:24UTC,300 synthetic
sessions, real astronomy, fixed weather and in-memory SQLite. It forces every
request to sample, exceeding production's rate, with actual logging enabled.
Ten warm runs: disabled median0.382s; initial enabled median0.3645s. The enabled
run being lower reflects variation, not an instrumentation speedup. Final-run
enabled median was0.359s, retained in runtime-diag-overhead-final.txt. These measurements
show no obvious overhead regression in this local workload; they do not guarantee
server overhead or improved user latency. Astronomy harness warnings/limitations
from previous diagnostics remain applicable.

Evidence in workspace parent: runtime-diag-tests-final.txt,
runtime-diag-isolation-tests.txt, runtime-diag-overhead-off.txt,
runtime-diag-overhead-on.txt, runtime-diag-overhead-final.txt and independent
review test output. No live observations/database/provider credentials are used.

Reproduce tests with the repository Python environment:
`python -m pytest tests/test_runtime_diagnostics.py tests/test_request_timing.py tests/test_calculation_cache.py -q`.
Measure off/on separately:
`python scripts/benchmark_runtime_diagnostics.py .`
and `python scripts/benchmark_runtime_diagnostics.py . --enabled`.

## Minimal proposed capture/readout after separate approval

1. Publish the exact reviewed diagnostic commit via normal PR/rollback process
   and explicitly enable POLARIS_RUNTIME_DIAGNOSTICS=true for that process start.
   Deploying code alone leaves diagnostics off. Both actions require approval.
2. Within30minutes, use Polaris normally once (reload or Refresh). No stopwatch
   and no repeated trials. The first eligible /tonight request is sampled.
3. Obtain the `runtime_diagnostic` request record and existing `request_stage`
   lines sharing its generated request_id, plus art-worker start/end records
   in that interval. Current tools still lack Render runtime-log access, so a
   single filtered log export from Render is the minimal operator handoff.
   Do not share environment variables, tokens, or database credentials.
4. Compare auth/route offsets, planner wall vs worker/process CPU, background
   overlap and existing stage durations. Large process CPU with low planner CPU
   supports competing work; low process CPU requires targeted wait/runtime
   evidence before a cause is assigned. Do not sum nested stages.
5. Capture automatically stops after the window/budget. Remove the opt-in flag
   at the next approved configuration change to prevent recapture on future
   restarts. No repeated user stopwatch requests are necessary.

The result should determine the next investigation, not automatically trigger
an optimization, paid-tier change or deployment.
