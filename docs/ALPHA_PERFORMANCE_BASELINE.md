# Project Polaris alpha performance baseline

Status: internal operator baseline  
Audience: Doug and Codex

This is not tester homework. Alpha testers should only report normal human
feedback: whether Polaris felt slow, broken, confusing, or trustworthy.

Use this baseline to separate expected free-Render cold starts from product
problems such as sign-in confusion, account-load failure, or slow Tonight plan
generation.

## What we measure internally

- `/health/live` response time.
- `/health/ready` response time.
- `/operator` public page response time.
- Whether hosted pages show retry or request-ID guidance when something fails.

Do not ask testers to time page loads, open developer tools, inspect network
requests, or record technical performance values.

## Run the public endpoint baseline

From the Polaris repo:

```bash
.venv/bin/python scripts/alpha_performance_baseline.py
```

The script is read-only and uses only public hosted endpoints. It does not sign
in, read private user data, save feedback, or call authenticated APIs.

## Manual notes during a tester session

If a tester mentions slowness, record only:

- what screen felt slow;
- whether it happened on first open or after refresh;
- whether the page eventually loaded;
- whether they saw **Try again**, `Plan unavailable`, or a request ID; and
- whether the delay made them distrust Polaris.

## Before-Nancy baseline

Captured on August 2, 2026 after the hosted service was already awake:

```text
/health/live
- Samples: 3
- Successful: 3/3
- Median: 307 ms
- Fastest: 283 ms
- Slowest: 376 ms

/health/ready
- Samples: 3
- Successful: 3/3
- Median: 280 ms
- Fastest: 242 ms
- Slowest: 280 ms

/operator
- Samples: 3
- Successful: 3/3
- Median: 277 ms
- Fastest: 242 ms
- Slowest: 291 ms
```

Interpretation: this is a warm-service public endpoint baseline, not a cold
start measurement and not an authenticated Tonight-plan timing.
