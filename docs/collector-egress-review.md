# Collector database-read reduction

Baseline: `f67a9237f22d7cc9988030a2b6c65cf4b51250c6` (deployed weather/UI release).
Branch: `codex/collector-egress-reduction`. Local preparation only; release requires separate approval.

## Evidence and scope

Owner screenshots show organization egress 7.39 GB against 5 GB for September 25–October 25, with two projects sharing quota. October 14's tooltip shows Shared Pooler 630.173 MB and Auth 11.133 KB. This supports investigating database reads, but does not prove which query or project caused the full-cycle total. No production traffic savings are claimed.

The nightly collector previously fetched full records for all nights in its 14-day catch-up window, including completed observation JSON, then discarded completed nights in Python. Each per-sample commit also expired ORM attributes; the next sample's coordinate/window access reloaded that growing JSON. The patch selects pending night IDs in SQL, fetches each needed owned night individually, and retains immutable coordinates/window and the computed final summary locally across commits. The ORM still may issue narrow refresh queries during updates; global session expiration is unchanged.

The hourly satellite collector now excludes already-populated satellite references in SQL. Both SQL NULL and JSON null are included; unusable-but-collected evidence remains excluded from repeat collection exactly as before.

Only these two collector services change at runtime. No deletion, migration, frequency, retry, sampling-window, commit-boundary, UI, planner, NAS sync, weather-provider or authentication change. The current plan/reliability summary and NAS-sync optimizations are deferred.

## Isolated before/after measurements

Run `python scripts/benchmark_collector_egress.py` from this checkout. It reads original functions from the baseline Git object and runs both versions against separate in-memory SQLite databases with deterministic synthetic histories and mocked providers. No live credentials, database or provider calls are used. It counts SELECT executions, rows fetched, and UTF-8 JSON-serialized raw result rows. Byte counts exclude wire protocol and are **not Supabase billed egress**.

| Synthetic scenario | SELECTs before → after | Rows before → after | Byte proxy before → after |
|---|---:|---:|---:|
| Idle, no completed nights | 5 → 5 | 3 → 3 | 589 → 589 |
| Idle, 7 completed nights | 5 → 5 | 10 → 3 | 419,721 → 589 |
| Idle, 13 completed nights | 5 → 5 | 16 → 3 | 778,977 → 589 |
| Active, no completed nights | 27 → 28 | 27 → 28 | 156,756 → 9,763 |
| Active, 7 completed nights | 27 → 28 | 34 → 28 | 575,888 → 9,763 |
| Active, 13 completed nights | 27 → 28 | 40 → 28 | 935,144 → 9,763 |
| Satellite, no completed targets | 8 → 8 | 19 → 19 | 5,976 → 5,976 |
| Satellite, 100 completed targets | 8 → 8 | 219 → 19 | 153,176 → 5,976 |
| Satellite, 1,000 completed targets | 8 → 8 | 2,019 → 19 | 1,477,976 → 5,976 |

All nine comparisons assert identical reports, ordered provider calls and stored forecast/observation state, including an unrelated tenant. Active runs include missing scans. Satellite runs include SQL NULL/JSON null, provider failure, unusable quality, multiple revisions, and a target limit. Increased SELECT count in active nightly runs is an intentional tradeoff: one narrow ID query plus a demand-loaded record prevents transferring unrelated JSON. The benchmark is not a production latency measurement.

## Validation and limits

92 regression tests passed across nightly/satellite collection, reliability, forecast accuracy/collection, blending/agreement and weather. Independent reviewer passed 23 overlapping collector tests, checked tenant scope, retries and immutable context, and independently exercised JSON edge cases. No blockers found. SQLite execution verifies missing/false/true/null completion flags and SQL NULL/JSON null/reference objects/JSON string `null`. PostgreSQL SQL compilation checks passed; no live PostgreSQL execution was performed. Completion flags are the booleans written by the collector; malformed externally-written JSON is not newly supported.

Both SQL predicates may still scan database rows internally without new indexes. This patch reduces returned data, not guaranteed database CPU or latency. Real savings depend on each project's data, jobs and query volume. Two projects share the quota; their actual collector configuration and per-project usage still need verification.

## Proposed release

After explicit approval: recheck remote develop and exact diff, retain a rollback ref at the then-current deployed SHA, push/create PR, merge only this patch, and monitor both web and collector deployment status. Verify public health SHA. Inspect per-project daily Shared Pooler usage and collector completion/error reports after deployment; compare equivalent periods while accounting for usage/reporting delays. Existing consumed quota is not reduced retroactively. Roll back code if collection behavior changes; stored history needs no migration or restoration.
