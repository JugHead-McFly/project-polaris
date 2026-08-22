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
        "palette": ("#75e3d8", "#ef8296", "#6d78b8", "#f5dfb0"),
    },
    "M13": {
        "query": "Hercules Cluster",
        "required_terms": ("hercules", "cluster"),
        "profile": "globular_cluster",
        "palette": ("#f6e7bd", "#8ce8dc", "#6b8db9", "#f2bd72"),
    },
    "M16": {
        "query": "Eagle Nebula",
        "required_terms": ("eagle", "pillar"),
        "profile": "pillar_nebula",
        "palette": ("#77dfd3", "#dc8f76", "#6c74a9", "#f3ddb0"),
    },
    "M31": {
        "query": "M31 Andromeda Galaxy",
        "required_terms": ("andromeda",),
        "profile": "inclined_spiral",
        "palette": ("#82e5d8", "#f1d9a4", "#6385af", "#d78391"),
    },
    "M51": {
        "query": "M51",
        "required_terms": ("whirlpool",),
        "profile": "face_on_spiral_companion",
        "palette": ("#8be9dc", "#f0d39b", "#6e9fd0", "#e48191"),
        "official_source_url": "https://science.nasa.gov/asset/hubble/hubble-acs-visible-image-of-m51/",
        "source_label": "NASA Science · Hubble",
        "credit_override": "NASA, ESA, S. Beckwith (STScI), and the Hubble Heritage Team (STScI/AURA)",
    },
    "M57": {
        "query": "M57 Ring Nebula",
        "required_terms": ("ring", "nebula"),
        "profile": "ring_nebula",
        "palette": ("#7ce3d5", "#e88c8d", "#6687bd", "#f3deb1"),
    },
}
