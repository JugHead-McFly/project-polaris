# Hosted onboarding location entry

Status: implementation plan; build only if the first-time onboarding retest
shows that latitude/longitude still blocks completion.

## Problem to solve

Private-alpha testers need to give Polaris enough location context to calculate
weather, darkness, Moon position, target visibility, and timezone. They should
not need to understand astronomy coordinates before seeing their first Tonight
plan.

The current safest path is browser-assisted approximate location. If a tester
does not want to use browser location, manual latitude and longitude are still
available. Tester B's first failure suggests the manual path may be too much
friction for nontechnical users.

## Product rule

Make the easy path city/ZIP-style entry, but keep the stored planning data as
approximate coordinates plus timezone. Do not store a street address. Do not
send exact observing addresses to logs, monitoring, or support notes.

## Recommended first implementation

Use a small, reviewed lookup table for the private-alpha geography instead of a
general third-party geocoding service.

1. Add a server-side `POST /observatories/location-lookup` endpoint.
2. Accept a short text query such as a ZIP code or city/state.
3. Match only against an allowlisted local table or JSON fixture of common
   private-alpha regions.
4. Return rounded latitude, rounded longitude, timezone, and a display label.
5. Let the browser fill the existing observatory form from that result.
6. Save through the existing `/observatories` create/update endpoint.

This keeps the privacy and operational surface small: no new external lookup
provider, no browser-side API key, no street-address geocoding, and no new
database migration for the first pass.

## User experience

The setup screen should present the options in this order:

1. **Fill this in for me** using browser location.
2. **Enter city or ZIP** for an approximate lookup.
3. **Advanced: enter latitude and longitude manually.**

The manual coordinate fields should be collapsed or visually secondary once the
lookup path exists.

## Data boundary

The lookup response may include:

- display label, for example `Gilbert, AZ`;
- latitude rounded to about one or two decimals;
- longitude rounded to about one or two decimals;
- timezone name; and
- optional note such as `Approximate city center`.

It must not include or store:

- street address;
- unrounded device coordinates;
- full external geocoding payloads;
- user email or Auth identifier; or
- support/debug text that combines user identity with location.

## Acceptance checks

- A tester can complete setup without knowing what latitude and longitude are.
- The saved observatory still has valid latitude, longitude, timezone, and
  `coordinates_are_approximate=true`.
- Unknown locations fail with a plain message and leave manual entry available.
- Alice/Bob isolation remains unchanged.
- Local mode and existing observatory APIs continue to pass their current
  tests.

## When not to build it

Do not build city/ZIP lookup yet if the next retest shows that testers complete
setup using **Fill this in for me** and understand the handoff to Tonight. In
that case, the simpler browser-location path is enough for the first tiny
cohort.
