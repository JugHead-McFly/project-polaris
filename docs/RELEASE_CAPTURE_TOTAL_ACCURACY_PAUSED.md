# Capture total and accuracy pause release

This code patch for Project Polaris 1.6.0 combines the total-capture-time display
with the forecast-accuracy pause. Exact Git and deployment SHAs identify the
released revision. Separate backup tools and capture-import work are excluded.

The targeting History line shows total integration from synced verified records,
without a date or frame fallback. Legacy stacks remain separate. No extra history
query is added. Normal weather, planning, capture evidence and recommendation
records remain active; accuracy entrypoints and the reliability panel are paused.

## Recovery and release checks

An existing tenant backup was verified and a code rollback was tested. Detailed
recovery evidence is retained separately. The tenant backup is not a current
full-platform backup. No new export, database restore, migration, import, pruning,
deletion or credential change is included in this release.

The local `scripts/release_check.py` requires a matched local SQLite/capture-library
pair and local smoke API. It is not a hosted-tenant release gate. For this code
patch, use the full backend and Node suites, synthetic browser checks, exact source
review and hosted deployment verification.

## Deployment and rollback

The web service and accuracy cron follow `develop` with deploy-on-commit. Publish
only the reviewed candidate after release approval. Explicitly merge the single
non-secret `POLARIS_FORECAST_ACCURACY_ENABLED=false` key into both service
configurations, preserving other settings and the existing compute plan. The
Blueprint agrees with this value. Do not issue an extra manual deploy after the
branch update.

Confirm both deploys use the published SHA. Verify web liveness/readiness, public
assets, paused cron output and ordinary weather/target/history behavior. Report
signed-in production verification separately from synthetic browser results.

A rollback must retain the complete accuracy pause and archive-preservation
guards. Older builds ignore the switch and resume accuracy collection and
90-day retention, so do not use an old-build rollback. Publish the tested rollback
source through a new `develop` commit if recovery is needed. No database restore
is part of a code rollback. Recheck both service SHAs, readiness and paused cron
output afterward.

## Local validation

Run from the repository root using a development Python environment with the
repository dependencies installed. Leave `POLARIS_ENVIRONMENT`,
`POLARIS_AUTH_MODE` and `POLARIS_DATABASE_URL` unset so the default-settings test
can exercise the actual defaults.

```text
python -m pytest -q --disable-warnings
node --test tests/*.test.cjs
git diff --check
```

The tested application code passed 646 backend tests and 20 Node tests.
Synthetic Chromium checks used the repository's dashboard/API fixture at four
widths (1440, 768, 390, 320), with six history states per width. They verified
total-only copy, unavailable/legacy/empty/zero states, target reset, hidden
accuracy, retained weather and schedule, and no page errors or horizontal
overflow. The harness opens the collapsed planning details.

The prepared code rollback passed 29 focused backend tests and all 17 applicable
Node tests. Application code, configuration and tests are byte-for-byte unchanged
by the documentation sanitization. These local checks do not establish a
successful production deployment or a signed-in production UI check.
