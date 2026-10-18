# Per-filter history and forecast agreement review

Branch: `codex/filter-progress-forecast-agreement`, based on reviewed release
`17571d202dc5fe3dd5839cf384df410ee553d72f`. Nothing here is deployed.
The performance/dial release remains independently reviewable at that base.

## Per-filter progress

The library and target detail now expose recorded seconds and frames per filter.
Existing target goals remain shared; no extra filter goals or scheduler credit
are introduced. Accepted/rejected quantities are null, not zero. All imported
capture history is explicitly unassessed for quality. Catalog aliases resolve
to the same target for the target-detail breakdown. Account boundaries remain
the existing library query boundaries. There is no manual grading interface.

Verified importer behavior: the version-1 NAS manifest imports original raw
exposure counts and durations from archive proof records, excludes known failed
or stacked filenames, and deduplicates hashes. This is raw eligibility, not a
quality acceptance decision. It does not parse shotsInfo.json.

A read-only inspection of one archived M57 session's shotsInfo.json found:
DEC, RA, binning, exp, format, gain, ir, maxTemp, minTemp, shotsStacked,
shotsTaken, shotsToTake, target. This sample contains no per-frame acceptance
identities, rejection reasons, or quality metrics. Stack counts cannot establish
usable integration. This is a single-sample finding, not an exhaustive claim
about every firmware or archive session. No image pixels or bulk NAS images
were processed and no sync/import was run.

Automatic assessment remains incomplete. Existing analysis_service.py and
capture_analysis_service.py can measure stellar FWHM, roundness, sharpness,
signal, background uniformity and clipping. Their equipment starter profiles
and advisory quality scores do not constitute a validated raw-frame acceptance
policy. A defensible next step is a bounded representative raw-image evaluation
across filters, gain/exposure and calibration conditions, with explicit handling
of low-star/unsupported images, then a versioned decision policy linked to exact
frame identities and deduplicated durations. Any storage extension must follow
a verified recoverable backup. The first version intentionally does not turn
starter scores or stack counts into accepted hours.

## Forecast agreement

The compact expandable indicator compares cloud percentages from distinct
providers only when their location key and validity intervals match the same
elapsed hours of astronomical darkness. Partial hours are time weighted.
Mean spread <=15 percentage points is close, >15 and <30 mixed, and >=30 split.
These are descriptive product thresholds, not calibrated confidence levels.
The detail reports mean/max spread, providers, compared minutes, coverage and
the requested dark window. Coverage below 90% is explicitly partial.

Missing, single-source, stale-cache and incompatible data produce unavailable.
Duplicate providers do not count twice; conflicting duplicates and ambiguous
DST timestamps cannot create agreement. Overlapping comparison intervals are
rejected. Explicit offsets preserve repeated DST hours. Existing forecast-cache
freshness and NWS update-age validation remain in force. Provider differences
do not establish underlying model independence or clear-sky probability.
The existing blend, opportunity score and scheduler decisions are unchanged.

## Preservation, validation and preview

No database schema or production data changed; no migration is needed. Local
synthetic backup/restore tests passed, including tamper handling, tenant isolation
and capture-history replay. This is not a claim of a fresh production backup.

Targeted backend tests cover thresholds, missing/duplicate/incompatible sources,
partial windows, DST, history aliases, owner isolation, and unchanged goal credit.
Final validation passed 71 Python tests (including full-night schedule, API,
nightly forecast and backup/restore regressions) and 10 targeted Node tests.
Browser regression tests exercise agreement states, unknown quality, keyboard
expansion and widths 1440/768/390/320 with no page errors or horizontal overflow.
The in-memory preview is on http://127.0.0.1:8115/operator on Gamerig; it uses
synthetic observatory, weather, targets and history. Its deliberate visibility
gap demonstrates the timeline and is not a live-night prediction.

No push, merge or deployment has been performed. Develop auto-deploys; release
requires the parent's deployment coordination and explicit approval. Rollback
of these features is their base 17571d2; currently deployed code is 547feb0.
