# Rig profiles

Status: starter data foundation; not yet wired into live recommendations

Polaris needs rig-specific data before it can make trustworthy SNR-style
target and exposure decisions. The first catalog lives in
`app/data/rig_profiles.py` and intentionally starts small.

## Starter devices

- DWARF 3
- Seestar S50
- Seestar S30
- Vespera II
- Vespera 3

## Data policy

Each profile records source URLs and a confidence label. Unknown values stay
unknown. Do not invent read-noise curves, full-well values, exposure limits, or
filter behavior just because a target scorer would benefit from them.

Use these confidence labels:

- `manufacturer`
- `manufacturer_and_help_center`
- `manufacturer_and_official_faq`
- `official_faq_partial`
- `community_reported`
- `measured_by_user`
- `estimated`

## Why this matters

Rig data affects:

- whether a target fits the field of view;
- whether a fitting target is still too small to be satisfying for that rig;
- which sub-exposures are allowed;
- whether tracking can support longer sub-exposures;
- whether a planned run exceeds a device frame limit;
- expected sky-limited exposure behavior;
- confidence in target and exposure recommendations.

## First planning helper

`RigProfile.assess_target_fit()` compares a target's angular width and height
against a rig's native field of view. It returns an explicit fit result:

- `Unknown fit` when either side lacks enough data.
- `Too large` when the object exceeds the native field.
- `Very small` when the object fits but will occupy little of the frame.
- `Tight fit` when the object fits with little framing margin.
- `Comfortable fit` when the object has practical framing room.

This is intentionally a simple framing check. It does not account for mosaics,
cropping preference, rotation constraints, reducer/barlow optics, or post-crop
composition.

`RigProfile.estimate_run_plan()` compares planned imaging time and
sub-exposure length against a rig's recorded single-run frame limit. It returns:

- `No frames` for non-positive imaging plans.
- `Frame limit unknown` when Polaris has no dependable limit for that rig.
- `Single run` when the plan fits the recorded limit.
- `Split run` when the plan should be broken into multiple runs.

For now this is only a planning estimate. It does not control the device,
create runs, or assume that undocumented app limits are safe.

## Future use

The first safe uses are target fit, supported exposure choices, and device
limits. Real SNR calculation should wait until Polaris has reliable sensor
noise, dark-current, gain, and sky-background inputs for the selected rig.
