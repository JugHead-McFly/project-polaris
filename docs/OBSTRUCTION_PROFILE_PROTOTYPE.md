# Personal obstruction planning — backend prototype

2026-10-07. Local, uncommitted prototype based on develop `b6545684`.

## Evidence and decision

**Verified project evidence:** [Voice of Customer](VOICE_OF_CUSTOMER.md) records
one detailed house/tree blockage report, labeled directional evidence, not broad
validated demand. The [Product Bible](PRODUCT_BIBLE.md) calls for local horizon
constraints when known. Current planning uses a fixed 20° altitude floor.

**Public evidence, reviewed 2026-10-07:**

- [DWARF owner discussion](https://www.reddit.com/r/DWARFLAB/comments/1s5ji5r/how_do_you_plan_sessions/)
  includes balcony/obstruction planning difficulties. This is qualitative pain
  evidence, not feature usage, retention, or willingness-to-pay measurement.
- [Observer Pro](https://observer.pro/) advertises measured local horizon
  profiles and site-specific visibility. This establishes a competitor pattern,
  not its accuracy or traction.
- [Stellarium's polygonal landscape documentation](https://stellarium.org/doc/head/classLandscapePolygonal.html)
  describes measured azimuth/altitude horizons and separate alignment of photo
  panoramas and horizon polygons. Azimuth is true north toward east.
- [NINA Target Scheduler](https://tcpalmer.github.io/nina-scheduler/target-management/projects.html#horizon-determination)
  distinguishes the minimum altitude floor from a custom horizon and its offset.
- [Apple's Pano instructions](https://support.apple.com/en-gb/guide/iphone/iph7e06402b4/ios)
  allow the user to stop the sweep and use vertical panoramas. They do not provide
  an astronomical pixel-to-angle or true-north calibration contract.

**Inference:** a measured geometry input can make Polaris's nightly decisions
more locally useful. **Unknown:** broad user traction, measurement accuracy on a
real iPhone, and the right capture/settings workflow. An arbitrary panorama must
not be treated as a calibrated sky map.

**Scope decision:** implement a pure backend foundation. There is no photo upload,
sensor capture, automatic photographic measurement, HTTP input, persistent schema,
UI, migration, deployment, or equipment control. Account/site ownership for stored
surveys and the measurement workflow need a separate product design. Existing
hosted contexts still have no profile unless a backend caller explicitly supplies
one for that exact observing setup.

## Input contract and use

`ObstructionProfile.model_validate(data)` validates a complete manual survey.
Attach it to a fresh immutable `ObservatoryContext` used for a single plan.
`get_dark_visibility`, `build_target_plan`, `get_tonight_plan`, and the existing
`get_tonight_schedule` context pipeline then honor it. No process-global profile,
profile cache, or cross-account lookup is introduced.

```python
from dataclasses import replace
from app.core.obstruction_profile import ObstructionProfile

# Synthetic values only. The caller must have surveyed the whole sky around the
# telescope, including overhead structures; these are not a survey of Doug's site.
survey = ObstructionProfile.model_validate({
    "complete_coverage": True,
    "horizon": [
        {"azimuth_degrees": 0, "altitude_degrees": 15},
        {"azimuth_degrees": 90, "altitude_degrees": 35},
        {"azimuth_degrees": 180, "altitude_degrees": 10},
        {"azimuth_degrees": 270, "altitude_degrees": 25},
    ],
    "sectors": [{
        "start_azimuth_degrees": 350,
        "end_azimuth_degrees": 20,
        "minimum_altitude_degrees": 60,
        "maximum_altitude_degrees": 90,
    }],
    "clearance_degrees": 1,
})
# authorized_site_context comes from the caller's existing per-account/site path.
# Do not carry this profile to a different site via dataclasses.replace.
survey_context = replace(authorized_site_context, obstruction_profile=survey)
# plan = get_tonight_plan(db, observatory=survey_context, target_names=["M31"],
#                         use_capture_history=False)
# schedule = build_tonight_schedule(plan, timezone_name=survey_context.timezone_name)
```

- Numeric inputs must be finite numbers, not strings or booleans. Unknown fields
  are rejected. Profiles and nested geometry are immutable.
- Horizon: 2–720 unique, strictly increasing azimuths in `[0, 360)`, altitude
  `[0, 90]`. Zero is true north; angles increase eastward. Do not repeat north as
  360. Interpolation is linear and cyclic, including last-to-first across north.
- `complete_coverage: true` is required, with no default. It means the caller
  explicitly accepts the entire interpolated horizon and has represented known
  overhead obstacles. False, missing, and partial/unknown coverage are rejected;
  unmeasured directions must not be supplied as zero-height points. The software
  cannot verify the honesty or accuracy of that declaration.
- Up to 64 optional inclusive, clockwise sectors describe bounded vertical
  obstacles (e.g. a balcony roof). `350 → 20` crosses north. Minimum altitude must
  be less than maximum. Equal azimuth endpoints are ambiguous and rejected;
  represent full-circle overhead coverage with multiple sectors. Overlap is safe.
- Clearance is a vertical margin of 0–10°, default **1°**, applied above the
  horizon and on both vertical edges of sectors. It does not expand azimuth
  edges. This is a prototype design input, **not a proven sensor-error bound**.
- The independent 20° quality floor remains mandatory. A lower horizon cannot
  lower it; a higher horizon or roof can only restrict visibility. Equality with
  the local obstruction plus clearance is blocked; equality with the 20° floor
  alone remains allowed.

## Windows and scheduler integration

Without a profile the existing 15-minute altitude path, scores, output shape, and
endpoint behavior remain unchanged. With a profile:

1. Compute unrounded target-center azimuth/altitude at whole-minute instants.
   Fixed catalog targets use one vectorized Astropy transform per target; moving
   targets retain time-specific coordinates, including ephemeris positions.
2. Accept a one-minute interval only if both positions are known, above the
   quality floor, and its swept angular box clears the interpolated horizon and
   every intersecting sector. Include all horizon knots and sector boundaries
   crossed on the short azimuth arc, so a thin supplied obstacle between clear
   samples is not simply skipped. Steps over 5° azimuth per minute are rejected
   as unresolved, rather than extrapolated through rapid direction changes.
3. Split on every rejected interval. Keep all disjoint windows in the internal
   visibility result, but recommend **only the longest contiguous window**.
   Do not sum separated windows to meet the 45-minute planner minimum. Ties keep
   the earlier window. Secondary windows are deliberately not scheduled yet.
4. Pass that single window through the existing planner and scheduler fields.
   Never extend beyond the last accepted endpoint. Round the usable start inward
   to the next whole minute and end inward to the previous minute before sampling,
   so existing formatted schedule times cannot leak into a rejected interval.
5. Explain the applied constraint and exclusion reasons in `selection_reason`;
   nightly notes also identify excluded targets. The internal visibility result
   exposes `obstruction_windows` and `obstruction_exclusion_reasons` for review.
   No public response schema change is required. Existing weather vetoes, rig
   scheduling limits, and integration-goal logic remain in force.

## Limits and later decisions

This is sampled advisory geometry, not a guarantee of physical clearance. Between
one-minute samples, the swept box assumes a short, monotonic angular path bounded
by the endpoints. It can reject usable time conservatively, and cannot prove
continuous clearance for arbitrary curvature, fast-moving objects, an incomplete
survey, moving foliage, or an inaccurate north reference. Sparse horizon points
can hide unrecorded peaks. Near-zenith azimuth changes may exclude extra time.
No automatic calibration, claimed angular precision, spherical image projection,
full-frame footprint, telescope collision envelope, or refraction correction is
provided. A clear target center does **not** establish an unobstructed image frame.

Aware input bounds are first normalized to the supplied site's timezone, even
when callers provide UTC bounds. Naive bounds are rejected. Times are evaluated
on a UTC minute grid then returned in the site's local zone, including midnight
crossings. Nights spanning a UTC-offset transition and windows containing an
ambiguous local time (including windows wholly inside either occurrence of a
repeated DST hour) are explicitly excluded in this profile path: the existing
schedule string format cannot safely disambiguate those timestamps. Fixing that requires a separate
backward-compatible schedule timestamp design. The no-profile path is unchanged.

There is no persistence, so database tenant-isolation migrations/tests are not
applicable. Tests cover independent immutable contexts, existing hosted isolation,
and no-profile parity. Before production exposure, bind every stored survey to
its authenticated account and exact site/setup, test those boundaries, design a
partial-coverage workflow, validate real measurements, and measure catalog-wide
latency (especially solar-system/ephemeris targets). Phone reticle capture and a
panorama used only as a visual reference are later possibilities requiring real
iPhone orientation/north-calibration testing. No browser or device validation is
claimed for this backend prototype.
