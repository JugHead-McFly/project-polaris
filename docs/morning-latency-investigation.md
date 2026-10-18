# Morning latency investigation — 2026-10-18

Base and freshly verified production: 5bea916b84a88e35ef0f0addcd892ecdb97af038.
Isolated branch: codex/morning-latency-investigation. Application code unchanged.
No push, merge or deployment; no account/data/freshness/precision changes.

Doug reported a 24-second full load from an existing signed-in session at about
14:32 UTC. No matching server log has arrived in this execution thread yet.
This does not identify an authentication, cold-start or throttling cause, nor
establish a matched improvement over the preceding 31-second report.

## Evidence-backed candidates

1. Astroplan's next Moon rise and next Moon set both evaluate the same altitude
   grid. A local observer-scoped experiment reused only identical JD1/JD2 times,
   scale and arguments, retained the existing rise/set algorithms, and compared
   exact result JD components and masks. All seven cases passed, including
   Phoenix evening/morning, New York DST, Sydney, equator and polar cases.
   Warm baseline pairs took 0.083–0.095s; exact reuse took 0.044–0.050s, reducing
   two grid computations to one. This is a small part of a full request and
   does not eliminate downloads or explain the 24-second load on its own.

2. Fixed-target altitude transforms repeat a common night grid. A standalone
   matrix transform of 55 synthetic catalog targets × 41 identical instants
   matched every existing returned 0.1-degree altitude value, over three sites
   and three repetitions. Including fresh coordinate/time/frame construction,
   baseline took 0.225–0.236s; batching generally took 0.031–0.033s (one 0.057s
   run). This is a kernel experiment using the first 55 catalog entries, not
   Doug's exact selected targets or a full-plan benchmark. Per-target current
   instants and target-specific visibility-boundary refinements still require
   careful integration and may reduce the net benefit substantially. Moving
   and unknown targets must retain their existing paths. Do not simplify time
   sampling or freeze/reuse stale plans to obtain these gains.

Both probes use the project's pinned Astropy 6.0.1/Astroplan 0.10.1/NumPy 1.26.4
environment. They disable downloads only in isolated diagnostic processes;
the offline table emitted existing accuracy warnings. Comparisons use the same
table on both sides. They do not change or validate production reference-data
availability. Scripts contain assertions and are not imported by the app.

## Next decision from the pending production log

Correlate request_complete and all request_stage lines by request ID. Compare
moon/current/rise/set, altitude_compute count and wall/CPU, weather, catalog_load,
history, schedule and account-request durations. Inspect planning_runtime startup
status ready/deferred to determine whether preparation succeeded in that process.
Do not sum nested timings. A large wall/thread-CPU ratio alone cannot establish
throttling; native-worker CPU, waits and scheduling require separate evidence.

If altitude remains dominant, prototype common-grid integration and verify full
schedules across dates/timezones/equipment before considering release. If Moon
rise/set dominates, the narrowly scoped duplicate-grid candidate is preferable.
If delays lie elsewhere, target that measured stage. Both candidates still need
production implementation, independent review and full regression/benchmark
evidence. New deployment authorization must be checked; prior overnight approval
covered then-current work.

Evidence files beside the worktree: morning-moon-event-probe.txt and
morning-altitude-grid-probe.txt. Existing releases and rollback branches remain
untouched. The matching morning log is the only outstanding diagnostic input.
