# Local sky view prototype

Branch `codex/local-sky-view`, based on saved-spots commit `9313fc5`. Uncommitted reviewable changes only; no migration, deployment, or changes to Tonight planning.

Open Locations or Edit home → **Sky view**. Choose Use observing home or explicitly enter latitude, east longitude, elevation, IANA display timezone and UTC instant. Pick up to twelve existing catalog targets and Calculate sky. Hour buttons recalculate; Now sets the input and requires Calculate. The authenticated read-only API uses the existing Polaris astronomy service and tenant-scoped home lookup. Coordinates are not written to settings. Signing out, account changes and browser history restoration reset the view.

The horizontally scrollable SVG uses linear true-north clockwise azimuth 0–360° and geometric altitude 0–90°, with a 10° grid. These are angular diagram axes, not a panorama projection. Target centers below zero remain in the result list but are not drawn. Missing calculations remain unavailable. True north occurs at both ends. Changing latitude, longitude or elevation clears the display skyline.

## Landscape honesty

The initial landscape is unknown. Load synthetic demo explicitly loads a fictional partial outline and an equatorial example location; all target calculations still use the real astronomy service. Sketching requires at least two points in a finished segment. Separate segments preserve unknown gaps; no extrapolation or joining across gaps occurs. Import/export uses bounded `polaris-skyline` version 1 JSON with ascending azimuth/altitude points, source and notes. Source claims are user declarations, not verified accuracy. North seam and shared endpoint heights must agree. A hand sketch does not become measured because it looks plausible.

Black polygons cover zero elevation up to the supplied skyline. Overhead roofs and bounded altitude sectors are **not modeled in this display**; above a skyline is explicitly not a clearance claim. This format is separate from the scheduling obstruction profile and does not enable or change a saved spot or Tonight. It checks target centers at a single instant, not frame extent, safety limits, continuous tracks or scheduling samples. No automatic photographic calibration, heading sensor, pixel-to-angle conversion, 3D view, or image upload is implemented. Opposite phone panorama sweeps do not establish calibrated 180° image spans. A single measured roof peak cannot define a surrounding silhouette.

The supplied north/south panorama Library files could not be materialized in this executor: both authorized helper attempts returned `library file transfer failed: download failed`. No image bytes were inspected or used, no personal silhouette is included, and no transfer URLs or private photographs are bundled.

## Accuracy and validation

Positions reuse Polaris/Astropy geometric calculations without atmospheric refraction. Available Earth-orientation data may limit precision. The offline preview generator specifically emitted a stale-IERS warning and assumed UT1−UTC = 0; its positions should not be treated as instrument calibration. UI numeric rounding is not an accuracy guarantee. API dates are bounded to UTC years 2000–2100 with explicit offsets; the UI uses UTC input to avoid ambiguous daylight-saving local times and displays the corresponding local instant.

Automated tests cover real calculation reuse and changes with location/time, UTC-offset equivalence and DST repeated hours, invalid inputs/extreme date offsets, authentication and two-account home isolation, below-horizon/unavailable positions, north/shared-boundary consistency, exact grid spacing, partial coverage, repeated opening, stale responses/imports, and account reset. Full suites: 517 Python tests and 35 JavaScript tests. No native browser, iPhone, touch or screenshot verification is claimed; the managed browser environment was unavailable and Chromium sandbox failure was not bypassed.

## Offline review artifact

The accompanying ZIP includes complete source changes, a patch against the base commit, validation logs, and `preview/index.html`. Extract the ZIP and open that file in a desktop browser. Its controls select three fictional sites and nine hourly snapshots on 8 October 2026, generated with the real backend calculation for M31, M57, M13 and Jupiter. It makes no network requests. The application feature supports arbitrary validated inputs; the offline preview deliberately supports only its precomputed choices. Physical-phone file viewing remains unverified.
