# Cloud observation pilot — September 12, 2026

## Historical backfill completed later September 12

The user selected satellite data and requested historical retrieval. They confirmed the imported Test Site was the same physical location as Home. The development database contained 96 forecast revisions across 13 target times: 93 historical records at 11 times, plus 3 pending records at 2 future times.

Retrieved GOES-18 ACMC scans for all 11 past forecast times (September 1–11 at 8 pm Arizona time). Each selected scan midpoint was about 2 minutes 23–24 seconds before the target. All 47 regional pixels passed the cloud-mask quality check for every selected scan. These remain satellite-derived regional estimates, not ground-truth whole-sky measurements.

Added nullable JSON `satellite_cloud_observation` via migration `20260912_0009`. Stored source URLs, SHA-256 hashes, scan times, target offsets, classification uncertainty, pixel coverage, region, method version and location provenance. All revisions for the same target receive the same satellite reference. Original forecast, model-observation, status and timestamp fields are unchanged. Future records remain empty. This change applies only to the development database; nothing was pushed or deployed to Render.

Verification: 18 migration/forecast-history tests passed. Import transaction compared every original field before and after, checked owner isolation without tenant context and verified 93 attached references across 11 times. A second run verified idempotence (zero updates).

Tile 06 now displays the satellite references in the selected reliability-summary design. Each local evening is a collapsed native disclosure, with forecast and satellite values, exact timestamps, lead time and quality information inside. The tolerance selector offers 10, 20 and 30 percentage points and preserves expanded evenings. At the default tolerance, 4 of 11 checks qualify; mean absolute difference is 46.8 points. Browser verification confirmed expansion/collapse and the change to 5 of 11 at 30 points. These historical records contain single-hour forecasts, so this backfill does not create retrospective whole-night forecast averages.

The API excludes unusable references, nonfinite/out-of-range values, low pixel coverage, target mismatches, scan offsets over three minutes and forecasts saved at/after their target. One latest revision is selected per target. Post-midnight checks group with the previous local evening. Backend, response serialization, migration and dashboard checks passed. The local development server was restarted; no Render deployment occurred.

Diagnosis remains uncertain: the September 5 example has 0% forecast vs 100% satellite regional cloud classification, despite a forecast saved roughly 43 minutes ahead. The previous 45-minute reference mismatch no longer applies. The imported forecasts lack upstream model/run identity, and the satellite regional fraction is not a locally validated whole-sky measurement. Do not claim this proves the forecast vendor alone caused the discrepancy or that the observed fraction is a calibrated probability for tonight.

Reproducible evidence in ignored `.cache/goes-cloud-probe/`: `db-targets.json`, `fetch_history.py`, `historical-files.json`, `extract_history.py`, `historical-observations.json`, `store_history.py`, `import-verification.json`, and original satellite files.

| Local evening | Satellite regional cloud estimate near 8 pm |
| --- | ---: |
| Sep 1 | 0.0% |
| Sep 2 | 17.0% |
| Sep 3 | 38.3% |
| Sep 4 | 78.7% |
| Sep 5 | 100.0% |
| Sep 6 | 100.0% |
| Sep 7 | 100.0% |
| Sep 8 | 91.5% |
| Sep 9 | 0.0% |
| Sep 10 | 6.4% |
| Sep 11 | 0.0% |

## Result

Verified: GOES-18 ABI cloud-mask data can be downloaded anonymously and decoded for the saved Arizona location. A one-night feasibility test produced near-complete nighttime coverage. This establishes technical availability, not accuracy against the actual sky at the telescope. No application or database changes were made, and no recurring collector was started.

## Night tested

- Local evening September 11 through morning September 12, 2026.
- Approximate astronomical darkness: 8:02 pm–4:45 am Arizona time (03:02:20–11:44:33 UTC).
- Boundaries computed using Astropy, Sun altitude -18 degrees and saved coordinates. Offline Earth-orientation fallback was used; minute-level boundaries are sufficient for this feasibility test, not an assertion of subsecond accuracy.
- Source: public `noaa-goes18` S3 bucket, `ABI-L2-ACMC/2026/255/`.
- 105 scans selected, approximately five minutes apart; 104 had at least 90% good-quality pixels in the selected area. One scan near 2:27 am local had no usable area pixels.
- Tested area: approximate 10 km radius around the saved location, containing 47 native pixels. The nearest pixel center was about 1 km from the location.
- Accepting only DQF=0 and valid cloud classifications yielded approximately 99.04% temporal coverage, using nominal five-minute support clipped to the darkness window.
- Approximate time-weighted regional cloud fraction: 20.14%. This equally weights valid pixels within each scan, then weights scans by supported time. It is not an angular whole-sky percentage measured at the telescope, and the selected radius is an uncalibrated prototype choice.
- Approximately 12.88% of regional pixel-time classifications were probably clear/probably cloudy. This is a diagnostic, not a calibrated error bar. The binary mask counts probably cloudy with cloudy, per the product definition.
- No historic forecast comparison was attempted: the prior imported snapshots do not contain locked whole-night forecast series for this test.

