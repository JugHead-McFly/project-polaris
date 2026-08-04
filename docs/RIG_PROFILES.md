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
- which sub-exposures are allowed;
- whether tracking can support longer sub-exposures;
- whether a planned run exceeds a device frame limit;
- expected sky-limited exposure behavior;
- confidence in target and exposure recommendations.

## Future use

The first safe uses are target fit, supported exposure choices, and device
limits. Real SNR calculation should wait until Polaris has reliable sensor
noise, dark-current, gain, and sky-background inputs for the selected rig.
