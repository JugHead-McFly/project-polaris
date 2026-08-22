# NASA-informed target-art provenance

Last reviewed: 2026-08-22

Polaris generates its own lightweight vector target artwork. The vectors are
Polaris output; they are not NASA images and must not be presented as created,
reviewed, approved, or endorsed by NASA.

The background target-art cache retains the factual NASA source record used to
inform each supported target profile: NASA asset ID, source URL, title, source
label, published credit, media-usage URL, lookup timestamp, expiry, and selected
artwork profile. The user-facing target cards do not display source or
attribution labels. This internal record supports provenance review without
visually attributing the generated vector to NASA.

The resolver must continue to:

- reject candidates carrying a third-party copyright notice;
- keep NASA network access outside the user-request path;
- preserve stale and generic/category fallbacks;
- avoid NASA insignia, logotype, seals, and endorsement language; and
- attribute generated output to Polaris internally, not NASA.

Policy basis: NASA's current Images and Media Usage Guidelines state that NASA
content generally may be used factually for educational or informational
purposes with NASA acknowledged as its source, that third-party-marked material
does not convey reuse rights, and that generated-model output must be attributed
to the product rather than NASA. Review the current guidance before materially
changing how NASA source material is used:

- https://www.nasa.gov/nasa-brand-center/images-and-media/
- https://images.nasa.gov/docs/images.nasa.gov_api_docs.pdf