## Product selection and limitations

The initial Cloud Cover Layers (`ABI-L2-CCLC`) test returned 6 good, 5 degraded and 94 bad-quality flags for the nearest regional cell. Its DQF inherits cloud-height retrieval quality, so this is not proof that all corresponding cloud-mask observations are bad. Do not treat flagged zero values as verified clear weather or use the six accepted samples as a whole-night average.

The finer Clear Sky Mask has its own classification and quality flags and yielded much more usable data. Satellite retrievals are observation-based but still algorithmic and may use auxiliary model information. They are not a perfect independent ground truth. Thin cloud, spatial representativeness, nighttime performance and uncertainty need comparison with local sky images. A 10 km regional average cannot establish whether a particular target direction was obstructed.

Raw downloads and reproducible scratch probes are in ignored `.cache/goes-cloud-probe/`: `probe.py`, `report.json`, `samples.csv`, `mask_probe.py`, `mask-report.json`, and original NetCDF files. Temporary NetCDF dependencies were installed into `.cache/cloud-probe-deps`, not application requirements.

Primary references:
- https://registry.opendata.aws/noaa-goes/
- https://www.ncei.noaa.gov/products/goes-terrestrial-weather-abi-glm
- https://vlab.noaa.gov/web/towr-s/goes-csm
- https://vlab.noaa.gov/web/towr-s/goes-ccl

## Nearby camera findings

### James Yoder / ArtCentrics — Chandler

The owner publishes an all-sky camera and setup guide. The public Allsky map places it approximately 14 km / 9 miles from the saved location. This is approximate straight-line distance based on voluntarily published camera coordinates; no residential address is needed.

- Owner page: https://artcentrics.com/artcentrics-astronomy-main-page/astronomy-resources/site-weather-and-conditions/
- Viewer: https://allsky-yoder.artcentrics.com/
- Public registry: https://www.thomasjacquin.com/allsky-map/
- Owner contact page: https://artcentrics.com/contact-me/

Viewer and configured `image.jpg` returned HTTP 200. The image's Last-Modified header was September 8, 2026 at 20:33:46 UTC when checked September 12, so live freshness is not established and it appears stale. No automated reuse license was verified. Strongest nearby full-sky lead; owner permission, feed health, archives and nighttime image quality need confirmation.

### Weather Chit Chat — Gilbert / NE Mesa and Gold Canyon

- https://www.weatherchitchat.com/weather-webcam-mesa.php
- https://www.weatherchitchat.com/weather-webcam-superstitions.php
- https://www.weatherchitchat.com/contact.php

Both public image endpoints returned HTTP 200 and Last-Modified timestamps on September 12 around 21:40 UTC during the test. The Gilbert-labeled page says the camera points north and updates every minute; its actual image path and some site text refer to NE Mesa, so exact location should be confirmed. Gold Canyon is a Superstition Mountains view. These are directional views, not established full-sky night observation feeds. Nighttime usefulness was not verified. Site footer says all rights reserved; no automated reuse permission was found.

### Other leads

East Valley Astronomy Club manages the Gilbert Rotary Centennial Observatory and is a relevant route to other local camera owners: https://www.evaconline.org/ . A directory also lists a Phoenix camera without a public viewer, so it was not counted as an available source. Lowell's Anderson Mesa camera is near Flagstaff, not Mesa in the Phoenix valley, and its current operations page requires VPN; it is not a suitable nearby public feed.

No owners were contacted. Public visibility does not establish permission for automated collection or redistribution.

## Recommended next step

Extend the satellite pilot over varied nights and retain quality/coverage information. Validate the selected area and nighttime cloud classifications against an authorized local sky-camera source. Keep this separate from production reliability scores until its limitations and missing-data handling are agreed. The proposed nightly forecast captures remain six hours before astronomical dusk and at dusk, each evaluated over the same dusk-to-dawn window.
