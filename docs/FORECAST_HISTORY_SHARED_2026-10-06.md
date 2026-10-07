# Shared forecast history — October 6, 2026

Production audit found 414 revisions across 40 target times for the operator's
AZ Home, including 402 legacy model-matched revisions and no satellite references.
The history had not disappeared: the new satellite-only chart displayed zero
because the production collector did not retrieve satellite observations.

History remains keyed by authenticated user and observing-home ID in PostgreSQL,
with tenant RLS unchanged. It is never keyed by browser or device. The summary now
shows saved target times, pending references and future forecasts separately from
usable satellite comparisons. Forecast revisions do not inflate the check count.
Loading a new plan displays a loading state rather than a false zero-history count.

The existing hourly Render collector now attaches NOAA GOES-18 ACMC references to
past forecasts, including a bounded historical catch-up (48 target times per
account per run, within the existing 90-day retention). It preserves forecast
values and model-match status. Satellite checks no longer require an unrelated
model observation to have matched successfully. Download failures retry later;
bad-quality satellite results remain evidence but are excluded from scoring.

The extraction retains the prior pilot's 10 km regional estimate, DQF=0 requirement,
90% pixel coverage threshold and three-minute maximum midpoint offset. It checks
valid cloud classifications and masks, records SHA-256/source/time/location
provenance, bounds downloads to 32 MiB and projects the grid in memory-bounded row
strips. No satellite downloads run in the interactive plan request.

Validation: Python regression suite passed; all 11 archived pilot scans reproduced
their previous cloud estimates and quality fractions. A recent October 6 UTC scan
was retrieved successfully at the exact production home coordinates. Tests cover
repeat-run idempotence, owner isolation, separate request sessions, expired model
matches, future/post-target exclusions, failed retrieval retries, quality rejection
and scan timing across midnight. JavaScript syntax and git whitespace checks pass.

These remain comparisons at saved target times, **not whole-night averages** and
not a calibrated confidence percentage for tonight. The collection job currently
uses the existing explicit account allowlist and primary observing home. All
devices must use the same hosted deployment and account; development and production
databases remain intentionally separate. No older database was copied or merged.

Sources:
- https://registry.opendata.aws/noaa-goes/
- https://www.star.nesdis.noaa.gov/atmospheric-composition-training/satellite_data_goes_imager_projection.php
- `CLOUD_OBSERVATION_PILOT_2026-09-12.md`
