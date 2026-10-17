"""Advisory framing metadata; this does not design or execute a mosaic."""

MOSAIC_NOTE = (
    "Mosaic required: target exceeds this rig's single-frame field of view. "
    "This is a visibility opportunity only. Confirm panel layout, overlap, "
    "per-panel exposure and integration, and setup time manually in the telescope app. "
    "Polaris has not calculated a mosaic capture sequence or completion time."
)


def mosaic_advice(advisor):
    return {**advisor, "recommended_sub_exposure_seconds": None,
            "recommended_gain": None, "recommended_filter": None,
            "additional_subframes_needed": None, "recommendation_source": "manual_mosaic",
            "settings_confidence": "Manual mosaic planning required",
            "settings_reasons": [MOSAIC_NOTE], "settings_setup_guidance": [MOSAIC_NOTE],
            "settings_adjustments": [], "recommendation": MOSAIC_NOTE}
