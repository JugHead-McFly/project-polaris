# Polaris Goal Engine

The Goal Engine replaces the former four-hour fallback with explainable starter
goals. It is a planning system, not a prediction of final image quality.

## Imaging aims

Each target receives three choices derived from the same Detailed baseline:

- **Quick** — half the Detailed time, intended for a first complete result and
  early processing review.
- **Detailed** — the default balanced project goal.
- **Showcase** — twice the Detailed time, intended to provide lower noise and
  more processing latitude.

Doubling integration does not double image quality. Stacking improves
signal-to-noise by combining registered frames, while photon noise follows a
square-root relationship. The aims therefore describe increasing investment,
not fixed quality grades.

## Detailed starter goals

| Target class | Starter goal | Planning rationale |
| --- | ---: | --- |
| Open cluster | 2 hr | Bright separated stars develop relatively quickly. |
| Globular cluster | 3 hr | The bright stellar core develops sooner than faint extended detail. |
| Planetary nebula | 5 hr | Bright structure appears early; faint outer shells need more time. |
| Emission/reflection nebula | 6 hr | Extended gas and dust benefit from sustained integration. |
| Galaxy | 8 hr | Faint arms, dust lanes, and outer structure need deeper integration. |
| Solar-system target | 1 hr | A session-style goal; sharp frames and seeing matter more than deep integration. |
| Transient target | 2 hr | A session-style goal for an object that changes position and appearance. |
| Uncategorized target | 4 hr | A conservative fallback when catalog classification is unavailable. |

Polaris applies only a small reviewed set of object-specific adjustments. Each
adjustment is returned by the API and shown under **Why this goal?**. Current
examples include the broad North America Nebula, compact Ring Nebula, faint Owl
Nebula, mixed Trifid Nebula, and bright central structure of Andromeda.

## Current boundaries

- Detailed is the active default. Quick and Showcase are visible guidance; a
  persistent user-selected aim is later work.
- The engine does not yet adjust hours for a saved equipment profile, Bortle
  class, Moon conditions, or measured capture quality.
- Image-quality scores remain separate. Reaching an integration goal never
  declares a blurry or otherwise weak image to be high quality.
- All hours are starter heuristics and are rounded to practical half-hour
  planning increments.

## Technical references

- [Siril: Signal to noise ratio](https://siril.org/tutorials/signal-to-noise/)
  explains why astrophotographers collect and stack many frames, and why shot
  noise follows the square root of signal.
- [Siril](https://siril.org/) describes stacking as a way to improve
  signal-to-noise by combining registered images.
- [NASA astrophotography guide](https://science.nasa.gov/wp-content/uploads/2023/09/Astrophotography_Guide.pdf)
  describes photon-counting noise and the square-root law.
- [DWARFLAB DWARF 3 specifications](https://dwarflab.com/en-eu/products/dwarf-3-smart-telescope)
  document the 35 mm aperture, IMX678 sensor, and built-in VIS, Astro, and
  dual-band filters used by the current installation.
