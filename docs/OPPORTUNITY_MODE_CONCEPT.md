# Opportunity Mode: Post-Alpha Product Concept

Status: discovery concept — **not part of the live private alpha**

## The job to be done

When deep-sky imaging is not a good choice, a smart-telescope user should not
feel that Polaris has simply told them “no.” They should be able to see one
calm, honest suggestion for making useful use of the night—if one is genuinely
appropriate.

This comes from early community evidence, not a validated feature request. Some
observers use marginal nights for the Moon, planets, calibration frames,
equipment preparation, or target planning. Others explicitly advise beginners
not to over-plan or over-analyse. The design must respect both views.

## Product promise

**Polaris still gives one clear imaging recommendation first.** Opportunity
Mode is an optional, secondary card that appears only when it can offer a
credible alternative. It never implies that a weather or equipment warning is
safe to ignore.

Example:

> **Deep-sky imaging is not recommended tonight.**
> If you want a short astronomy task instead: review your next target window,
> prepare calibration frames indoors, or check whether the Moon/planet is a
> better fit for your actual conditions.

## What it could suggest

The first version should select **at most one** of these, with a one-sentence
reason:

| Situation | Optional suggestion | Guardrail |
| --- | --- | --- |
| Clouds, rain, unsafe wind, or unknown critical data | No outdoor imaging; plan, organize, or do indoor preparation | Never recommend opening equipment. |
| Clear enough for a short setup but weak deep-sky conditions | A Moon or planet suggestion when it is observable and suited to the telescope | Only after equipment-specific capability and safety rules are validated. |
| Deep-sky target blocked by Moon or poor timing | Review/save the next good target window | This is planning help, not a synthetic “good night.” |
| Calibration opportunity confirmed by the device workflow | Suggested calibration action | Do not invent a device procedure Polaris cannot verify. |
| No credible alternative | Nothing | Silence is better than a low-value task list. |

## What it must not become

- A second planner competing with Tonight’s primary recommendation.
- A generic astronomy content feed or a long checklist.
- A workaround for safety-related “Do Not Image” conditions.
- A claim that moonlight, weather, or calibration advice applies equally to
  every telescope and user.
- A replacement for the existing portfolio, target planning, or capture-import
  roadmap.

## Proposed user experience

1. Polaris shows its normal **Proceed**, **Use Caution**, or **Do Not Image**
   decision.
2. If a credible optional alternative exists, show a compact card below the
   decision: **“A useful alternative tonight.”**
3. The card contains a single action, a reason, and an optional `i` explanation.
4. The user may dismiss it. Polaris records only a simple helpful/not-helpful
   response, never pressure to take the suggestion.

Keep the primary screen skimmable: the default card should be shorter than the
current weather explanation, not another block of instructions.

## Validation before implementation

Ask private-alpha testers after they understand the core Tonight flow:

1. On a non-imaging night, would one optional alternative be useful or
   distracting?
2. Which alternative would they actually use: lunar/planetary, calibration,
   planning, or none?
3. Did the alternative make the main recommendation clearer or less clear?
4. Would they trust Polaris to distinguish an equipment-safety warning from a
   merely disappointing deep-sky night?

Build only if multiple testers independently say the card would help them act
without making the decision screen feel busier.

## Success measures

- Testers correctly repeat the primary safety/imaging decision.
- The optional card is considered helpful by more testers than distracting.
- No tester interprets it as permission to image in unsafe conditions.
- It reduces the “what can I do instead?” question without adding support load.

## Placement on the roadmap

This is a **v1.9/v1.10 candidate**, after the current alpha proves that people
can onboard, understand Tonight, and return for a second real decision. It is
not a commitment and should be dropped if the evidence favors a simpler core.

Evidence source: [VOICE_OF_CUSTOMER.md](VOICE_OF_CUSTOMER.md), entries dated
2026-07-29.
