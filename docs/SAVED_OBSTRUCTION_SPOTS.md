# Saved setup spots and explicit Tonight selection

Reviewable local feature on `codex/saved-obstruction-spots`, based on editor
commit `e63e8c6`. No live migration, commit, push or deployment has been performed.
The three prior integration-validation changes remain separately in the original
`/workspace/project-polaris` checkout; this worktree does not publish them.

## Workflow

Hosted **Edit home → Local obstructions → Saved setup spots** lets the user name,
load, save and delete complete reviewed surveys. Saving never enables a survey.
An existing spot must be loaded before it can be edited/replaced. Saving requires
both the editor's complete-coverage confirmation and a separate review of the exact
scope position/height, with an explicit source declaration. Incomplete drafts can
still be exported using the editor; they cannot be saved as planning-ready spots.

**Local obstructions for Tonight** defaults to Off. Select a named reviewed spot,
then Refresh plan. The choice lasts only in this signed-in page, never localStorage
or the account. Reload/logout/account changes/BFCache reset selection to Off. A
selected spot that changes, is deleted, or becomes invalid stays explicitly
unavailable until the user re-selects its reviewed revision or chooses Off.
Saving/loading never silently updates the active revision. Selection changes and
saved-list reloads invalidate visible/in-flight plans. Background condition checks
use the same selection and reject responses from older accounts/selections.

Only the hosted primary observing home is used by Tonight. Other homes' spots
cannot be applied. This stage deliberately does not add a multi-home switcher or
local-mode persistence; local preview/export behavior remains available.

## Storage and isolation

One additive `obstruction_spots` table stores owner, parent observing home, name,
immutable schema version, revision, geometry JSON, source quality, review/update
timestamps and a home-geometry binding. Composite owner foreign key cascades
on home deletion. PostgreSQL migration enables and forces RLS with owner checks,
revokes public/anon/authenticated access, and grants the existing app role access.
No role, credential, or other security configuration is changed.

The bounded JSON reader accepts at most 128 KiB and rejects duplicate/nonfinite
JSON, extra fields and invalid geometry without echoing submitted input. CRUD
uses authenticated tenant sessions and filters both owner and home. Updates and
deletes use atomic revision comparisons. Supported PostgreSQL saves/deletes lock
the parent row, serializing the 32-spot cap and concurrent home changes. Home edits
that change coordinates, elevation, timezone or rig invalidate all its survey
bindings and increment revisions in the same transaction. Reverting coordinates
does not restore confirmation. A fresh save after explicit review is required.
Direct unsupported database edits are not an authorized data workflow.

SQLite does not enforce `FOR UPDATE`. Separate SQL checks ran on a disposable
PostgreSQL 16 Docker container with no network or published ports. The complete
generated migration executed; forced RLS blocked cross-owner reads/updates/deletes
and inserts, ownership FK rejected a mismatched home, anon access was denied, and
two concurrent parent-lock/revision updates produced exactly one successful writer.
Home deletion cascaded correctly. The container and its data volume were removed.
This verifies actual database enforcement and concurrent SQL operations; it does
not establish deployment-specific role configuration or full HTTP-service load
behavior on PostgreSQL. No existing database or credentials were touched.

## Planning and provenance

`GET/POST /tonight` add optional `obstruction_spot_id` and
`obstruction_revision` query parameters. Omit both for Off; providing only one
fails validation. The server checks ownership, primary home, exact revision,
source, home binding and geometry before constructing an immutable request
snapshot. An invalid selection yields a clear error before planning, never an
unobstructed fallback. A request uses its validated snapshot; later edits do not
retroactively change an already generated plan. Refresh after environmental changes.

Tonight returns applied/off provenance. Hosted recommendation history retains
spot ID/name/revision/source/review timestamp and the full geometry snapshot in
existing JSON provenance, so later edits/deletion cannot rewrite the evidence for
an earlier plan. Spot and Tonight responses use no-store. No image, precise spot
GPS, camera access, telescope control or payload logging is introduced.

Source quality currently accepts `manual_measured` (user-declared, not verified
accuracy) or `synthetic` (testing only, never accepted by Tonight). Storage reserves
`photo_estimate`, but the write API rejects it and no extractor/upload exists.
Future photo estimates need explicit pose/projection assumptions, observed and
unknown coverage, review/correction state and uncertainty treatment; review alone
must not certify angular accuracy. Four iPhone cardinal photos are not currently
converted into a calibrated map. A future metadata/schema extension must preserve
that distinction rather than relabel estimates as measured.

Existing obstruction planning retains the independent 20° floor, one-minute UTC
samples and conservative angular checks, longest contiguous clear window, blocked
interval reasons and DST safeguards. The scheduler never joins disjoint clear
windows. This remains advisory target-center clearance, not continuous visibility
or full-frame clearance. See `OBSTRUCTION_PROFILE_PROTOTYPE.md` for exact limits.

## Verification and remaining work

Synthetic API tests exercise owner/home isolation, CAS save/delete, home-change
invalidation/reconfirmation, invalid/synthetic/stale/unknown rejection, request
limits, independent provenance snapshots and attachment to the actual planner
context. The existing geometry/scheduler suite checks blocked gaps and boundaries.
Migration tests build a fresh SQLite database, check model parity, downgrade and
reapply. The disposable PostgreSQL rehearsal executes the generated migration and
checks RLS, ownership and concurrent revision updates. DOM tests use actual shipped HTML
and scripts with synthetic auth/network: explicit selection, Off default,
revisions, logout/late response handling and full-page Tonight request/error flow.
Independent review reproduced and then rechecked fixes for two asynchronous UI
races (stale plans after reload and late saves switching edit destination).

No actual browser rendering, native keyboard traversal, screen reader or physical
phone check is established by jsdom. The previously attempted installed Chromium
sandbox could not start; no bypass has been attempted. Full-app desktop and
physical iPhone Safari checks remain release blockers. Deployment-role and
full-service concurrency checks remain staging validation. Photo-assisted input remains a separately scoped follow-up.
