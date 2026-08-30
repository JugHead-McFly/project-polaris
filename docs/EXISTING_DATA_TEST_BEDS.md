# Existing-Data Test Beds

Last updated: 2026-08-30

## Decision

Project Polaris is in a Doug-first, single-user phase. Monsoon weather and the
availability of new captures must not control the development schedule. V1.11
and V1.12 use existing data and deterministic scenarios as their primary test
beds. New imaging and matched forecast observations are useful when they happen,
but they are not milestone gates.

## Approved test-bed sources

1. **Existing capture library**
   `/Users/doug/ProjectPolaris` is read-only source material unless Doug gives a
   separate explicit instruction. Tests may inspect existing FITS metadata and
   derived results without moving, renaming, rewriting, or deleting captures.
2. **Existing application database**
   The local Polaris database contains known targets, sessions, capture history,
   equipment context, and quality analyses. Back up before any test that would
   write to it; prefer a disposable copy or isolated test database.
3. **Existing hosted history**
   Saved recommendations, usefulness feedback, and forecast-accuracy rows may
   support privacy-safe review. Use the restricted application boundary for
   normal checks and keep tenant-isolation verification in every hosted schema
   change.
4. **Deterministic fixtures**
   Automated fixtures may model missing or rare conditions without claiming
   that synthetic values were observed. Keep them free of personal data and
   stable across test runs.
5. **Documented historical outcomes**
   Previously verified plans and known edge cases may become named regression
   scenarios when their inputs and expected decisions are clear enough to
   reproduce.

## Core scenario matrix

Maintain repeatable coverage for:

- clear, marginal, fully cloudy, and unavailable weather;
- bright Moon, low Moon interference, and target-specific Moon separation;
- Alt-Az and equatorial tracking;
- short and long usable windows, including the DWARF 999-frame limit;
- comfortable, tight, oversized, and very-small target framing;
- different observing time zones and dates crossing midnight;
- forecast checks that match, expire, deduplicate, and age out;
- targets with and without prior capture history;
- known deep-sky quality records and unsupported planetary/lunar scoring; and
- hosted tenant ownership, restricted runtime access, and cross-user denial.

## Implemented nightly-decision harness

The first V1.11 slice is available as:

```bash
.venv/bin/python scripts/nightly_test_bed_report.py
```

It runs five named scenarios through the real imaging-settings, night-decision,
schedule, night-rating, Opportunity Score, and operator-message logic:

1. the sanitized documented 50.2 monsoon hold;
2. a clear EQ nebula night using existing M57 history;
3. a long C20 session split at the DWARF 3 recorded 999-frame limit;
4. a bright-Moon broadband caution case; and
5. a weather-provider outage that must fail safely.

The same command opens `polaris.db` in SQLite read-only mode and reports only
aggregate evidence. The first verified run found 24 captures across 18 targets,
26 sessions, 42.94 integration hours, and 24 version-2 quality analyses. It
also identified one old capture-free session with an invalid placeholder date.
That row is harmless to the current dashboard, remains untouched, and is
tracked as later cleanup rather than a milestone blocker.

On 2026-08-30, all five scenarios and the complete 326-test suite passed.

## Truth and privacy rules

- Never label fixture data as a real observation.
- Never copy private coordinates, account identifiers, or raw captures into the
  Git repository.
- Use aliases or generated identifiers in committed fixtures.
- Keep raw captures and the live database outside destructive test paths.
- Do not weaken a privacy, security, or safety rule to make a scenario pass.
- Record why each test-bed expectation is trustworthy: measured history,
  documented product rule, provider contract, or deliberately synthetic edge
  case.

## Milestone use

V1.11 exits when the important nightly-decision scenarios are stable,
explainable, and covered by focused regression tests plus the full suite. V1.12
uses the same test beds to verify the joined Tonight, Portfolio, Goals, Quality,
and Locations experience. Neither milestone waits for clear skies, a new image,
an outside tester, or a minimum forecast sample count.
