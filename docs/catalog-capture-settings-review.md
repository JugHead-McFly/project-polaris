# Catalog capture settings investigation

## Confirmed cause

The seasonal/OpenNGC catalog extension deliberately returned null exposure,
gain and filter in `get_target_metadata`. The planner then skipped the existing
condition/type settings engine whenever the exposure was null. Thus selecting
an expanded-catalog object bypassed otherwise available equipment/category
starting guidance. This was not evidence that the user's telescope was
misconfigured.

Curated recipes were also keyed only by designation. NGC6705 did not inherit
the existing M11 recipe even though the pinned catalog resolves them to one
physical object. Alias matching now consults physical catalog identity before
the geometry-only fallback. Observation IDs and history are not rewritten.

## What was previously configured

The checked-in recipes include M11/M22 at 10 seconds, gain 60 and Astro, and
M16/M17/M20 at 15 seconds, gain 80 and Duo-Band. Existing general DWARF settings
rules use 15 seconds and gain 60. These are application starting recipes, not
proof of empirical calibration of every telescope or target.

M39 (NGC7092), M34 (NGC1039), and M37 (NGC2099) have no individual recipe in
that configuration. Their OpenNGC types are open clusters. The selected DWARF
mini profile records supported exposures of 15/30/60/90 seconds, but explicitly
has no recorded default gain or filters. The hosted observatory schema stores
rig choice and tracking preference, not a per-target exposure/gain preset.
Imported hosted history stores integration, frame counts and filter labels;
it stores neither exposure nor gain, and explicitly does not grade quality.

This investigation did not inspect production account rows or the user's live
local library. It therefore cannot establish whether a previously configured
device setting exists outside the application's available source/configuration.
No such configuration has been deleted or overwritten by this correction.

## Resulting behavior

- Physical aliases reuse existing curated recipes before generic fallback.
- New catalog targets with a recognized category and supported rig exposures
  receive an explicitly labeled equipment/category starting exposure.
- The three reported clusters receive a conservative 15-second DWARF mini
  starting exposure. Gain/filter stay unavailable rather than inheriting
  unverified DWARF 3 values. Guidance tells the operator to retain/confirm device
  values; it does not claim that they forgot configuration.
- Known DWARF 3 capability data allows gain 60 and category-appropriate Astro or
  Duo-Band recommendations under the existing conditions rules.
- Existing successful local capture recipes keep precedence and source IDs;
  ungraded imported integration history does not become calibrated advice.
- Unknown rigs/categories remain unknown. Mosaic candidates still require
  manual planning. Integration goals, history and astronomical eligibility are
  unchanged.
- Secondary target names include an existing reliable Messier alias (M39/M34/M37)
  while canonical storage/schedule identifiers remain unchanged.

`settings_provenance` records source, selected rig, capability source URLs and
whether capture history was used. The confidence label explicitly distinguishes
a category starting point from capture calibration. Full Mini gain/filter
recommendations require reliable device/configuration evidence; they cannot be
recovered from hosted rows that never stored those values.

## Regression coverage

`test_catalog_capture_settings.py` covers the three reported aliases, curated
NGC/Messier recipe equivalence, DWARF Mini versus DWARF 3 capabilities, unknown
equipment, existing successful settings precedence, and preserved alias history.
Seasonal tests retain real astronomy checks over October, December and February,
including complete night coverage, altitude floors and integration budgets;
their prior assertion of intentionally missing exposure is updated to the
new partial starting recommendation. Tests use memory SQLite and disabled IERS
downloads, never live observations or external credentials.
