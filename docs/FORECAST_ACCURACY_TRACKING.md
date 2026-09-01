# Forecast Accuracy Tracking

Status: automated private-alpha collection phase
Audience: Doug, product review, and operations

## Purpose

Polaris now begins building evidence about how well the weather forecast shown
for an imaging-window opening agrees with a later provider reading near that
hour. This is deliberately a collection phase. It does not change the
Opportunity Score, target ranking, or the Proceed / Use Caution / Do Not Image
decision.

## What is stored

For one observing home and one forecast hour, Polaris stores the latest
available forecast values for:

- temperature;
- cloud cover;
- humidity;
- dew point;
- sustained wind speed; and
- the existing provider name and timestamps.

When Polaris later receives a real provider reading within 75 minutes of that
forecast hour, it stores the equivalent observed values and marks the check as
matched. A single reading matches only the nearest eligible forecast hour.

The hosted private alpha runs the same planning and matching path at minute 17
of every hour. The collector processes only user UUIDs in the private
`POLARIS_FORECAST_ACCURACY_USER_IDS` Render environment allowlist. Each UUID
receives a separate tenant-scoped database session, so the existing forced Row
Level Security policy remains active throughout collection.

## Privacy boundary

Accuracy rows are owned by the signed-in user and protected by the same forced
PostgreSQL Row Level Security boundary as recommendations and observatories.
They do not contain latitude, longitude, postal code, target, telescope, email,
or account profile data. Polaris uses only the existing weather providers and
does not send this history to a new recipient.

The hosted tenant-isolation rehearsal explicitly verifies that another user,
and a request with no user identity, cannot read or change these rows before a
production migration is accepted.

## Missing data and honest limits

- No row is created without a real future forecast hour and at least one
  forecast value.
- A forecast is never treated as observed data.
- If both the scheduled collector and a user refresh miss the matching window,
  the pending check expires instead of being guessed.
- Repeated refreshes update one pending row for the same observing home and
  forecast hour rather than increasing the sample count.
- Times are converted from the observing home's named time zone to UTC before
  matching, including overnight and international date boundaries.
- History older than 90 days is deleted during normal tracking work.

## Operations

Render runs `python scripts/collect_forecast_accuracy.py` hourly. A successful
run prints aggregate tenant counts only; it does not print UUIDs, coordinates,
or weather values. Any configured-tenant failure makes the command exit with a
failure status so Render can surface it operationally.

Adding an alpha account to automated collection requires adding its UUID to
the cron service's comma-separated
`POLARIS_FORECAST_ACCURACY_USER_IDS` environment variable. Removing a UUID
stops future scheduled collection but does not alter existing history or the
90-day retention rule.

## User-facing state

Tonight shows a compact **Building forecast confidence** line inside the
existing weather summary. A matched-check count is visible, but Polaris does
not publish an accuracy percentage or confidence grade. Five matched checks
only establish that a future calibration review can begin; they do not prove a
confidence level.

## Future calibration gate

Before Polaris shows a confidence rating, product review must define and test:

1. which error measures matter for imaging decisions;
2. how cloud, humidity, wind, temperature, and provider changes are weighted;
3. the minimum sample size for each observing home and season; and
4. how stale or systematically missing observations affect the result.

Until then, the stored evidence is diagnostic only.
