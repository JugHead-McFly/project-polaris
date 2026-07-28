# C20 sub-exposure validation plan

## Decision to validate

Polaris currently recommends **15-second sub-exposures**, gain 60, and the
Duo-Band filter for C20 (the North America Nebula). The recommendation is based
on Doug's best available C20 capture history, rather than a generic rule.

It should not automatically move to 30-second sub-exposures until a comparable
capture test shows that the longer exposure is at least as good technically.

## Current evidence

| Capture date | Sub-exposure | Gain | Filter | Frames | Quality score |
| --- | ---: | ---: | --- | ---: | ---: |
| Jun 4, 2026 | 15 sec | 60 | Duo-Band | 272 | 93/100 |
| Jul 20, 2026 | 15 sec | 60 | Duo-Band | 156 | 61/100 |
| Jul 27, 2026 | 15 sec | 60 | Duo-Band | 994 | 92/100 |
| Jul 27, 2026 | 15 sec | 60 | Duo-Band | 282 | 89/100 |

There is no comparable 30-second C20 capture in the library. The 15-second
choice is therefore proven for this observatory; 30 seconds is a hypothesis to
test, not a better setting by default.

## Why test 30 seconds

For a long usable target window, 30-second sub-exposures would reduce the frame
count by about half. A planned 1,644-frame 15-second session would become about
822 frames at 30 seconds, which fits within DWARF's 999-frame single-run limit.

The tradeoff is that longer exposures can brighten the sky background, clip
bright stars, amplify tracking drift, and make wind movement more visible. The
test must establish whether those risks are acceptable at this site and with
this equipment.

## First controlled test

Use a clear night with C20 high enough to image. Keep these items the same for
both test blocks:

- target: C20;
- filter: Duo-Band;
- gain: 60;
- framing, focus, and telescope position;
- no charging or major equipment changes during either block.

Capture two back-to-back blocks:

| Block | Setting | Minimum useful sample |
| --- | --- | --- |
| A | 15 sec, gain 60, Duo-Band | 20–30 minutes |
| B | 30 sec, gain 60, Duo-Band | 20–30 minutes |

If wind rises, clouds arrive, focus changes, or the target approaches the
horizon during one block, label that block inconclusive and repeat on another
night. Do not treat a prettier on-screen preview as proof by itself.

## How Polaris should compare the result

After both sessions are imported, compare each capture's:

1. quality score and its component details;
2. star shape and trailing indicators;
3. background level, variation, and highlight clipping;
4. amount of usable integration collected per minute of real observing time;
5. whether either setting creates an avoidable DWARF frame-limit split.

## Decision rule

Keep 15 seconds as the recommendation unless 30 seconds produces comparable or
better technical quality across at least two reasonably matched tests. If it
does, update the C20 equipment guidance to 30 seconds and explain that the
choice both preserves image quality and fits a typical long window within one
DWARF run. If results are mixed, retain 15 seconds and let Polaris split the
schedule into clearly labeled runs of no more than 999 frames.

## Product follow-up

Future Polaris settings logic should select exposure time and run count
together, using target, filter, Moon/sky brightness, wind/tracking risk,
temperature, user equipment, proven capture history, usable window, and the
DWARF 999-frame limit. This plan provides the first real C20 evidence needed
for that rule.
