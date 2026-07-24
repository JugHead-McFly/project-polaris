# Polaris Roadmap to Private Alpha and Beta

Last updated: 2026-07-23

## How to read this plan

Polaris is currently **v1.6.0 in development**: a working local, single-
observatory advisory product. A version number records product milestones; it
does not by itself mean the product is ready for a public market.

Doug's expected development cadence is about **10–14 focused hours per week**.
The dates below are planning ranges, not promises. The roadmap protects the
central product rule: help a smart-telescope user spend less time figuring out
what to do and more time under the sky.

## High-level path

| Milestone | Working window | Main outcome | Exit test |
| --- | --- | --- | --- |
| **v1.6 — Local product closeout** | Now–early August | Finish and document the local single-user workflow; validate with real captures | Doug can reliably plan, capture, ingest, review, and improve a session without manual database work |
| **Discovery + alpha architecture** | Late July–early August (2 weeks, parallel) | Real user evidence and an intentional hosted-product design | Discovery findings are logged; one small alpha architecture is chosen in writing |
| **v1.7 — Alpha foundation** | Mid–late August (2–3 weeks) | Accounts, tenant boundaries, secure configuration, and a deployable baseline | Two users cannot see or affect each other's data; backups and error monitoring are exercised |
| **v1.8 — First hosted nightly loop** | Late August–mid September (3 weeks) | Phone-friendly onboarding plus tonight's recommendation, window, and explanation | A new user can onboard and reach a credible recommendation without Doug's help |
| **v1.9 — Alpha reliability** | Mid–late September (2 weeks) | Feedback capture, support path, privacy basics, and repaired onboarding/recommendation failures | Doug and 2–3 trusted testers complete the core flow repeatedly without a critical issue |
| **v1.10 — Private alpha** | October–November (4–6 weeks) | 10–20 invited users using Polaris in real observing decisions | Returning use, understandable recommendations, and users who would miss Polaris if it went away |
| **v2.0 — Closed beta** | December 2026–February 2027 (6–10 weeks) | Carefully expand toward 100 users; measure retention and support load | Stable service, no unresolved privacy/security blocker, and repeatable evidence of value |
| **Public-launch decision** | After closed beta | Decide whether to launch, narrow the audience, extend beta, or stop | Decision is based on retention, trust, support burden, and willingness-to-pay evidence—not feature count |

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

The outcome is an architecture decision record covering: user accounts,
observatory/data isolation, hosted database, capture/upload assumptions,
configuration/secrets, deployment, backup/recovery, monitoring, and the
minimal support path. Do not select a framework because it is fashionable.

### Alpha: prove one repeatable habit

The hosted alpha must do only a few things well:

1. Let a user set up an observing location and basic telescope context.
2. Give a plain-language tonight recommendation, ranked alternatives, and a
   usable window.
3. Explain why a target is recommended or deferred.
4. Let the user say whether the recommendation was useful.

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
