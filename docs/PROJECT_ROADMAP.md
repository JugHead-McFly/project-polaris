# Polaris Roadmap: Single-User First, Alpha Later

Last updated: 2026-08-30

## How to read this plan

Polaris has a working **v1.6.0 local product checkpoint** and a secure hosted
path that Doug can use as the single active operator. The v1.7 hosted
foundation has passed account-isolation, deployment, monitoring, backup, and
recovery gates. The v1.8 hosted nightly loop saves recommendations, collects
usefulness feedback, and has passed a clean-account onboarding and
data-isolation walkthrough. Those foundations are preserved, but external
alpha recruitment is deferred. Current development is Doug-first and does not
wait for tester participation, forecast sample counts, cohort evidence, clear
weather, or new imaging sessions. Existing captures and saved planning data
are the active development test beds during monsoon season. A version number
records product milestones; it does not by itself mean the product is ready
for a public market.

Doug's expected development cadence is about **10–14 focused hours per week**.
The dates below are planning ranges, not promises. The roadmap protects the
central product rule: help a smart-telescope user spend less time figuring out
what to do and more time under the sky.

## High-level path

| Milestone | Working window | Main outcome | Exit test |
| --- | --- | --- | --- |
| **v1.6 — Private-alpha onboarding checkpoint** | Complete as of Aug. 2 | First-time hosted setup, handoff, and safe `Do Not Image` explanation are understandable enough for the next invited tester | Passed: clean account saw setup first, reached Tonight, saw no Doug data, and understood cloud-driven `Do Not Image` |
| **v1.7 — Alpha foundation** | Complete | Accounts, tenant boundaries, secure configuration, deployment, monitoring, backup, and recovery | Passed: two-user isolation, hosted deployment, privacy-safe monitoring, tenant export, and full recovery drill |
| **v1.8 — Feedback + scoring foundation** | Foundation complete Aug. 2 | Preserve privacy-safe recommendation and usefulness history for Doug's own review now and possible external validation later | Passed internally: aggregate metrics, review focus, trust-oriented feedback prompts, and tenant isolation exist. Live-tester criteria are deferred rather than an active exit gate. |
| **v1.9 — Exposure and reliability logic** | Substantially complete by late August | Improve recommendation trust where weather, Moon, tracking mode, heat, rig limits, and 999-frame limits affect the actual plan | Doug sees conservative, explainable settings and no known critical planning or safety contradiction |
| **v1.10 — Opportunity Advisor UI + scoring investigation** | Complete Aug. 30 | Turn Tonight into a compact, at-a-glance opportunity card while validating score components before exposing them as product promises | Passed locally and hosted: Tonight explains the realistic opportunity, best target, fallback, score drivers, rig match, and forecast-history state without implying false certainty |
| **v1.11 — Single-User Nightly Intelligence** | Complete Aug. 31 | Improve recommendations from existing weather, forecast, rig, location, and capture evidence using repeatable historical and synthetic test beds | Passed: five existing-data nightly scenarios, explainable hard stops, full-cloud zero weather scoring, hosted bad-night guidance, and Render/local alignment |
| **v1.12 — Single-User Product Checkpoint** | Active | Consolidate the strongest nightly, portfolio, goal, quality, and location workflows into a dependable personal product | Polaris is useful and internally verified against existing data; neither outside participation nor additional imaging is required |
| **v1.13 — Optional private-alpha reconsideration** | Future; only after Doug explicitly chooses to resume it | Decide whether a small external cohort would answer a question that single-user use cannot answer | A written go/no-go decision names the exact question, support burden, privacy gate, and smallest useful cohort before any invitation is sent |
| **v2.0 — Closed beta decision** | Only after a later alpha produces useful evidence | Decide whether to expand, narrow scope, extend validation, or keep Polaris personal | Decision is based on observed value, trust, support burden, and willingness-to-pay evidence, not feature count |
| **Public-launch decision** | Future | Decide whether to launch, narrow the audience, extend beta, or stop | Launch only when repeat use and trust are proven by behavior |

## Plain-English map

These names are how we will talk about progress in session briefings. The
technical names remain useful in code and architecture discussions, but should
not be the primary way Doug has to carry the project in his head.

