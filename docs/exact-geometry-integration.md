# Exact refinement and Moon-separation integration

Branch codex/deeper-latency; base reviewed PR9 commit d783e4bd0cb0b5fe37a6e2e11a0588e7b00544aa.
This integration is separate from PR9 and has no deployment approval.

Repeated per-target coordinate transforms dominate the measured astronomy work.
The implementation batches the exact threshold-refinement instants and midpoint
Moon separations, leaving current-time samples, moving targets and policy decisions
on their existing paths. The scalar path and optimization now share one refinement
generator, preserving DST/UTC stepping and disjoint crossings.

The explicit API accepts coarse_times, midpoint, minimum_altitude and observatory.
It uses at most 64 coordinates per target chunk and 512 coordinate/time pairs per
transform; pair lists are flushed incrementally. Coarse grids above 4096 samples
skip optimization. Empty/unknown/moving/invalid targets, nonfinite samples and
ValueError optimization failures retain the original calculation path. Only finite
results seed the existing request-local exact cache. No cross-request state,
reference-table policy, clock rounding, goals, history, equipment or schema change.

## Evidence

Four complete 55-candidate plans and schedules exactly match both the pre-PR9
baseline and PR9 behavior: Phoenix October/December, New York DST and Sydney.
Independent evaluation against the original HEAD visibility implementation also
matched 249 complete visibility dictionaries and 249 Moon separations across
83 targets and three locations. Tests cover 65-target/512-pair boundaries, empty
and oversized grids, invalid and nonfinite input/output, original fallback, moving
and unknown targets, disjoint threshold intervals and concurrent observatories.

Normal application benchmark (no prototype monkeypatch), 300 synthetic sessions,
memory SQLite, fixed weather and clock, real astronomy after startup preparation:

| Request | Reviewed PR9 baseline | Integrated details |
| --- | ---: | ---: |
| First prepared request | 1.025s | 0.866s |
| Warm 1 | 0.635s | 0.490s |
| Warm 2 | 0.643s | 0.485s |

Approximately 24% additional local warm improvement. The new geometry-details
stage takes 66-68ms and remaining altitude compute takes 109-111ms. Targets and
gaps are unchanged. These figures exclude provider/network delays and cold Render
wake; they do not establish a production five-second target. Offline comparison
uses the same IERS table and retains the existing warning limitations.

Reproduce: python scripts/benchmark_exact_geometry.py .
This harness now measures the application directly. The earlier probe script is
historical research and should not be installed over this integrated code.

Evidence beside worktree: details-integrated-benchmark.txt, details-final-tests.txt,
independent-details-tests.txt, independent-integrated-details.txt.

## Remaining operational gate

PR9 was published with remote rollback codex/rollback-before-common-grid at
5bea916b84a88e35ef0f0addcd892ecdb97af038. Automatic approval review denied both
merge attempts: it requires explicit user authorization to merge PR9 into develop
and trigger Render production deployment. Neither command executed. The parent
handles obtaining that confirmation. This newer integration requires separate
release approval; no push, merge or deployment has been attempted for it.

Final validation:125 regression tests passed. Independent review passed75 distinct tests and found no blocking issues; final guard evidence is ../independent-details-output-tests.txt.
