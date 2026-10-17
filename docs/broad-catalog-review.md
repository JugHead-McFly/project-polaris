# Broad catalog and full-night scheduling review

This supersedes the six-object-only expansion in seasonal-catalog.md. Work is
local on codex/long-dwell-cards; release/base rollback is
7cc8ff1ae1023691fdee290d4bd15d62ee5e6514. Nothing is merged or deployed.

## Corpus and provenance

12,036 searchable physical deep-sky entries: 12,035 parsed OpenNGC entries plus
the curated SIMBAD Pleiades entry (which has no NGC designation). 12,935 indexed
IDs/aliases. Existing public IDs remain unchanged. Ordinary stars, nonexistent
objects and duplicate records do not become separate deep-sky targets. Duplicate
designations resolve to their physical entry; ambiguous common names are not
silently resolved. Search supports IDs, aliases/common names and pagination.

Source: Mattia Verga and contributors, [OpenNGC](https://github.com/mattiaverga/OpenNGC),
revision `4e2398a263de663d83f7b86be80c368c34335764`, CC BY-SA 4.0. The original
CSV, full license and version/hash manifest ship under app/data/catalog.
SHA-256 `211ddbb3e319bb04b52b0cb7ca3b13862079a022dbe577f2367bd3846b0fa85f`.
Original per-field source codes are retained: NED, SIMBAD, HyperLEDA, HEASARC
and Corwin as defined by the [upstream guide](https://github.com/mattiaverga/OpenNGC/blob/master/NGC_guide.txt).
The derived data retains the upstream attribution/license. The separate curated
SIMBAD source is recorded on M45. See seasonal-catalog.md for its position/size.

The parser validates finite coordinates and angular measurements. Unknown
magnitudes/sizes remain null. With only a major axis, equipment fit uses a
clearly identified bounding circle, not an invented measured minor axis.
Catalog extent does not guarantee photographic framing or include every faint
outer structure. No catalog object gains a verified capture preset.

## Selection and performance

The full catalog is searchable through `/objects/catalog/search` and the
operator's Target & planning details search. The scheduler uses a separate
conservative automatic discovery path: known aperture, visual magnitude and
angular extent; V<=12 for apertures<=50mm or V<=14 for larger rigs; at least
eight native pixels across when scale is known; catalog surface brightness
<=24 when supplied. Complex groups and dark nebulae require individual review.
These are transparent starter discovery thresholds, not measured telescope
limiting magnitudes or image-quality guarantees. Search results show exclusions.
Existing curated targets retain their existing policy.

**There is no maximum-size exclusion.** Oversized targets remain eligible and
appear as Mosaic candidates. They cannot claim an executable panel sequence,
imaging integration, panel count or exposure recipe without configuration.

After completion/alias reconciliation, a vectorized whole-night altitude sieve
selects up to six promising objects in each 30-minute slot. This retains later
risers instead of using one evening shortlist. A 32-degree coarse gate allows
margin; detailed Astropy visibility independently enforces 35 degrees and the
actual date, timezone and location. Coarse sidereal time uses UTC as UT1 solely
for this generously margined sieve, without IERS network retrieval. The final
astronomy path retains the existing IERS behavior and precision warnings.

Measured Phoenix/Dwarf Mini discovery: 1,511 objects pass the initial physical
and known-data rules; 41 reach the time-stratified shortlist; cold local sieve
took 0.275 seconds including catalog load. Only shortlisted plus curated/history
objects get expensive detailed windows. The corpus is cached in-process and
hash-checked on first load; refreshes have no catalog network dependency.

This is a bounded practical search, not a global coverage optimizer. A remaining
gap means no evaluated target fits; it does not prove that all 12,036 objects
are impossible. The UI notes the discovery filters and further catalog review.
No invisible target, completed goal or forced fifth-target truncation is used to
hide a gap. Three to four is a tie-breaking preference, not a target quota.

## History and settings safety

No database migration, record rewrite, observation import or calibration edit.
New catalog entries keep the previous four-hour fallback goal and tier ratios.
Alias integration is combined read-only before shortlisting and scheduling.
Where legacy aliases have different goals, the lower existing goal is retained
so a catalog lookup cannot reopen completed work. Hosted and local history paths
both reconcile aliases. Explicit target lists remain scoped, including empty lists.
Verified local settings are retained; new catalog settings remain null with a
visible confirmation prompt. Manual mosaics do not displace usable single-frame
capture allocations and yield to later-rising single-frame targets.

## Realistic Phoenix evidence

Synthetic clear weather/history (M31 completed, other objects with zero credited
time), real October17–18,2026 Phoenix geometry, Dwarf Mini, Bortle8, 35-degree floor:

| Target | Local block | Stop |
|---|---|---|
| NGC7217 | 19:15–23:20 | Remaining four-hour goal plus setup |
| NGC1023 | 23:20–03:25 | Remaining four-hour goal plus setup |
| M1 | 03:25–05:12 | Dawn rounded inward |

597 allocated minutes including15 setup;0.802 minutes of boundary gaps.
Capture settings need confirmation. This is not Doug's private account replay.
The previous17-object catalog had only a C20 manual mosaic until00:26, then a
4h47 gap. Missing seasonal coverage and mosaic selection explained that result;
there was no universal three-hour cap.

## Validation, preview and release

Regression coverage includes pinned ingestion/hash, aliases, unknown data,
goal preservation, local/hosted history, explicit target scope, later risers,
oversized mosaic eligibility, performance, real Phoenix October/December/February,
setup, disjoint windows, polar nights, API/import isolation and rendering.
Final counts and artifacts are in the handoff. The earlier nine Node UI checks
remain relevant; the new preview also exercises catalog alias search.

Run `tests/serve_seasonal_fixture.py` with the test environment and in-memory
database settings documented in seasonal-catalog.md, then visit
http://127.0.0.1:8113/operator . It uses synthetic authentication/history and
real fixed-date geometry. Older8111/8112 fixtures are superseded.

Refresh procedure: review/pin an upstream commit, replace CSV/license, update
source.json revision, run `scripts/validate_catalog.py`, inspect changes and run
catalog/full-night regressions. Do not refresh automatically in production.

Local horizon obstructions still have no configured model in this release and
are explicitly disclosed. Live account state and real capture settings need
verification before execution. Merging develop auto-deploys on Render, so a
separate release approval is required after review.

Final verification:127 Python regressions and9 Node checks passed. Independent
review reran4 alias/scope regressions and found no remaining blocker.
Loopback preview returned HTTP200; catalog alias search and visible unset-settings
prompts worked; no JavaScript errors or desktop horizontal overflow.
