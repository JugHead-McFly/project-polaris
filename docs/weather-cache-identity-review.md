# Weather cache identity and initial reload investigation

## Matched production evidence
On 2026-10-18 after the 0.5 CPU upgrade, the retained browser request took 3.46 s: TTFB 3.45 s, download 8.67 ms, negligible queue/stall. It started 1.26 s after navigation. Server app time was 3.33 s, planner 3.11 s, weather 1.48 s, authentication 0.60 ms. Thus neither authentication nor asset download explains the dominant remaining request time in this capture. The browser/application difference is about 0.13 s, not a precise network-only measurement.

Primary weather 708.7 ms precedes enrichment; astronomy 764.6 ms overlaps NWS 494.5 ms. The structural critical path is approximately 708.7 + max(764.6,494.5) = 1473.3 ms, close to weather 1480 ms. Remaining planner time is about 1630 ms. Nested spans must not be summed. No matched CPU logs were supplied for this request, so these are elapsed times, not CPU attribution.

## Safe correction
The previous cache key rounded coordinates to two decimals and omitted timezone, despite providers/provenance using finer coordinates and astronomy payloads containing local times. Nearby locations or timezone edits could receive the wrong cached payload. Cached postal codes also belonged to the first caller. Negative cache ages could extend freshness after clock reversal.

The correction uses exact latitude/longitude and timezone, rebinds postal code on fresh/stale defensive copies, and rejects negative ages. Existing 20-minute freshness, six-hour stale fallback, timestamps, provider blending, request/retry behavior and authentication are unchanged. Public weather may still be shared for identical location/timezone; account data and complete plans are not cached here. Higher key specificity can increase cache misses after location edits, deliberately favoring correctness.

## What is not justified
Starting astronomy before primary success would theoretically reduce this trace to max(764.6,708.7+494.5)=1203.2 ms, only about 270 ms lower. It also issues unnecessary provider calls on failures/stale fallback and can introduce up to the six-second astronomy timeout into a fast failure path if workers are joined. No speculative requests were implemented.

Whole-plan reuse is not implemented: recommendations depend on authenticated account, observatory coordinates/timezone/horizon, current date/time and setup window, equipment/EQ settings, integration history/goals, weather freshness, and algorithm/catalog version. Existing persisted recommendation records are summaries/provenance, not a complete versioned reusable response. Browser state resets on reload. A cache keyed merely by user/date or location/date would be unsafe; stale targets or integration progress are unacceptable.

The existing process-local weather cache already avoids provider requests for repeated calls within 20 minutes. Deployment/restart clears it; expiry and location changes miss it. The matched 1.48-second weather trace is a provider-fetching request. A later two-second refresh is consistent with warm weather reuse, but its exact cache state is unverified without matched logs. Reload itself does not inherently clear the server cache.

## Validation and measured limits
31 focused weather/cache/provider tests passed; independent reviewer reran the same 31 and found no blockers. New tests cover formerly colliding locations, timezone isolation, fresh/stale postal rebinding, defensive copies, TTL/stale boundaries crossing midnight, and future timestamps. Existing tests cover fallback, retries/rate limits and provider timeout/overlap.

Synthetic local comparison uses isolated provider sleeps matching the trace, three cold/warm pairs per version, no external requests or database. Baseline median cold 1.475306 s / warm 0.0293 ms; corrected median cold 1.474801 s / warm 0.0233 ms. The approximately 0.5 ms cold difference is noise, not a measured speedup. The existing warm cache avoids simulated provider delay in both versions. This patch is a correctness fix with no claimed production latency benefit.

## Release status
Feature branch codex/weather-startup-overlap, base d49496572a35d04dc6eee94261b667dae37d630b. Local only: no push, merge or deployment authorized. The production $7 plan alignment is preserved. No live observations, database, credentials, security settings or diagnostics flag were changed. Independent review: no blockers. Any future release needs review of the final scope and explicit merge/deployment approval.

Additional forecast blending/agreement/accuracy regressions: 32 passed. Total distinct author-run tests: 63; independent 31 are overlapping validation, not additional unique tests.
