# Moon initialization and production latency

Base: live 30c5dc9102a306f477808ff7db5118012a60116c.
Isolated branch: codex/moon-latency-diagnostics. No database/schema changes.

## Evidence

Doug reported approximately31 seconds for a signed-in load. The supplied Render
log identifies POST /tonight request bcad202cfd52 at 2026-10-18T03:24:41UTC:
33.1459 seconds server elapsed, planner29.2889, weather3.4279 and computation25.8602.
Moon took14.166 seconds wall/1.033 thread CPU. Altitude actual computation took
5.7511 seconds/0.9595 CPU over100 evaluations (210 public calls); the earlier
release had about11.84 seconds altitude-series wall. Transit batch was1.0051
seconds/0.1546 CPU. Catalog loading1.8217/0.2789 and darkness0.7902/0.0986 also
showed large wall/CPU differences. Nested stages are not additive.

The log shows catalog initialization on this request. It does not contain
IERS download timings or establish that CPU throttling occurred. Thread CPU
does not include other/native threads. Health requests during planning took
roughly10–504ms versus7–14ms afterward; this is compatible with resource
contention but does not prove its cause. The checked-in Render blueprint uses
a free service; deployed service capacity was not independently inspected.

A fresh-process, isolated-cache reproduction with the same normal Astropy
download policy found a concrete blocking path: first Moon computation10.5472s,
including successful public IERS downloads9.4355s and0.6693s, with0.5s process
CPU. Subsequent Moon calls0.1119/0.1110s made no additional downloads. An offline
test took0.2983s cold and0.1098/0.1088s warm, but emitted IERS accuracy warnings;
offline operation is only a diagnostic fixture and is NOT the production fix.

This confirms lazy IERS initialization can dominate the first Moon call. It
does not establish that every second of the production14.166s had that cause.
No cold-start/throttling assumption is needed for the implemented change.

## Change and limits

Production lifespan now awaits normal astronomy reference-data initialization
and catalog integrity checking before yielding readiness. It calls the existing
Moon-current calculation at a synthetic reference location with the actual
current time, warming the standard process reference tables. No user plan,
account history, forecast or geometry result is cached across requests. IERS
auto-download/freshness/precision settings and ordinary refresh behavior are
unchanged. No network restriction, offline fallback or reduced sampling was
introduced. Tests and development skip preparation.

Transient initialization exceptions are logged by class only and deferred to
the existing request path; catalog preparation is attempted independently.
Cancellation is not swallowed. Startup logs separately report wall, thread and
process CPU for reference preparation. Request logs now split Moon-current,
rise and set; moon_current can include other planner calls and is not necessarily
wholly nested within the top-level moon stage.

Fresh-cache prepared test: astronomy initialization8.3827s plus catalog0.1363s
at startup; first Moon call0.1510s, warm0.1037/0.1070s. Outputs exactly matched
the unprepared fixture. Download duration varies between runs; this is movement
of initialization cost before readiness, not proof of reduced total boot work.
A cold free-service wake may still leave a browser waiting for startup. Local
timings do not establish production load speed. No paid upgrade was made.

Reproduce from repository root with memory/test environment:
`python scripts/benchmark_moon_initialization.py network`
and in a fresh process:
`python scripts/benchmark_moon_initialization.py network-prepared`.
Each uses a fresh temporary Astropy cache and prints startup separately from
three fixed-time synthetic Moon calls. `offline` is a diagnostic-only variant.

## Validation and release

Tests cover readiness waiting, test/development bypass, transient failure and
retry, unchanged IERS settings, exact Moon outputs at six sites/dates including
DST and polar no-rise/set cases, plus existing scheduler/account/history checks.
Independent review additionally checked cancellation and isolated catalog
failure. Two preexisting local-library preflight tests were made explicit about
their local-library requirement to avoid order-dependent imported environment
defaults; application preflight behavior is unchanged.

Before publishing, retain remotely reachable rollback30c5dc9 and verify merged
tree and Render live/ready health. The operator has authorized these in-progress
fixes with rollback. Actual signed-in production performance remains unmeasured
until fresh telemetry is available; do not substitute repeated user reloads for
diagnosis. No observation, calibration, backup, NAS or production database data
is modified by this change.
