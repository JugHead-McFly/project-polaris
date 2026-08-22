# Target opportunity scoring

Status: experimental foundation; not wired into live recommendations

This captures the next scoring direction from the private-alpha research
thread where Jd Stefaniak described using FITS/XISF SNR analysis, sensor
characteristics, Bortle class, filter, moonlight, field of view, focal length,
and exposure guidance to prioritize nightly imaging objects.

Doug had asked whether Polaris could start coding toward that logic. The first
implementation is intentionally separate from the production planner so the
current alpha recommendation remains stable while the scoring idea is tested.

## Current experimental inputs

The first local model scores a target opportunity from 0-100 using:

- maximum target altitude during the dark window;
- usable dark minutes;
- Moon illumination and Moon separation;
- Bortle class;
- whether the target fits the saved field of view, including whether it is
  comfortable, tight, oversized, or very small for the selected rig; and
- exposure-confidence signal.

It returns a plain-English quality label and a component breakdown. It does not
yet read raw FITS ADU values, sensor read noise, dark current, or filter
transmission. Those belong in a later calibrated exposure/SNR layer after we
confirm what data Polaris can measure reliably from Doug's captures and from
smart-telescope metadata.

The first rig-aware helper uses the selected rig's native field of view to feed
the scorer. This lets Polaris distinguish a comfortable framing opportunity
from a target that technically fits but will appear very small, or a target that
is too large for the selected smart telescope.

The rig comparison helper scores the same target opportunity across several
known rigs and returns the ranked results with each rig's field-of-view label.
This is the local foundation for future product questions like, "Is this a good
DWARF Mini target, or would it be better suited to a wider/narrower rig?"

## Product rule

Do not expose the formula as a promise. Polaris should explain the major
reasons behind a recommendation without implying scientific certainty or
equipment safety control.

## Beaconsfield-style scoring reference

A community prototype reviewed on 2026-08-22 appeared to use this 100-point
night-quality weighting:

- cloud and stability: 45 points;
- astronomical darkness: 20 points;
- Moon interference: 15 points;
- transparency: 10 points;
- seeing: 5 points; and
- target altitude: 5 points.

Treat these weights as a research input, not a Polaris formula. They are useful
because they make the score easy to explain at a glance. They are incomplete
for Polaris because they score the night more than the target. Polaris should
prefer a **target-specific opportunity score** where a difficult night can still
produce a practical recommendation for the right target, filter, window, and
rig.

Example product direction:

- overall night: 58/100, Challenging;
- C 20 with Duo-Band: 72/100, Usable;
- faint broadband galaxy: 39/100, Poor.

This prevents mediocre conditions from becoming a simplistic "no-go" when a
realistic narrowband or high-surface-brightness target is still worth trying.

## Candidate Polaris components

A Polaris-native opportunity score should investigate:

- weather and cloud reliability;
- usable darkness and window length;
- Moon impact by target type and filter;
- target altitude and geometry;
- rig field-of-view, target scale, exposure support, and frame limits;
- operational risks such as heat, wind, dew, and tracking mode; and
- source confidence, including missing weather or incomplete official rig data.

Separate blockers from reducers. Rain, unsafe wind, extreme heat, missing
critical weather, or no usable target window may block a recommendation.
Moonlight, mediocre transparency, short windows, light pollution, low-but-usable
altitude, or imperfect seeing should usually reduce or adapt the recommendation
instead of automatically stopping the user.

## Future path

1. Keep this scorer behind tests until the current alpha loop is stable.
2. Compare its output against the existing planner score on known nights.
3. Prototype the Tonight UI with an opportunity score label before exposing the
   score as a calibrated product promise.
4. Add calibrated sensor/exposure inputs only after the FITS data and equipment
   profile are dependable.
5. Wire it into the planner only when it improves explanation and trust without
   surprising existing recommendations.
