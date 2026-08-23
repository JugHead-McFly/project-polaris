# Rig profiles

Status: V1.9 foundation wired into hosted Tonight recommendations

Polaris needs rig-specific data before it can make trustworthy SNR-style
target and exposure decisions. The first catalog lives in
`app/data/rig_profiles.py` and is now used by hosted Tonight planning when a
user selects a rig for their observing home.

## Current device coverage

The current database covers the major manufacturer-backed smart-telescope
families Polaris has official specs for:

- DWARFLAB DWARF II
- DWARFLAB DWARF 3
- DWARFLAB DWARF mini
- ZWO Seestar S50
- ZWO Seestar S30
- Vaonis Stellina
- Vaonis Vespera II
- Vaonis Vespera Pro
- Vaonis Vespera 3
- Vaonis Vespera Pro 2
- Vaonis Hestia
- Celestron Origin Intelligent Home Observatory
- Celestron Origin Mark II Intelligent Home Observatory
- Unistellar Odyssey
- Unistellar Odyssey Pro
- Unistellar eQuinox 2
- Unistellar eVscope 2

This is not a claim that Polaris knows every discontinued, regional, prototype,
or crowdfunded smart telescope. Additions should be made only from official
manufacturer or support documentation, with unknown values left blank.

Current catalog summary:

- 17 total profiles.
- 5 manufacturers: Celestron, DWARFLAB, Unistellar, Vaonis, and ZWO.
- 15 profiles with rectangular field-of-view data usable for framing checks.
- 14 profiles with a published normal battery-life value.
- 13 profiles with a published storage-capacity value.
- 5 profiles with a published operating-temperature range.
- 1 profile with a documented single-run frame limit.

## Read-only catalog API

The local V1.9 foundation exposes a protected read-only catalog endpoint:

    GET /rig-profiles
    GET /rig-profiles/{rig_key}
    GET /rig-profiles/{rig_key}/fit-check
    GET /rig-profiles/{rig_key}/run-plan
    GET /rig-profiles/{rig_key}/target-score

The catalog route returns the catalog summary plus plain-language-ready profile
summaries. The detail route returns the source-backed profile fields for one
selected rig. The fit-check route accepts target width and height in degrees
and returns the rig's framing label, margin, and reason. The run-plan route
accepts imaging minutes and sub-exposure seconds and returns estimated frame
count plus single-run, split-run, or unknown-limit status. The target-score
route accepts experimental opportunity inputs and returns a 0-100 score with
the component-by-component reasoning. These routes do not create, edit, or
delete profiles.

## User rig selection foundation

Hosted observatories can now store an optional `rig_profile_key`. The field is
validated against the known rig catalog and normalized to the stable key, such
as `dwarf-3`, even if a model name like `DWARF 3` is submitted.

The hosted operator setup and **Edit observing home** flow now let a user pick
their rig from the catalog. Tonight displays the selected rig on the primary
target card and includes a short rig-match explanation for the selected target.
If the selected rig has no published rectangular field of view, Polaris can
calculate one only when trusted focal-length, resolution, and pixel-size specs
are all present. Otherwise, Polaris says framing is not yet supported instead
of guessing.

Existing observatories may still have no rig selected. In that case Tonight
falls back to the existing generic explanation and labels the rig profile as
not specified until the user updates their observing home.

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
- whether the user's planned session is likely to press battery, storage, or
  temperature limits;
- expected sky-limited exposure behavior;
- confidence in target and exposure recommendations.

## Official operating-limit fields

Profiles now reserve fields for:

- storage capacity in GB;
- normal battery life in hours;
- battery life with dew heating active, when the manufacturer publishes it;
- operating temperature range in Celsius;
- recorded single-run frame limit, when documented.

Unknown values remain `None`. This is intentional. Polaris should warn from
known constraints, but it should not invent battery, storage, thermal, or frame
limits when an official source does not publish them.

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

The active safe use is target fit and visible target-to-rig reasoning. The next
safe uses are supported exposure choices and device limits, especially
single-run frame limits, tracking mode, battery, storage, and heat cautions.
Real SNR calculation should wait until Polaris has reliable sensor noise,
dark-current, gain, and sky-background inputs for the selected rig.
