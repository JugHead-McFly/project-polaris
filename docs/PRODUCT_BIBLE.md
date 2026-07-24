# Polaris Product Bible

Last updated: 2026-07-23

## Purpose

This is the product source of truth for Polaris. It records customer evidence,
product decisions, roadmap priorities, beta scope, positioning, and deliberate
deferrals so the project does not rely on recollection or drift toward feature
accumulation.

Polaris's governing question is:

> Will this make Polaris the default app a smart-telescope user opens before an
> imaging session?

## Vision and mission

**Vision:** Make astrophotography planning feel like having an experienced,
trustworthy imaging partner beside the user.

**Mission:** Turn a user's real sky, equipment, available time, and own imaging
history into a clear, explainable answer to: “What should I do tonight?”

Polaris is an advisory product. It recommends and explains; the operator makes
the final decision and controls the equipment.

## Core product promise

Working promise:

> Spend less time deciding and more time capturing.

Working testable expression:

> In under 30 seconds, Polaris gives a smart-telescope user a short,
> explainable list of realistic imaging choices for tonight.

This is a hypothesis to validate, not public marketing copy or a performance
guarantee yet.

## Product principles

- Recommend instead of overwhelm.
- One tap beats five taps.
- Beginners succeed first.
- Explain every recommendation.
- Do not require astronomy knowledge for the main decision.
- Save users time every night.
- Separate image quality from integration progress.
- Use the user's own capture record when it improves the recommendation.
- Keep the operator in control.
- Do not build a feature solely because it is common in competing apps.

## Current product position

Polaris already has an advisory nightly recommendation, target scheduling,
weather/Moon/darkness context, capture-history ingestion, portfolio progress,
explainable Quality Scoring v2, observing history, and location planning.

The strongest strategic difference is the capture-to-next-plan loop:

1. Decide whether the night is worthwhile.
2. Recommend a target and capture window for the user's constraints.
3. Reuse settings proven in the user's capture history.
4. Import and preserve the resulting capture record.
5. Track integration progress separately from image quality.
6. Explain the best next quality improvement.
7. Improve future recommendations from accumulated evidence.

Steps 1–6 exist in substantial form. Persistent user imaging aims,
personalized integration goals, equipment calibration, and a fully adaptive
feedback loop remain roadmap work.

See [COMPETITIVE_LANDSCAPE.md](COMPETITIVE_LANDSCAPE.md) for evidence and
competitor context.

See [COMMERCIALIZATION_AND_ALPHA_PLAN.md](COMMERCIALIZATION_AND_ALPHA_PLAN.md)
for the honest business-assessment framework, web-first alpha plan,
productization requirements, and current cost guardrails.

## Customers to validate

These are working personas, not established facts. Discovery findings can
change or split them.

| Persona | Context | Primary job to be done | Product implication |
| --- | --- | --- | --- |
| Beginner Bob | Dwarf 3 owner, new to target choice, easily discouraged | Start a worthwhile capture with confidence | Clear recommendation, plain-language reasons, few decisions |
| Intermediate Ian | Uses smart telescope regularly and may own more than one scope | Use limited clear time efficiently | Reliable windows, integration context, known-good settings |
| Expert Emma | Comfortable with advanced processing and images often | Save planning time without losing control | Fast, inspectable rationale and accurate constraints |

The initial public research should include Dwarf 3, Seestar, Vespera, and other
smart-telescope users; Polaris must not assume one device's needs represent the
whole market.

## Near-term milestone strategy

### Private alpha — working target: October 1, 2026

Goal: 10–20 trusted users. The primary question is:

> Would these users be disappointed if Polaris disappeared?

The alpha should prove the core nightly decision, not present a finished app.

Minimum experience to validate:

- A short list of realistic target recommendations.
- A personalized nightly rating or go/no-go decision.
- Recommended capture window.
- Plain-language explanation of why a target is recommended or deferred.
- A durable session/capture record that supports the next recommendation.

### Closed beta — target range: 100–300 users

