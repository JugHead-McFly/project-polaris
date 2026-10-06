# Tile 06 forecast comparison review — September 12, 2026

## Verified local findings

Reviewed `app/services/weather_service.py`, `app/services/forecast_accuracy_service.py`, `app/web/operator.js`, and the ignored historical export `.cache/imported-forecast-history.json`.

- The imported Test Site history contains 93 matched snapshots covering 11 distinct forecast target hours. Every forecast and comparison provider is `open-meteo`. These are historical imported records, not independently collected measurements at the development home.
- Open-Meteo `current` fields are stored as observed values. Its documentation explicitly describes current conditions as weather model data; calling these independent observations or verified accuracy is misleading.
- The matcher accepts a 75-minute offset and finalizes pending records immediately. Of the 93 imported snapshots, 86 compare against a model time 45 minutes before the forecast target; 7 compare against a time 15 minutes after it.
- Different forecast revisions for one target can therefore be scored against different comparison values. For September 11 at 8 pm Arizona time (September 12 at 03:00 UTC), earlier revisions use 1% cloud cover at 7:15 pm; the latest revision uses 100% at 8:15 pm. The cause of the model's change is unknown from this export; the records do not prove either value describes the actual sky.
- The longest-lead snapshot selected within each horizon bucket produces cloud absolute differences of 13.18 points (0–6 hours, 11 target hours), 51.67 points (6–12 hours, 6 target hours), and 49.5 points (12–24 hours, 6 target hours). These are not comparable independent accuracy estimates. The latest-snapshot mean is 20.64 points across 11 target hours.
- The chart displays at most eight recent checks using evenly spaced positions and smoothed curves, with only month/day labels. This obscures actual sampling times and suggests continuity between discrete checks.
- The request does not explicitly select a model or persist model-run identity. Fetch time is used as forecast creation time.

## Recommendation (not an implemented change)

Use a simple comparison table with paired values, exact target/comparison times and source. Paired bars or a difference list are alternatives. Remove smoothed connecting curves. Until independent observations exist, label the comparison as a model estimate and distinguish imported Test Site history from home-site validation.

Repair evaluation before choosing a replacement: archive forecasts at fixed lead times (for example 1, 6, 12 and 24 hours), use the same site and target time, assign one reference measurement to all revisions for that target, and record source/model/run and collection times separately. Missing reference data must remain unverified. Preserve imported history rather than silently rewriting it. Use independent sky measurements or timestamped user reports for cloud verification; station temperature/wind readings do not establish full-sky cloud cover at the telescope.

Run a prospective comparison of baseline Open-Meteo, explicit HRRR and NWS, optionally adding meteoblue. A suggested initial collection period is 30–60 nights, extended to include varied weather; it is not a statistical sufficiency guarantee. Compare cloud error and false clear-sky/go decisions separately by horizon. Never backfill latest revised forecasts as if they were forecasts actually available earlier.

## Provider research

No reviewed source demonstrates which provider is most accurate at this site.

- Open-Meteo explicit HRRR: hourly updates at 3 km, cloud-layer fields, available through the existing provider. A useful controlled baseline, but automatic model selection may already use HRRR. https://open-meteo.com/en/docs/gfs-api
- NWS API: US forecasts, grid data and station observations; free/open service. Useful external forecast comparison; observation geography and cloud measurement limitations still matter. https://www.weather.gov/documentation/services-web-api
- meteoblue: Learning Multimodel forecasts and astronomy seeing products; strong feature fit to investigate, not proof of superior local accuracy. Confirm package access and commercial terms before integration. https://docs.meteoblue.com/en/weather-apis/forecast-api/overview and https://content.meteoblue.com/en/private-customers/website-help/outdoor-and-sports/astronomy-seeing
- Tomorrow.io: hourly forecasts for 120 hours; premium minute-by-minute forecasts for the next hour. A commercial challenger, with no local comparative evidence established here. https://docs.tomorrow.io/reference/weather-forecast
- WeatherAPI: existing adapter in Polaris lowers integration effort; provider documents blending GFS, HRRR and ECMWF models. Shared models mean a different vendor is not necessarily independent or better. https://www.weatherapi.com/api-changelog.html

Open-Meteo current conditions and automatic selection: https://open-meteo.com/en/docs
Open-Meteo model-run archive for reproducible evaluation: https://open-meteo.com/en/docs/single-runs-api

No application code, database contents, provider configuration or deployment changed during this review.


## Multi-source correction implemented locally, September 12

Verified implementation: hourly cloud estimates combine the existing primary provider
(Open-Meteo, or WeatherAPI fallback) with NWS grid skyCover where available. Each source
gets equal weight. Missing values are excluded, never interpreted as clear. NWS grid
updates older than 12 hours are excluded. Source values, spread, and hourly timestamps
are retained in recommendation input_provenance; historical forecasts are not rewritten.
New blended accuracy snapshots are labeled cloud-blend-v1.

Forecast clouds alone now produce Use Caution and retain the target plan. The planned
105 F heat stop remains. Cloud points can reach zero without discarding independent
wind/humidity score contributions. A comparison disclosure next to the recommendation
shows both start estimates and a time-weighted astronomical-darkness cloud mean when
at least 90% of that window is covered; it also discloses two-source coverage.

Live local check: Open-Meteo 100%, NWS 36% at the selected start; mean 68%, spread
64 percentage points. Darkness-window mean rounded to 24%, with both sources covering
100% of the window. These are forecasts, not observations or proof of improved accuracy.

Unknown: whether the mean beats either provider at this site. Sources may share model
inputs; their spread is not a confidence interval. No calibrated weights or probability
of an imaging success is claimed. Historical point checks remain distinct from nightly
averages. Collection still depends on recommendation runs; unattended daily collection,
fixed lead-time snapshots, and automatic full-night satellite verification remain work
to complete. This change has not been pushed to Render.

NWS grid semantics: https://github.com/weather-gov/api/blob/master/gridpoints.md
NWS API: https://www.weather.gov/documentation/services-web-api
