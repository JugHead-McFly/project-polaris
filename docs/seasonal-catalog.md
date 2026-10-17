# Seasonal catalog expansion — local review

The previous catalog contained only 17 objects and none of M33, M45, M42,
M1, M78 or NGC281. With M31 complete, real Phoenix astronomy on October 17,
2026 left no unfinished catalog target after C20 set below 35 degrees at
00:26. A high-scoring manual C20 mosaic also displaced single-frame options.
This is a candidate-coverage and selection problem, not a universal three-hour cap.

## Catalog provenance

Catalog values checked October 17, 2026. Coordinates are J2000/ICRS;
dimensions below are arcminutes, converted to degrees only for equipment fit.

| ID | RA | Dec | Extent used | Type | Source |
|---|---|---|---|---|---|
| M33 | 01:33:50.897 | +30:39:36.63 | 60.26 × 35.48 | Spiral galaxy | [SIMBAD](https://simbad.cds.unistra.fr/simbad/sim-id?Ident=M+33) |
| M45 | 03:46:24.2 | +24:06:50 | 76.86 × 76.86 | Open cluster | [SIMBAD](https://simbad.cds.unistra.fr/simbad/sim-basic?Ident=M45) |
| M42 | 05:35:16.8 | −05:23:15 | 66 × 66 | Emission nebula | [SIMBAD](https://simbad.cds.unistra.fr/simbad/sim-id?Ident=M+42) |
| M1 / NGC1952 | 05:34:31.97 | +22:00:52.1 | 8 × 4 | Supernova remnant | OpenNGC |
| M78 / NGC2068 | 05:46:45.82 | +00:04:45.5 | 4.5 diameter | Reflection nebula | OpenNGC |
| NGC281 | 00:52:59.35 | +56:37:18.8 | 35 × 30 | H II emission nebula | OpenNGC |

OpenNGC data attribution: Mattia Verga, [OpenNGC database](https://github.com/mattiaverga/OpenNGC),
[data](https://raw.githubusercontent.com/mattiaverga/OpenNGC/master/database_files/NGC.csv),
[field/source definitions](https://raw.githubusercontent.com/mattiaverga/OpenNGC/master/NGC_guide.txt),
CC BY-SA 4.0. The three adapted catalog entries retain that attribution and
[license](https://creativecommons.org/licenses/by-sa/4.0/).
Its coordinates cite NASA/IPAC NED; M1/NGC281 sizes cite HEASARC LBN,
M78's single diameter cites HEASARC MWSC. M78 uses that diameter as a circular
bounding estimate, not a measured minor axis or the whole surrounding dust complex.
M1's position is the Crab pulsar. Extended nebulosity and photographic framing
can exceed catalog boundaries; field fit is not a guarantee of framing margin.
M45 needs a mosaic on Dwarf Mini. The other five catalog extents fit its
approximately 2.13 × 1.20 degree field; M42 has little margin on the short axis.

## Preservation and selection policy

No database migration, observation edit, import rewrite or calibration change.
The six new entries retain their previous four-hour detailed fallback goals,
including the existing quick/showcase multipliers. Adding a scientific type
must not silently increase a goal and reopen an already completed project.
This is a compatibility baseline, not a claim that every target needs four hours.
No exposure, gain, filter or frame count is inferred from catalog coordinates.
Existing recorded capture settings still follow the existing advisor path.
Without such settings, the cards explicitly require confirmation before capture.

Highest-scoring available single-frame targets precede manual mosaics. A
single-frame run continues until its remaining goal, visibility limit or dawn.
Mosaics remain available when no suitable single-frame target can run, and yield
when one rises. They never claim imaging integration or fabricated panel settings.
Three to four targets is a soft preference: once three have been selected,
equal-score ties favor an already selected target. No forced switch merely to
reach three; no hard four-target cutoff; no extension past remaining goals.

## Reproducible Phoenix scenario

Synthetic clear weather and integration history (M31 complete; others zero),
Phoenix 33.4484, −112.074, 331m, America/Phoenix, Bortle 8, Dwarf Mini;
real Astropy sky geometry, 35-degree floor, October 17–18, 2026.
Astronomical darkness 19:14:47–05:12:35.

| Target | Local block | Stop condition |
|---|---|---|
| NGC281 | 19:15–23:20 | Four-hour remaining goal plus five-minute setup |
| M33 | 23:20–03:25 | Four-hour remaining goal plus five-minute setup |
| M1 | 03:25–05:12 | Astronomical dawn, rounded inward |

597 scheduled minutes, including 15 setup minutes; 0.802 minutes of boundary
gaps. This is an advisory timing plan: all three capture settings require
confirmation. It is not a replay of Doug's account or a guarantee of weather,
unconfigured horizon clearance, framing or image quality. Offline IERS fallback
warns of arcsecond-level coordinate precision limits for these future dates.

No push, merge or deployment is authorized by this review. Base/rollback is
7cc8ff1ae1023691fdee290d4bd15d62ee5e6514; branch codex/long-dwell-cards.

## Validation and preview

114 related Python regressions passed, including real-sky Oct17, Dec15 and
Feb15 checks sampling every scheduled minute above35 degrees, goal accounting,
completed-target exclusion, null settings, API/import behavior and mosaic fallback.
Additional isolated June21 run: M13 then M57, 0.98min gap. Dec15: M33, M1,
M97, 0.78min gap; Feb15: M1, M63, 1.63min gap. February's tiny remainder is
whole-minute/whole-exposure rounding, not missing hours. Two targets suffice.

Preview: `python tests/serve_seasonal_fixture.py` with
`POLARIS_DATABASE_URL=sqlite:///:memory:` and `POLARIS_ENVIRONMENT=test`, then
http://127.0.0.1:8112/operator . Its history is synthetic and its account library
is intentionally empty. No real telescope, weather or account requests occur.
Desktop1440px and mobile390px render with visible verification prompts,
no JavaScript errors, and no horizontal overflow in the desktop check.
