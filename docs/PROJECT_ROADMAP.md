# Polaris Roadmap to Private Alpha and Beta

Last updated: 2026-08-20

## How to read this plan

Polaris has a working **v1.6.0 local product checkpoint** and a hosted private
alpha path that has passed its core onboarding retest. The v1.7 hosted
foundation has passed account-isolation, deployment, monitoring, backup, and
recovery gates. The v1.8 hosted nightly loop now saves recommendations,
collects usefulness feedback, and has passed a clean-account onboarding and
data-isolation walkthrough. A version number records product milestones; it
does not by itself mean the product is ready for a public market.

Doug's expected development cadence is about **10–14 focused hours per week**.
The dates below are planning ranges, not promises. The roadmap protects the
central product rule: help a smart-telescope user spend less time figuring out
what to do and more time under the sky.

## High-level path

| Milestone | Working window | Main outcome | Exit test |
| --- | --- | --- | --- |
| **v1.6 — Private-alpha onboarding checkpoint** | Complete as of Aug. 2 | First-time hosted setup, handoff, and safe `Do Not Image` explanation are understandable enough for the next invited tester | Passed: clean account saw setup first, reached Tonight, saw no Doug data, and understood cloud-driven `Do Not Image` |
| **v1.7 — Alpha foundation** | Complete | Accounts, tenant boundaries, secure configuration, deployment, monitoring, backup, and recovery | Passed: two-user isolation, hosted deployment, privacy-safe monitoring, tenant export, and full recovery drill |
| **v1.8 — Feedback + scoring loop** | Active; foundation complete Aug. 2 | Turn Yes/No feedback and first-tester observations into a simple alpha learning loop | Passed internally: aggregate metrics, review focus, and trust-oriented feedback prompts exist. Exit requires the live-tester criteria in `PRIVATE_ALPHA_TEST_PLAN.md`. |
| **v1.9 — Exposure and reliability logic** | Mid–late August | Improve recommendation trust where weather, Moon, tracking mode, heat, and 999-frame limits affect the actual plan | Testers see conservative, explainable settings and no critical planning/safety confusion repeats |
| **v1.10 — First private alpha cohort** | Late August–September | 2–5 invited users use Polaris for real observing decisions before any broader cohort | Returning use, understandable recommendations, and no unresolved privacy/security blocker |
| **v2.0 — Closed beta decision** | After alpha evidence, not before | Decide whether to expand toward 25–100 users, narrow scope, extend alpha, or pause | Decision is based on retention, trust, support burden, and willingness-to-pay evidence, not feature count |
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
| **Build Mission Control** | A person can see the meaningful state of their observing work in one understandable place. | Largely complete locally; hosted alpha now carries the first Tonight loop. |
| **Invite the First Explorers** | Real smart-telescope users try the hosted core workflow and teach us where it fails. | Ready for the next carefully invited tester; broaden only after repeat-use evidence. |
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
only when a tester gets stuck or misunderstands what Polaris saved and why.

### Discovery and alpha architecture: decide before building

Continue the smart-telescope discovery sprint while moving into V1.8. Capture
specific problems, current workarounds, frequency, and interest in testing.
Use those findings to decide what enters the feedback/scoring loop and what
stays parked.

The architecture decision is recorded in
[`ALPHA_ARCHITECTURE_DECISION.md`](ALPHA_ARCHITECTURE_DECISION.md). Polaris
will keep its FastAPI/Python core as a modular monolith, use Render for the web
service, and use Supabase for authentication and PostgreSQL. The first hosted
loop intentionally excludes raw FITS uploads and the local capture archive.
Implementation must still prove the decision's tenant-isolation, backup,
recovery, monitoring, and cost assumptions before external alpha access.

### Alpha: prove one repeatable habit

The hosted alpha must do only a few things well:

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

The v1.7 foundation is complete: two real accounts were isolated successfully,
the hosted application was deployed, Sentry monitoring and privacy scrubbing
were exercised, and a backup was restored into a separate Supabase project.
The restored account, observatory, Row Level Security boundary, and planning
flow all passed the recovery drill.

The active v1.8 browser slice resolves the signed-in user's observing home and
uses its coordinates and timezone through weather, darkness, Moon,
target-visibility, moving-object, and schedule calculations. Hosted planning
uses catalog defaults rather than Doug's local capture history. The signed-in
browser presents a phone-friendly recommendation, target settings, conditions,
and advisory timeline. Recommendation runs are saved with tenant ownership and
privacy-safe planning provenance, and the user can record a simple Yes/No
usefulness response. Automated checks cover persistence and cross-user
isolation. The next exit work is to make that feedback useful: a compact alpha
review loop that shows what testers did, whether they understood the plan, and
which product issue should be fixed next.

Advanced portfolio, quality, locations, image-processing, native mobile,
subscriptions, and a broad device matrix remain optional until user evidence
shows they are needed for repeat use.

## Weekly operating rhythm

At the beginning of each coding session, Polaris should state:

- Current version and milestone.
- The one outcome for the session.
- The next one or two tasks only.
- Expected time for that work.
- Any real blocker or decision required from Doug.

At the weekly review, update the Voice of Customer tracker, re-rank planned
work with the Polaris Score, verify the roadmap, and deliberately park ideas
that do not help the current exit test.

## Honest success measures

The private-alpha date is a useful forcing function, not a promise. Reduce
alpha scope or slow invitation pace if reliability, privacy, or user
comprehension is not ready. The target is not a large company on a deadline; it
is credible evidence that Polaris reduces planning friction for real users.
