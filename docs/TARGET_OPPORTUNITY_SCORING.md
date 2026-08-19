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

## Future path

1. Keep this scorer behind tests until the current alpha loop is stable.
2. Compare its output against the existing planner score on known nights.
3. Add calibrated sensor/exposure inputs only after the FITS data and equipment
   profile are dependable.
4. Wire it into the planner only when it improves explanation and trust without
   surprising existing recommendations.
