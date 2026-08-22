"""Curated NASA lookup and vector-art profiles for supported targets.

Adding a target here is sufficient for the background cache refresher to
resolve official metadata and generate its lightweight Polaris artwork.  The
user-facing planning path never calls NASA or transforms remote media.
"""


NASA_TARGET_ART_CATALOG = {
    "M8": {
        "query": "Lagoon Nebula",
        "required_terms": ("lagoon",),
        "profile": "emission_nebula",
        "palette": ("#72d8c6", "#f0e4c5", "#315f63", "#d5a54d"),
    },
    "M13": {
        "query": "Hercules Cluster",
        "required_terms": ("hercules", "cluster"),
        "profile": "globular_cluster",
        "palette": ("#72d8c6", "#f0e4c5", "#315f63", "#d5a54d"),
    },
    "M16": {
        "query": "Eagle Nebula",
        "required_terms": ("eagle", "pillar"),
        "profile": "pillar_nebula",
        "palette": ("#72d8c6", "#f0e4c5", "#315f63", "#d5a54d"),
    },
    "M31": {
        "query": "M31 Andromeda Galaxy",
        "required_terms": ("andromeda",),
        "profile": "inclined_spiral",
        "palette": ("#72d8c6", "#f0e4c5", "#315f63", "#d5a54d"),
    },
    "M51": {
        "query": "M51",
        "required_terms": ("whirlpool",),
        "profile": "face_on_spiral_companion",
        "palette": ("#72d8c6", "#f0e4c5", "#315f63", "#d5a54d"),
        "official_source_url": "https://science.nasa.gov/asset/hubble/hubble-acs-visible-image-of-m51/",
        "source_label": "NASA Science · Hubble",
        "credit_override": "NASA, ESA, S. Beckwith (STScI), and the Hubble Heritage Team (STScI/AURA)",
    },
    "M57": {
        "query": "M57 Ring Nebula",
        "required_terms": ("ring", "nebula"),
        "profile": "ring_nebula",
        "palette": ("#72d8c6", "#f0e4c5", "#315f63", "#d5a54d"),
    },
}
