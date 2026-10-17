# Recommendation quality review

Local branch: `codex/long-dwell-cards`. Release/rollback base:
`7cc8ff1ae1023691fdee290d4bd15d62ee5e6514`. Nothing merged or deployed.
This review supersedes the example rankings in broad-catalog-review.md.

## Confirmed defect

The final planner discarded magnitude, angular footprint and surface brightness
after catalog discovery. Its remaining score combined capture confidence,
portfolio priority, maximum/average altitude, usable dark time and Moon conditions.
Thus observable compact galaxies could outrank easier large, bright targets for
the Dwarf Mini. The four-hour fallback goal did not add a ranking bonus; it made
each selected new target occupy four hours once selected. Unknown metadata did
not explain the two galaxies: both have measured dimensions and brightness.

Detectability alone is not a beginner imaging recommendation. Neither galaxy is
declared impossible; the defect was insufficient comparative suitability scoring.

## Evidence and alternatives

The stored Dwarf Mini profile is 30 mm aperture, 150 mm focal length and 2.9 um
native pixels (approximately 3.988 arcsec/pixel, 2.13 by 1.20 degree field).
Footprints below describe native sampling, not optical resolution or predicted SNR.
Catalog B-band mean surface brightness is measured within the B=25 isophote;
it is not directly interchangeable with an invented Bortle sky magnitude.

| Object | Catalog extent, arcmin | V magnitude | Mean B surface brightness | Native long x short axis pixels |
|---|---|---|---|---|
| NGC7217 | 4.52 x 3.84 | 10.47 | 22.93 | 68 x 58 |
| NGC1023 | 7.40 x 3.06 | 9.47 | 22.59 | 111 x 46 |
| M33 | 62.09 x 36.73 | 5.79 | 23.61 | 934 x 553 |
| M42 | 90 x 60 | 4 | Unknown | 1354 x 903 |
| M45 | 76.86 x 76.86 | Unknown in imported record | Unknown | 1156 x 1156 |
| M1 | 8 x 4 | 8.4 | Unknown | 120 x 60 |
| M78 | 4.5 x unknown | 8 | Unknown | 68 x unknown |
| NGC281 | 35 x 30 | Unknown | Unknown | 527 x 451 |
| M39 / NGC7092 | 19.5 x unknown | 4.6 | Unknown | 293 x unknown |
| M34 / NGC1039 | 22.5 x unknown | 5.2 | Unknown | 339 x unknown |
| M37 / NGC2099 | 11.4 x unknown | 5.6 | Unknown | 172 x unknown |

OpenNGC supplies these values except curated SIMBAD M45. Existing framing data
uses SIMBAD 60.26 x 35.48 for M33 and 66 x 66 for M42; catalog boundaries differ.
M78's catalog extent is not the entire faint surrounding complex. M45 requires
manual mosaic configuration on this field and remains eligible. Large angular
size alone does not make M33 easy under urban skies: its mean surface brightness
is faint. M42 and the other popular targets remain subject to their actual
windows, completion and equipment fit. No named-object popularity bonus is used.

Sources: pinned [OpenNGC guide](https://github.com/mattiaverga/OpenNGC/blob/4e2398a263de663d83f7b86be80c368c34335764/NGC_guide.txt)
and shipped CSV; [Sony IMX662 sensor specification](https://www.sony-semicon.com/files/62/flyer_security/IMX662-AAQR_AAQR1_Flyer.pdf).
The manufacturer product page has conflicting desktop/mobile sensor text; this
change does not silently alter the existing IMX662 profile.

## Implemented policy

One transparent suitability adjustment is used in both discovery and final rank:

- Known V <=6 adds 8, <=9 adds 4; unknown V subtracts 6.
- A known long axis >=120 native pixels adds 8, saturating there. No upper-size
  penalty or mosaic exclusion is introduced.
- Galaxies below 120 long-axis pixels subtract 8; below 60 short-axis pixels
  subtract 12. Unknown short axis receives the same conservative 12 penalty.
- Missing scale/extent subtracts 20 for galaxies or 8 otherwise.
- Extended objects with catalog mean B surface brightness >=23 subtract 8;
  missing surface brightness receives the same conservative penalty.
- Galaxies/reflection nebulae under Bortle >=7 or unknown sky background subtract
  10. These are preferences, never new visibility vetoes.
- Completely missing catalog metadata receives a conservative 44-point penalty.

The 120/60 pixel and brightness thresholds are explicit product heuristics, not
calibrated telescope limits. The explanation travels into target and block
selection reasons. Missing unfavorable information cannot improve the reviewed
galaxy scores. Independent review caught and prompted that uncertainty fix.

Each half-hour discovery slot retains stellar, galaxy and nebula alternatives so
bright clusters cannot eliminate every other family before detailed assessment.
The 12,036-entry searchable corpus remains separate from automatic discovery.
The physical discovery gate admits 1,511 entries for this rig before sky checks;
the old 41-entry/0.275-second benchmark predates this quality policy.

No exposure, gain, filter or frame count is invented for new catalog targets.
The detailed four-hour goal (quick two/showcase eight) is a compatibility default,
not an experimentally established integration requirement. Existing capture
history confidence does not certify every legacy catalog preset for this rig.

## End-to-end result and validation

Synthetic clear weather, M31 completed, all other credited integration zero;
real Phoenix October 17-18, 2026 geometry, Bortle 8, Dwarf Mini, 35-degree floor:

| Target | Local scheduled block |
|---|---|
| M39 / NGC7092 | 19:15-23:20 |
| M34 / NGC1039 | 23:20-03:25 |
| M37 / NGC2099 | 03:25-05:12 |

597 minutes allocated including 15 minutes setup; only 0.802 minutes (48 seconds)
of inward-rounded dusk/dawn boundaries remain. New target capture settings stay
unset with a visible confirmation prompt. This is isolated synthetic evidence,
not a replay of Doug's private observation history or a guarantee of best images.

138 Python regressions passed, including 11 new suitability tests. Independent
review reran all 11 successfully and found no remaining implementation blocker.
Tests cover equal-visibility ranking, individual missing fields, changing rig
scale, aliases, saturated size bonuses, faint surface brightness, real seasonal
coverage, completion, setup, polar nights and API/import isolation. The prior
nine Node UI checks remain applicable; no JavaScript changed in this review.

Fresh local browser verification returned HTTP 200 with the three targets above,
working M101 alias search, unset-settings prompts, no JavaScript errors and no
desktop horizontal overflow. Desktop/mobile screenshots remain local. Preview:
http://127.0.0.1:8113/operator using tests/serve_seasonal_fixture.py and an in-memory
database. No attempt was made to bypass the parent's denied Library access.

Remaining limits: no empirical SNR or image-quality calibration; no configured
local obstruction model; bounded candidate search, not a global optimizer. Date,
location, timezone, 35-degree visibility, setup and reconciled integration history
continue to constrain actual allocations. A gap means no evaluated suitable
unfinished target fits, not that every searchable object is impossible.

Release approval is still required: merging develop auto-deploys on Render.
Live observations, backups and calibration output were not modified.
