# Quality Scoring v2

Quality Scoring v2 replaces the original fixed star-count ladder with
measurements that describe technical image quality. It remains a capture-review
aid, not a scientific grade or a prediction of the final processed image.

## Why v2 is needed

The original score gave every capture a 50-point starting value and awarded up
to 20 points for the absolute number of detected stars. That made the result
depend too heavily on the target and field of view. A globular cluster, a
planetary nebula, and a broad emission nebula should not need the same number of
detected stars to be considered successful.

In v2:

- detected-star count is diagnostic and determines confidence, but earns no
  points;
- point-based measurements describe sharpness, star shape, star
  signal-to-noise, background uniformity, and clipping;
- captures are compared primarily with other captures of the same target;
- the scoring version is stored with every analysis so a future formula change
  cannot silently reinterpret an old score;
- the v1 score is preserved when an existing analysis is upgraded.

## Score components

| Component | Maximum | Measurement |
| --- | ---: | --- |
| Sharpness | 30 | Median stellar full width at half maximum (FWHM), in pixels; smaller stars are sharper. |
| Star shape | 25 | Median stellar roundness; values nearer zero indicate rounder stars. |
| Star signal | 20 | Median detected-star peak divided by robust background noise. |
| Background uniformity | 15 | Difference between sigma-clipped background tiles relative to image signal. |
| Highlight protection | 10 | Fraction of pixels clipped at the image maximum. |

The score is the sum of the five components. There is no automatic base score.

## Confidence and supported captures

Deep-sky scoring requires at least 25 usable stellar measurements. Captures
with 10–24 usable stars may expose measurements with limited confidence but do
not receive a final v2 score. Captures with fewer than 10 usable stars are not
scored by the deep-sky model.

Planetary and lunar imaging require a separate high-frame-rate quality model.
Polaris therefore reports those captures as unsupported by the v2 deep-sky
model instead of manufacturing a misleading score from a handful of field
stars.

## Starter equipment profiles

FWHM is measured in pixels and depends on the imaging system. The engine uses a
named equipment profile selected from the FITS telescope metadata. Project
Polaris includes a reviewed DWARF mini starter profile and a conservative
generic fallback. Later releases can add user calibration and profiles for
other equipment without changing the stored v2 measurements.

## Background method

Polaris estimates background noise with the median absolute deviation (MAD).
Background uniformity uses a four-by-four grid of sigma-clipped tile medians so
bright stars and compact target structure have less influence than they would
in a raw whole-image standard deviation.

## Migration policy

The schema migration adds v2 measurement fields and marks existing rows as
version 1. Existing `quality_score` values are copied to
`legacy_quality_score` before a capture is reanalyzed. Reanalysis is a separate,
explicit operation performed only after the database has been backed up.

## References

- [Photutils point-source detection](https://photutils.readthedocs.io/en/stable/user_guide/detection.html)
  documents FWHM, roundness, sharpness, and background-threshold source
  detection.
- [Photutils DAOStarFinder](https://photutils.readthedocs.io/en/stable/api/photutils.detection.DAOStarFinder.html)
  explains the roundness and sharpness statistics.
- [Astropy sigma clipping](https://docs.astropy.org/en/stable/api/astropy.stats.sigma_clipping.sigma_clip.html)
  documents iterative rejection of outlying pixels for robust background
  statistics.
- [Siril documentation](https://siril.readthedocs.io/_/downloads/en/latest/pdf/)
  uses FWHM and star roundness as star-based image-selection measurements.
