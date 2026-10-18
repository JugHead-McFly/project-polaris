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
that configuration. Their OpenNGC types are open clusters. The original DWARF
mini profile recorded supported exposures of 15/30/60/90 seconds but omitted
gain and filters. Independent review checked the current manufacturer manual,
section 3.2.2.2, on 2026-10-18:
https://help.dwarflab.com/en/docs/DWARF-mini-Smart-Telescope-User-Manual

The manual recommends exposures of 15-60 seconds and gain 60-80, Astro for
galaxies/star clusters and Duo-Band for emission nebulae. Polaris now records
these filter capabilities and selects gain 60 at the lower end of that range.
The 15-second choice is a conservative application starting policy within the
manufacturer's range, not evidence of a unique manufacturer default or optimal
per-target calibration. These three clusters share a category; identical
starting settings do not claim identical observed performance.

The hosted observatory schema stores
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
- The three reported clusters receive 15 seconds, gain 60 and Astro as
  manufacturer-informed Mini starting recommendations. This corrects an
  incomplete equipment profile; it does not retrieve or overwrite device values.
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
user-configured values still require device/configuration evidence; they cannot
be recovered from hosted rows that never stored those values. Manufacturer
recommendations are sufficient for a labeled starting point, not such recovery.

## Regression coverage

`test_catalog_capture_settings.py` covers the three reported aliases, curated
NGC/Messier recipe equivalence, DWARF Mini versus DWARF 3 capabilities, unknown
equipment, existing successful settings precedence, and preserved alias history.
Seasonal tests retain real astronomy checks over October, December and February,
including complete night coverage, altitude floors and integration budgets;
their prior assertion of intentionally missing exposure is updated to the
new source-backed starting recommendation. Tests use memory SQLite and disabled IERS
downloads, never live observations or external credentials.
