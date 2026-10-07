# Nightly forecast track record

The compact card shows separate afternoon and dusk sample counts. The historical
individual-time checks and graph remain under View history; they do not count as
nightly forecast evidence. No confidence probability or recommendation penalty is
derived from this pilot.

## Collection and evidence

The existing Render cron job checks every five minutes for the explicitly enabled
account IDs. It saves an immutable forecast in the ten minutes **before** six hours
ahead of astronomical dusk, and again in the ten minutes **before** dusk. Actual
capture time, lead time, provider fetch time, source mix and hourly source values
are retained. Fetches finishing late are marked missed, never relabeled. The
forecast must have been fetched within ten minutes. A missing interval is never
reconstructed later. These are prospective records; afternoon capture on the day
of deployment can already be missed.

The boundary is astronomical darkness (Sun below -18 degrees), determined for the
saved observing home. Hourly cloud values are clipped and weighted by their
duration in that exact interval. At least 90% forecast coverage is required.
Overlap is rejected rather than double counted. The original blended forecast
method and raw provider provenance are retained. No target selection or imaging
session is required.

After dawn plus 30 minutes, the job fills five-minute bins with GOES-18 ACMC
regional cloud estimates using the saved location and window. The existing 10 km
region, DQF=0, 90% pixel coverage and nearest scan within three minutes requirements
remain. Source hashes and scan provenance are stored for each sample. Duplicate
scans are not counted twice. Weighting uses each bin's duration, clipped at dawn.
This is sampled regional satellite cloud cover, not telescope-direction sky truth.

Each invocation processes up to 24 missing samples per account. Results commit
individually; interrupted batches resume. Network failures get three attempts,
then remain missing. Up to 14 days of incomplete observation windows can catch up.
A usable night requires at least 90% temporal coverage with no gap over 30 minutes.
Incomplete/poor-quality nights never become clear-sky zeros.

## Interpretation

Afternoon and dusk groups are separate. Each uses the latest saved source-mix,
method and coordinate cohort, rather than combining different forecast methods or
homes. Initial review begins at 30 comparable nights **per horizon**; this is a
review threshold, not statistical proof or a calibrated probability for tonight.
Records without sufficient observation coverage remain excluded.

The diagnostics report within-10-point counts and signed forecast-minus-satellite
bias. A provisional 20% nightly-average cloud threshold labels missed-clear nights
(forecast >20%, observed <=20%) and unexpectedly cloudy nights (forecast <=20%,
observed >20%). This threshold is disclosed in expanded history and is not a
go/no-go imaging rule. Local camera validation is still outstanding.

## Operations

Migration `20261006_0011` adds `nightly_forecasts`, with a composite observatory-owner
foreign key, unique home/date and forced tenant RLS. Original history is untouched.
Apply the migration before deploying the new API. Render's cron schedule must be
`*/5 * * * *`; the legacy point collector still runs once per hour at :15. Nightly
capture runs before that slower legacy planner. New accounts need addition to the
existing explicit `POLARIS_FORECAST_ACCURACY_USER_IDS` allowlist.

Tests cover immutable snapshots, late/missed fetches, clipped weighting, gaps and
duplicate scans, bounded retries/resumption, owner separation and source cohorts.
Full regression and migration checks are required before deploy. A production
two-owner RLS fixture can run transactionally and must be rolled back.