| What Polaris is becoming | Plain-English outcome | Where we are |
| --- | --- | --- |
| **Teach Polaris About the Sky** | It understands the location, weather, darkness, Moon, targets, and capture context that matter for a night of imaging. | Largely complete for the local single-observatory product. |
| **Teach Polaris to Make Smart Suggestions** | It weighs tradeoffs and explains a realistic target recommendation. | Largely complete locally; quality scoring and goal refinement remain active work. |
| **Help Users Plan Their Night** | It turns a recommendation into a practical imaging window and sequence. | Largely complete locally through Planner V3. |
| **Build Mission Control** | A person can see the meaningful state of their observing work in one understandable place. | Largely complete locally; the hosted single-user product now carries the Tonight loop. |
| **Deepen the Personal Product** | Existing captures and saved planning evidence make recommendations, goals, quality guidance, and planning more useful over time. | Active in v1.12; this is the current product-development focus. |
| **Invite the First Explorers** | Real smart-telescope users try the hosted core workflow and teach us what single-user use cannot. | Deferred until v1.13 and only resumed by an explicit decision from Doug. |
| **Launch Polaris** | A public product earns continued investment through repeat use and trust. | Future; only after alpha and closed-beta evidence. |

## Business workstream - parallel, not a delay

Product development is one lane. Naming, a domain, a landing page, launch
materials, and legal/business preparation run alongside it, but they do not
justify delaying a trustworthy core experience.

| Timing | Business work | Decision rule |
| --- | --- | --- |
| **Now** | Family naming review, customer discovery, product language, and a preliminary finalists screen. | Project Polaris stays the internal codename; no public brand claim yet. |
| **After a provisional finalist** | Preliminary web, app-store, domain, social-handle, and USPTO screen; reserve a suitable domain only after that check. | A creative shortlist is not availability clearance. |
| **Before external alpha** | Simple landing page, support contact, privacy/terms preparation, and a clear invitation/feedback process. | Obtain qualified legal review where a decision carries legal consequences. |
| **Before public launch** | Brand system, public site, store assets, pricing tests, documentation, and launch checklist. | Build only what beta evidence says is necessary. |

## What matters in each stage

### v1.6: private-alpha onboarding checkpoint

This checkpoint is effectively complete. Its job was to make the first hosted
visit understandable enough that a new tester can reach a credible Tonight
recommendation without Doug coaching the screen.

- The hosted setup screen now explains the one-time purpose in plain English.
- Browser location is presented as **Fill this in for me**.
- Manual latitude and longitude are labeled as approximate fallback fields.
- A one-time **You're ready for tonight** handoff appears after setup.
- A clean test account reached Tonight without seeing Doug's data.
- Cloud-driven `Do Not Image` now names cloud cover and shows a Very Poor
  night rating instead of appearing to blame only the Moon.

**Guardrail:** do not keep polishing onboarding in the abstract. Change it again
only when Doug's use, a deterministic scenario, or a future tester reveals a
specific problem.

### Hosted architecture foundation: preserve for later

Customer discovery may continue when useful, but it is not an active gate.
Capture specific problems, current workarounds, frequency, and interest when
evidence appears; do not wait for it before continuing the single-user roadmap.

The architecture decision is recorded in
[`ALPHA_ARCHITECTURE_DECISION.md`](ALPHA_ARCHITECTURE_DECISION.md). Polaris
will keep its FastAPI/Python core as a modular monolith, use Render for the web
service, and use Supabase for authentication and PostgreSQL. The first hosted
loop intentionally excludes raw FITS uploads and the local capture archive.
Single-user releases must preserve tenant-isolation, backup, recovery, and
monitoring checks. Reassess cost and external-user assumptions only if external
alpha is later resumed.

### Single-user development: prove one repeatable habit

The hosted single-user product must do only a few things well:

1. Let a user set up an observing location and basic telescope context.
2. Give a plain-language tonight recommendation, ranked alternatives, and a
   usable window.
3. Explain why a target is recommended or deferred.
4. Let the user say whether the recommendation was useful.
5. Choose sub-exposure and frame count together from the target, filter, Moon
   and sky brightness, tracking risk, temperature, prior capture quality, usable
   window, and selected telescope's limits. For DWARF devices, prefer a safe
   exposure that can use the window within the 999-frame limit or split the work
   into multiple clearly labeled capture blocks.
