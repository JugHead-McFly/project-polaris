# Forecast accuracy paused

Forecast accuracy collection and assessment are paused by default. Live weather
forecasts, provider blending/cache behavior, target planning, safety decisions,
capture totals and ordinary recommendation records remain active.

`POLARIS_FORECAST_ACCURACY_ENABLED` is the reversible switch. Its code default is
`false`; the web and cron Blueprint entries explicitly set `false` for release.
This is application behavior, not a database permission or hosting-plan change.

## Disabled behavior

- `scripts/collect_forecast_accuracy.py` exits successfully with
  `{"status": "paused", "collection_enabled": false}` before importing collection
  or database services, parsing tenant IDs, or contacting providers. The existing
  five-minute cron schedule can stay intact. It performs no nightly sampling,
  hourly tracking, satellite backfill, history scans, retention or writes.
- Hosted Tonight GET and POST skip accuracy summaries and tracking. In
  particular, POST does not execute the accuracy tracker's 90-day retention.
  POST still saves normal recommendation records. Responses carry an explicit
  `paused` accuracy state, not a measurement of the archived evidence; placeholder
  zero counts do not represent an archive inventory.
- The forecast reliability panel is hidden initially and remains hidden for
  the paused response. Regular forecast conditions and targeting stay visible.
- Existing accuracy and nightly evidence is left in place. Backup/export support
  and research service functions remain intact. There is no migration, cleanup,
  archive rewrite, import or data deletion in this change.

The switch guards deployed entrypoints. Direct calls to retained research
service functions still run those functions; it is not an access-control layer.

## Re-enable deliberately

Set `POLARIS_FORECAST_ACCURACY_ENABLED=true` for both the web service and collector
and restart/deploy those processes through the approved release path. Keep the
Blueprint consistent with that decision. A valid existing tenant allowlist and
provider configuration are still required. No credential rotation is needed.

Opt-in restores the previous collector and Tonight paths, including the
existing 90-day snapshot retention. It also restores the previous reliability
indicator; it does not create a calibrated confidence score. Missed prospective
forecast snapshots cannot be reconstructed, and nightly satellite catch-up is
limited to the existing 14-day window. Retain a verified recovery point before
opting back in if old evidence must survive the resumed retention policy.

## Candidate and rollback boundary

This work is prepared separately from total-only capture candidate
`23a03e9291a470fd6557f826bf5a659f639b38cf`. It builds on that candidate and does not
replace its branch. Deploying the combined retirement candidate includes both
the total-capture-time change and this pause. Reverting only the retirement
commit restores the total-only source candidate without rewriting the database.
Deploying that older source also restores its unconditional accuracy collection
and 90-day retention; it ignores the new switch. Review that consequence before
using it as a production rollback. If accuracy must stay paused during rollback,
retain the request/collector guards in the rollback candidate. Do not restore or
overwrite live data as part of an ordinary code rollback.

An existing tenant backup was verified and a code rollback was tested. Detailed
recovery evidence is retained separately. This code-only release includes no
database migration, restore, import, pruning or deletion.


Before publication, explicitly merge `POLARIS_FORECAST_ACCURACY_ENABLED=false`
into both service configurations so an existing override cannot resume accuracy
work. Preserve all other settings. Verify the effective pause through the new
cron's output and the tested Tonight guards. Rollback must retain those guards;
do not redeploy an older build that collects or applies 90-day retention.
