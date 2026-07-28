# Polaris Roadmap to Private Alpha and Beta

Last updated: 2026-07-28

## How to read this plan

Polaris has a working **v1.6.0 local product checkpoint** and is now building
the **v1.8 hosted nightly loop**. The v1.7 hosted foundation has passed its
account-isolation, deployment, monitoring, backup, and recovery gates. A
version number records product milestones; it does not by itself mean the
product is ready for a public market.

Doug's expected development cadence is about **10–14 focused hours per week**.
The dates below are planning ranges, not promises. The roadmap protects the
central product rule: help a smart-telescope user spend less time figuring out
what to do and more time under the sky.

## High-level path

| Milestone | Working window | Main outcome | Exit test |
| --- | --- | --- | --- |
| **v1.6 — Local product closeout** | Now–early August | Finish and document the local single-user workflow; validate with real captures | Doug can reliably plan, capture, ingest, review, and improve a session without manual database work |
| **Discovery + alpha architecture** | Late July–early August (2 weeks, parallel) | Real user evidence and an intentional hosted-product design | Discovery findings are logged; one small alpha architecture is chosen in writing |
| **v1.7 — Alpha foundation** | Completed ahead of the original mid–late August window | Accounts, tenant boundaries, secure configuration, and a deployable baseline | Passed: two-user isolation, hosted deployment, monitoring, backup, and full recovery drill |
| **v1.8 — First hosted nightly loop** | Active; originally planned for late August–mid September | Phone-friendly onboarding plus tonight's recommendation, window, explanation, and usefulness response | A new user can onboard, receive a saved recommendation, and rate it without Doug's help |
| **v1.9 — Alpha reliability** | Mid–late September (2 weeks) | Feedback capture, support path, privacy basics, and repaired onboarding/recommendation failures | Doug and 2–3 trusted testers complete the core flow repeatedly without a critical issue |
| **v1.10 — Private alpha** | October–November (4–6 weeks) | 10–20 invited users using Polaris in real observing decisions | Returning use, understandable recommendations, and users who would miss Polaris if it went away |
| **v2.0 — Closed beta** | December 2026–February 2027 (6–10 weeks) | Carefully expand toward 100 users; measure retention and support load | Stable service, no unresolved privacy/security blocker, and repeatable evidence of value |
| **Public-launch decision** | After closed beta | Decide whether to launch, narrow the audience, extend beta, or stop | Decision is based on retention, trust, support burden, and willingness-to-pay evidence—not feature count |

## Plain-English map

These names are how we will talk about progress in session briefings. The
technical names remain useful in code and architecture discussions, but should
not be the primary way Doug has to carry the project in his head.

| What Polaris is becoming | Plain-English outcome | Where we are |
| --- | --- | --- |
| **Teach Polaris About the Sky** | It understands the location, weather, darkness, Moon, targets, and capture context that matter for a night of imaging. | Largely complete for the local single-observatory product. |
| **Teach Polaris to Make Smart Suggestions** | It weighs tradeoffs and explains a realistic target recommendation. | Largely complete locally; quality scoring and goal refinement remain active work. |
| **Help Users Plan Their Night** | It turns a recommendation into a practical imaging window and sequence. | Largely complete locally through Planner V3. |
| **Build Mission Control** | A person can see the meaningful state of their observing work in one understandable place. | Largely complete locally; v1.6 is closing the real capture-to-learning loop. |
| **Invite the First Explorers** | Real smart-telescope users try the hosted core workflow and teach us where it fails. | Next major product milestone: private alpha. |
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

### v1.6: finish the product we have

This is not a new feature race. Its job is to make the real local workflow
trustworthy and understandable:

- Finish the active Quality Scoring v2 and location-planning work.
- Continue real-capture ingest, image, quality, integration, and history tests.
- Resolve defects and confusing language discovered during use.
- Keep the release/backup path proven.

**Guardrail:** a feature enters v1.6 only when it makes the nightly decision,
capture learning loop, or trustworthy local operation materially better.

### Discovery and alpha architecture: decide before building

Run the 14-day smart-telescope discovery sprint while closing v1.6. Capture
specific problems, current workarounds, frequency, and interest in testing.
At the same time, audit the current FastAPI/SQLite app for safe reuse.

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
and advisory timeline. Recommendation runs are now saved with tenant ownership
and privacy-safe planning provenance, and the user can record a simple Yes/No
usefulness response. Automated checks cover persistence and cross-user
isolation. The remaining exit work is a hosted manual acceptance test after
deployment, followed by first-tester onboarding and comprehension feedback.

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

The October private-alpha date is a useful forcing function, not a promise.
Reduce alpha scope or delay it if reliability, privacy, or user comprehension
is not ready. The target is not a large company on a deadline; it is credible
evidence that Polaris reduces planning friction for real users.
