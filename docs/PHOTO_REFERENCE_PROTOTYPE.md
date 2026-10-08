# Local photo-reference workspace

Integrated locally on `codex/sky-photo-integration`, based on sky-view commit
`5cab047`. The reviewed photo-reference prototype was copied from the separate
`codex/photo-reference-markers` worktree; that source worktree was not changed.
No commit, push or deployment is part of this integration.
No photo is supplied or stored in Git except a small generated synthetic PNG test
fixture. No account, database, migration, telescope-control or Tonight change.

## What works

Open **Local obstructions → Open local photo reference workspace** in either
editor placement. It opens a separate tab at
`/operator-assets/photo-reference.html`. The page can also run from the three
HTML/CSS/JS files together, with no backend. Click **Open photo workspace**, then
choose a local JPEG/PNG/WebP original (up to 25 MiB, decoded limit 100 megapixels).
HEIC requires a local conversion first; retain that exact converted file.

The first action is **Mark true north (0°)**. User clarification establishes true
north as the intended axis, but a qualitative landmark description is not an
exact pixel or angular offset. No marker is prepositioned. Tap the known landmark,
drag its numbered marker to adjust, and label it. An independent **Mark known
level (0° elevation)** action is available only as a user assertion of known level;
a roofline or image center is not presumed level. A general landmark has neither
known direction nor known height. Each point remains editable/removable. Keyboard
users can place a point at the image center then use arrows to move it, with Shift
for a larger image-relative step.

Closing the workspace dialog, including Escape, retains the in-tab draft;
reopening restores it. Loading identical image bytes retains references. A different
image clears them after a replacement confirmation when notes are unsaved. Reload
or tab close loses in-memory state; unsaved edits request the browser's normal
leave confirmation. BFCache restoration explicitly clears it. This standalone tab
is not account-bound: logging out in another tab does not erase this independent
local draft. Close or Clear here when finished.

**Export references (no image)** saves JSON containing labels, setup notes,
user-declared source type, image dimensions/hash, and normalized point coordinates.
It never embeds photo bytes, original filename, EXIF, user/site IDs or account
credentials. Keep the original image separately. Import requires the exact image's
SHA-256 and decoded dimensions before applying any points. A different crop,
conversion or re-encoding is a different image and must be marked again.

## Explicit geometry limits

There is no calibrated grid, angle interpolation, projection fit, horizon tracing,
obstruction-profile conversion or Tonight application. North supplies an azimuth
reference; level supplies an elevation reference. Neither supplies the other axis.
Even both together leave projection, angular scale, camera pose and unseen
coverage unknown. The format requires those unknown states and rejects purported
calibration. Coordinates are normalized displayed-image positions, not degrees.

No iPhone panorama is assumed to span 180 degrees, and 0.5x camera photos are not
mapped using uniform degrees per pixel. Hugin/PanoTools explains that spherical
scenes admit different planar projections; rectilinear and cylindrical mappings
have different geometry. See the [projection documentation](https://hugin.sourceforge.io/docs/manual/Projections.html).
The design consequence here is to preserve observations without inventing a
mapping. Browser decoding supplies displayed orientation/dimensions; EXIF,
intrinsics, lens correction, tilt and physical camera pose are not calibrated.
An AI illustration is not a calibration source; choosing Illustration keeps every
unknown state unchanged. A separately measured roof elevation can now be recorded as evidence, but the
photo itself does not measure or infer that angle. **Mark measured elevation**
requires an explicit finite value from −90° to 90° and measurement-source/aiming
notes. Each such marker carries `approximate: true`, `absolute_accuracy: unknown`,
and an explicit same-position/height confirmation (default false). Unconfirmed
setup makes the evidence conditional; confirming setup does not certify accuracy.
The value, source notes and setup confirmation remain editable. Invalid or blank
edits block export with an actionable error. Changing images clears unplaced
measurement entries so a reading is not silently reused on another image.

A measured-elevation point remains separate from the level-zero and true-north
markers. Even a measured value of zero does not automatically turn it into the
known-level marker. No sensor repeatability range is treated as absolute accuracy.
No private readings or landmarks are included in defaults or synthetic tests.
Draft export is now version 2, with strict measurement metadata; version 1 drafts
without measured-elevation markers remain importable.

## Privacy and implementation

No API calls, uploads, analytics, localStorage, IndexedDB or sessionStorage.
The standalone page has a restrictive meta CSP including `connect-src 'none'`.
Only user-selected local object URLs display photos. Replacement/Clear releases
object URLs; generation guards prevent stale decoding/imports from applying after
newer edits, image choices or resets. Only fixed HTML is inserted as markup;
reference labels and notes use text/value properties.

JSON import is limited to 256 KiB and 100 points, rejects duplicate keys, unsupported
versions/fields, invalid positions/IDs/hash types, and claimed calibration. Image
hashing uses browser Web Crypto; if unavailable, the UI asks for localhost/HTTPS
rather than weakening image identity. Resource limits do not establish smooth
performance for large panoramas on every phone.

## Verification and preview

Node/jsdom tests cover separate zero axes, empty and multi-reference insufficiency,
image identity, repeat loading, dismiss/reopen, editing/keyboard movement, clear,
BFCache, malicious/duplicate imports, rejected calibration, stale decodes/imports,
export without photo data large imported IDs, measured-angle bounds/types/provenance, approximate-status
invariants, editable measurement fields, image-replacement clearing and legacy
version-1 import. Image decode and dialog behavior
are mocked: these tests do not verify native browser decoding, touch dragging,
visual layout or actual dialog keyboard behavior. The synthetic PNG supplies real
bytes for hashing, not private imagery. FastAPI checks serve the standalone assets
and editor entry link.

Actual browser and physical iPhone testing remains required. The existing Chromium
runtime failed sandbox startup in earlier work; no sandbox bypass has been used.
To preview in the already working local environment, ask that chat to serve this
worktree using its existing Polaris startup, then open
`/operator-assets/photo-reference.html` on that app's URL. Alternatively unzip the
review bundle's `preview` directory and open `photo-reference.html`; if a browser
lacks Web Crypto in file mode, use the existing localhost server. Start with the
included synthetic image. Test original iPhone-photo decoding, true-north placement,
label/drag, close/reopen, export/Clear/import/reselect-original, and mobile scrolling.
Do not publish or apply a photo draft to Tonight as part of this preview.


## Integration with Sky view

Both **Sky view → Open local photo reference workspace** and the existing Local
obstructions editor open the same standalone page in a separate tab with
`rel="noopener"`. The photo page directs the user to switch back to the existing
Polaris tab, preserving both transient drafts. It also offers a link to open
Polaris in another tab if the original tab is no longer available. No opener
communication, URL-carried draft, embedding or automatic transfer is used.

This is deliberately two explicit workflows:

1. Record image landmarks and separately measured approximate elevations in the
   local photo workspace. Export reference JSON and retain the original image.
2. In Sky view, enter independently known direction/height coordinates or draw a
   clearly approximate skyline on the angular grid. Export skyline JSON separately.

Neither format is accepted by the other editor. In particular, a measured
photo-reference elevation has no inferred azimuth, and a north marker has no
inferred elevation or degrees-per-pixel scale. No photo outline, completed horizon,
overhead clearance or unknown-direction coverage is invented. Tonight is unchanged.

The supplied panorama could not be downloaded in this task. No private photo
pixels, readings or landmarks were available or added. All tests use the existing
synthetic fixture. The integration is discoverable and renderable through existing
Polaris asset serving; actual browser, image-decoding and physical-device validation
remain unperformed.