6. Do not lengthen a DWARF exposure past 15 seconds merely to avoid the
   999-frame limit unless equatorial tracking is explicitly enabled or
   successful capture history proves the longer setting worked. Add telescope
   model and tracking-mode selection before enabling this automatically for new
   users.
7. Make selected-rig reasoning visible in Tonight. A user should see why the
   recommended target is or is not a good match for their rig, including field
   of view, target scale, filter fit, smart-telescope workflow fit, and any
   unknown official-spec gaps such as incomplete DWARF mini framing data.
8. Move the Tonight presentation toward an opportunity-advisor layout: large
   score/label, best window, best target, fallback target, score drivers, and a
   bottom-line "what to do" recommendation. Use current data first; do not
   present new scoring math as calibrated until it has been compared against
   known historical outcomes and repeatable test-bed scenarios.
9. Build forecast trust from evidence rather than claims. Save one minimal,
   tenant-isolated forecast check per observing home and forecast hour, match
   only later provider readings near that hour, expire missed checks, retain 90
   days, and show only a building-history state until calibration is justified.

The v1.7 foundation is complete: two real accounts were isolated successfully,
the hosted application was deployed, Sentry monitoring and privacy scrubbing
were exercised, and a backup was restored into a separate Supabase project.
The restored account, observatory, Row Level Security boundary, and planning
flow all passed the recovery drill.

The completed v1.8 browser foundation resolves the signed-in user's observing
home and uses its coordinates and timezone through weather, darkness, Moon,
target-visibility, moving-object, and schedule calculations. Hosted planning
uses catalog defaults rather than Doug's local capture history. The signed-in
browser presents a phone-friendly recommendation, target settings, conditions,
and advisory timeline. Recommendation runs are saved with tenant ownership and
privacy-safe planning provenance, and the user can record a simple Yes/No
usefulness response. Automated checks cover persistence and cross-user
isolation. External cohort analysis is deferred. During v1.12, existing saved
plans, captures, feedback, forecast checks, and deterministic scenarios support
Doug's own review without becoming a reason to pause development.

Advanced portfolio, quality, locations, and image-processing work may proceed
when it materially improves Doug's single-user workflow. Native mobile,
subscriptions, a broad device matrix, and cohort operations remain optional
until a later product decision brings them into scope.

### Monsoon test-bed rule

V1.11 and V1.12 must not depend on additional imaging. During the current
monsoon period, development and validation use the data Polaris already has:

- the existing capture library and database, treated as read-only source data;
- saved hosted recommendations, feedback, and forecast-history rows;
- known historical planning outcomes and edge cases; and
- privacy-safe deterministic fixtures that reproduce clear, cloudy, Moon-heavy,
  tracking, rig-fit, timezone, frame-limit, and unavailable-data scenarios.

New captures and matched forecast observations are welcome when they occur, but
they are supplementary evidence, not milestone gates. See
[`EXISTING_DATA_TEST_BEDS.md`](EXISTING_DATA_TEST_BEDS.md) for the handling and
verification rules.

### Parked v1.10 follow-up backlog

- [ ] Expand the cached NASA-informed target-art catalog across common
  galaxies, nebulae, and clusters so popular targets resolve quickly. Preserve
  catalog-driven configuration, background-only refreshes, expiry and stale
  fallback behavior, official-source and credit metadata, accessible source
  links, rights-safe candidate selection, and category/generic artwork
  fallbacks.

## Weekly operating rhythm

At the beginning of each coding session, Polaris should state:

- Current version and milestone.
- The one outcome for the session.
- The next one or two tasks only.
- Expected time for that work.
- Any real blocker or decision required from Doug.

At the weekly review, examine results from the existing-data test beds and any
opportunistic real use, update available Voice of Customer evidence without
waiting for it, re-rank planned work with the Polaris Score, verify the roadmap,
and deliberately park ideas that do not help the current single-user exit test.

## Honest success measures

There is no active private-alpha date. The current success test is whether
Polaris produces stable, understandable, useful decisions across its existing
historical and synthetic test beds and improves Doug's personal workflow.
External alpha, clear weather, and new captures are not prerequisites for
continuing the product. If alpha resumes later, reliability, privacy, and user
comprehension remain hard gates before any invitation or expansion.
