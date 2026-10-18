# Independent review and corrections

Reviewer: separate `independent_release_review` agent, not the settings author.
Initial review target: f4781aec6dc24e2a58936ab3442ced3b9e45dd2c.
Final verdict on corrected working tree: no blocking findings.

## Findings resolved

1. The Mini profile omitted gain/filter evidence that is available in the
   manufacturer manual, section 3.2.2.2, checked independently on 2026-10-18:
   https://help.dwarflab.com/en/docs/DWARF-mini-Smart-Telescope-User-Manual
   It recommends exposure 15-60 seconds, gain 60-80, Astro for clusters/galaxies
   and Duo-Band for emission nebulae. `app/data/rig_profiles.py:302` now records
   these capabilities and documents gain 60 as an application-selected starting
   value. Fifteen seconds is the lower endpoint selected by application policy,
   not a unique factory default or target-specific measured optimum.
2. Category fallback omitted an emission filter when sky brightness did not
   activate a later condition rule. `imaging_settings_service.py:392` now seeds
   a category-appropriate filter only if the rig records it. Regression tests
   cover both Bortle 3 and 7, Mini and DWARF 3, clusters and emission nebulae.
3. Repeated identical Moon computations dominated much of the local incident
   profile. `calculation_cache.py:10` scopes exact reuse to one calculation and
   clears it on exceptions. The reviewer checked time offsets/DST fold, complete
   observatory identity, positional/keyword canonicalization and mutable-return
   handling. Two 55-candidate real-astronomy tests compare complete planner and
   scheduler outputs with reuse disabled and enabled: exact equality.

## Privacy and failure behavior

No blocking concurrency/privacy findings. Timing labels are literals, identifiers
are generated per request, and no arguments, accounts or tokens are recorded.
No cross-request astronomy sharing occurs. Weather calls retain provider socket
timeouts, and the worker is joined before return. These socket timeouts are not
total wall deadlines. Added tests verify provider TimeoutError handling and
propagation/cleanup of unexpected worker failures.

## Validation and limits

Independent focused cache/settings review: 20 tests passed. Combined regression:
244 tests passed, 57 dependency/IERS/polar-observation warnings. Browser suite:
15 viewport/target-count layouts and partial/full recommendation labels passed.

Independent fixed-date profile, 50 candidates and 300 synthetic imported sessions:
warm planner 4.773/4.879 seconds before, 2.327/2.370 after. Profiling overhead is
included. The local IERS-failure experiment proves repeated attempts are possible,
but the supplied production excerpt contains no IERS warnings. Render CPU quota,
astronomy-network subtimings and the deployed performance improvement are not yet
measured. No production resolution is claimed and no deployment occurred.
