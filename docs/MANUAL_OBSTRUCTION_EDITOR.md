# Manual obstruction editor and preview

Local feature based on the reviewed geometry prototype commit `d993387`.
No commit, push, deployment, migration, or live-data operation is part of this step.

## User workflow

Hosted users: **Edit home → Local obstructions** (beneath the observing-home form).
Local-mode users: **Locations → Local obstructions**. The expandable editor is
optional and does not change the user's observing home or Tonight's plan.

1. Enter measured direction/height pairs, clockwise from true north. Two blank
   heights initially represent unknown coverage, not zero-height obstructions.
2. Optionally add bounded-altitude roof sectors. A 350°→20° sector crosses north;
   sky below a roof remains potentially clear. Equal endpoints are ambiguous and
   rejected. All existing prototype constraints are preserved.
3. Select a vertical clearance (default 1°, allowed 0–10°). The 20° imaging floor
   remains independent. The margin is a design input, not proven sensor accuracy.
4. Explicitly confirm a complete horizon and overhead survey for the exact setup
   (or explicitly test the labeled synthetic example). Every geometry edit and
   import clears confirmation. Partial coverage cannot yield a clear preview.
5. Enter a target-center direction/height and select **Validate & preview**.
   Polaris validates the profile and checks this direction using the same
   `interval_exclusion_reason` used by obstruction-aware planning. The diagram
   shows the horizon, roof sectors, vertical margin, separate 20° floor, and point.
6. Export a JSON draft to retain it; import it later and reconfirm. An incomplete
   draft can be exported, with `complete_coverage: false`. Export/import never
   changes account settings. Destructive draft replacement asks before proceeding.

This is an actual-model geometry preview, not an astronomical target-track or
night planner. No real target, location, weather, capture history, or database
query is needed. It does not apply the draft to tonight, calculate darkness, or
claim that a full image frame is clear. Photographs, sensors, automatic panorama
calibration and telescope control remain outside scope.

## Reversible architecture

- `app/api/obstructions.py`: authenticated POST `/obstructions/preview`, mounted
  with the same authentication dependency as other APIs. No database dependency,
  account lookup, persistence, third-party geometry call, or logging of payloads.
  Normal application logs contain route/status/timing rather than profile values.
- Request body: `{profile: ObstructionProfile, probe: {azimuth_degrees,
  altitude_degrees}}`. The existing frozen profile validator is authoritative.
  Content type must be JSON; streaming body accumulation stops above 128 KiB.
  Extra fields, non-finite numbers, numeric strings/bools, duplicate JSON keys,
  partial coverage and out-of-range geometry are rejected. Validation errors omit
  submitted input values. Route success and route validation errors are no-store;
  auth failures remain governed by the existing auth middleware.
- Response contains only submitted geometry and its derived plot/probe result;
  no profile survives between requests. The north seam is explicitly included.
  Roofs are split at north for drawing; horizon clearance is interpolated before
  SVG clipping, so high/sloping horizons agree with backend tests near zenith.
- Frontend is a separate native-JS module and scoped CSS, initialized once from
  the existing boot function. It uses the existing authenticated fetch adapter.
  New assets participate in the existing asset-version calculation. No production
  frontend dependency is added. `jsdom` is a development-only DOM test dependency
  pinned in `package.json`/`package-lock.json`; use `npm ci` then `npm test`.
- Form rows use native labeled number inputs, fieldsets/legends, buttons, focus
  placement for added/deleted/blank fields and live status text. The mobile form
  uses two columns; the diagram scrolls horizontally to retain legible axes.
  That region is keyboard-focusable. No browser layout claim follows from these
  source and DOM checks.

## Draft lifecycle, import/export and privacy

All draft state lives in the current DOM, not localStorage, sessionStorage,
IndexedDB, cookies, a database or a URL. Reload starts blank; back-forward cache
restoration, sign-out and account identity changes clear both editor instances.
Pending requests are aborted and guarded by revision numbers: stale success/error
responses and slow imports cannot replace newer edits or reset data. Changing the
probe invalidates its preview without changing survey confirmation.

Exports have exactly `{format: "polaris-obstruction-profile", version: 1,
profile: {...}}`. No auth token, user/site ID, location or history is included.
Client import validates structure and numeric bounds, limits bytes/rows, rejects
unknown fields/versions and duplicate keys (including equivalent escaped names),
and only replaces a draft after the whole import succeeds. All imported values
are assigned as text/numeric values, never HTML. Importing a profile previously
marked complete still requires a new explicit confirmation. A downloaded file is
a user-retained copy; the app does not silently save or share it.

## Verification and limitations

Python tests exercise the authenticated route, strict body handling, north wrap,
clear/blocked directions, independent floor, request isolation, response caching,
error redaction, no DB/astronomy calls and parity of the synthetic UI fixture with
the real backend. Existing geometry/planner tests remain in the aggregate suite.
Node/jsdom tests exercise repeated imports/edits, exports, incomplete coverage,
malicious data, duplicate fields, revisions/aborts, account reset, errors, accessible
control structure and diagram regressions. A fresh independent reviewer reproduced
two defects (zenith clipping and duplicate import keys); both are fixed with tests.

A supported Chromium launch with its sandbox enabled was attempted once in this
cloud environment. It failed at sandbox startup. No unsafe flags or security
bypass were attempted. Thus live browser, visual layout, actual keyboard traversal,
screen reader and device testing remain unverified. A self-contained **static
HTML review preview** is generated from the actual editor DOM and synthetic backend
response. It can be opened in a browser, but is not a browser screenshot or proof
of tested layout. Its disabled controls intentionally do not pretend to be a live
planner. The source feature can be exercised with Polaris running normally.

Stored survey ownership, location binding, applying a profile to Tonight, phone
capture/calibration and continuous/full-frame clearance still need separate design
and verification. See [the geometry prototype](OBSTRUCTION_PROFILE_PROTOTYPE.md)
for the existing sampling, DST, completeness and accuracy limitations.