Expand only after the alpha identifies repeatable value. Collect crash reports,
usage behavior, retention, actual feature use, and reasons users stop relying
on the recommendation.

### Public launch

Launch after evidence shows what users repeatedly use and trust—not merely
after feature count reaches an arbitrary threshold.

## Workstreams

| Workstream | Goal | Current status |
| --- | --- | --- |
| Voice of Customer | Learn user problems and language | Starting with the 14-day sprint |
| Product Bible | Maintain product source of truth | Active |
| Competitive intelligence | Track capabilities, reviews, pricing, and complaints | Initial review complete; recurring research pending |
| Beta program | Recruit, support, and learn from testers | Future after discovery |
| Marketing engine | Build trust and audience before launch | Future; public build journal later |
| Metrics | Measure activation, use, retention, and trust | Define during alpha preparation |
| Partnerships | Evaluate clubs, creators, and platform relationships | Future |
| Monetization | Validate willingness to pay after value is proven | Future |

## Voice of Customer protocol

Use the staged questions in [CUSTOMER_DISCOVERY_SPRINT.md](CUSTOMER_DISCOVERY_SPRINT.md).
For each observation, record user type, telescope, the problem, current
workaround, frequency, severity, requested solution, beta interest, voluntary
willingness-to-pay signal, and critical-path impact.

Evidence has more weight than feature requests. Quotes such as “I need this,”
“I'd buy that,” “Take my money,” and “I've always wanted this” are excitement
signals; log them with the surrounding problem and user context.

## Polaris Score

Score each proposed feature or problem from 0–10 in six dimensions:

| Dimension | Question |
| --- | --- |
| Demand | How many users independently raised it? |
| Pain | How severe is the problem? |
| Frequency | How often does it occur? |
| Mission fit | Does it improve the nightly imaging decision? |
| Feasibility | Can Polaris deliver it safely and credibly in the current stage? |
| Wow | Would it meaningfully improve trust, delight, or word of mouth? |

The total is out of 60. A score of 50 or more is a strong beta candidate,
subject to the minimum-beta scope and technical/safety review. Lower scores are
not rejections by default; they are parked until evidence changes.

## Feature-decision buckets

| Bucket | Meaning |
| --- | --- |
| Must Build | Without it, the core beta promise fails or users are predictably disappointed. |
| Should Build | Clear value, but not essential to validate the alpha. |
| Nice to Have | Worth revisiting after core value is proven. |
| Don't Build | Interesting but outside the mission or harmful to focus. |
| Parking Lot | Intentionally deferred pending evidence, timing, or capacity. |

## Current deliberate deferrals

Until discovery or alpha evidence changes the decision, defer:

- Social features and community galleries.
- Achievement badges.
- Advanced processing workflow.
- Complex equipment-management breadth.
- Extensive visual customization.
- Broad integrations with every astronomy platform.
- Feature requests unrelated to deciding what to image tonight.

Do not promise artificial intelligence, a paid plan, an App Store date, or an
official relationship with DwarfLab during early customer research.

## Decision log

| Date | Decision | Why |
| --- | --- | --- |
| 2026-07-23 | Run customer discovery before expanding beta scope | Avoid feature-driven development without evidence |
| 2026-07-23 | Treat October 1 as a private-alpha target, not a public launch promise | Create urgency while preserving room to learn |
| 2026-07-23 | Keep Polaris advisory and user-controlled | Safety, trust, and current product boundary |
| 2026-07-23 | Do not ask communities to select names, logos, or colors during discovery | Prevent leading questions and preserve focus on real pain |
| 2026-07-23 | Pursue a web-first alpha before native mobile distribution | Validate the core decision workflow with faster iteration and less platform overhead |

## Weekly product review

Every week:

1. Review new customer feedback and excitement signals.
2. Update the Voice of Customer record.
3. Score new problems and ideas with the Polaris Score.
4. Re-rank roadmap items and confirm the next highest-value beta action.
5. Place deliberately deferred ideas in the Parking Lot.
6. Check whether current work moves Polaris toward the private-alpha target.
7. Record decisions and their supporting evidence here.
