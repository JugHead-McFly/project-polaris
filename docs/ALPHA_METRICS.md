# Private-alpha health report

Polaris now has a small, read-only operational report for the private alpha.
It answers whether invited people are getting through the core loop without
turning our support process into surveillance.

## What it reports

- profiles created;
- accounts with an observing home;
- accounts with at least one saved nightly plan;
- accounts that returned to plan two or more different nights;
- activation rates for observing-home setup, first saved plan, and second-night
  return;
- total saved plans, grouped only by recommendation outcome; and
- total Yes/No feedback and response rate; and
- one aggregate review focus, such as onboarding completion, first-plan
  reliability, recommendation trust, second-night return, or careful expansion.

It never prints names, email addresses, user IDs, observatory names,
coordinates, target names, or written feedback.

## Run it

From the Polaris project folder:

```bash
python scripts/alpha_metrics_report.py --env-file .env.staging
```

That prints a plain-English review summary. For the raw aggregate JSON, use:

```bash
python scripts/alpha_metrics_report.py --env-file .env.staging --json
```

When deliberately reading the production database, use the explicit guard:

```bash
python scripts/alpha_metrics_report.py --env-file .env.production --confirm-production-read
```

The report is read-only. It does not alter accounts, recommendations, or
feedback. Run it once per weekly alpha review, then use the totals and review
focus alongside the qualitative notes in `ALPHA_TESTER_FLIGHT_LOG.md`.
