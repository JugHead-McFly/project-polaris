def build_night_plan(
    recommended_target,
    backup_target,
    darkness,
    weather,
):
    observing_rating = weather.get(
        "observing_rating",
        1,
    )

    if observing_rating >= 4:
        decision = "Proceed"
    elif observing_rating == 3:
        decision = "Use Caution"
    else:
        decision = "Do Not Image"

    target_sequence = []
    notes = []
    backup_option = None

    clouds = weather.get(
        "cloud_cover_percent"
    )

    if clouds is not None and clouds > 50:
        notes.append(
            "Cloud cover may significantly reduce "
            "imaging quality."
        )

    if decision != "Do Not Image":
        if recommended_target:
            target_sequence.append(
                {
                    "object": (
                        recommended_target["object"]
                    ),
                    "start": (
                        recommended_target[
                            "recommended_start"
                        ]
                    ),
                    "end": (
                        recommended_target[
                            "recommended_end"
                        ]
                    ),
                    "reason": (
                        recommended_target[
                            "next_action"
                        ]
                    ),
                }
            )

            if not recommended_target[
                "observable"
            ]:
                notes.append(
                    f'{recommended_target["object"]} '
                    "is currently below the minimum "
                    "imaging altitude."
                )

            moon_warning = (
                recommended_target.get(
                    "moon_warning"
                )
            )

            if (
                moon_warning
                and not moon_warning.startswith(
                    "None"
                )
                and not moon_warning.startswith(
                    "Minimal"
                )
            ):
                notes.append(
                    moon_warning
                )

        if backup_target:
            backup_option = {
                "object": (
                    backup_target["object"]
                ),
                "start": (
                    backup_target[
                        "recommended_start"
                    ]
                ),
                "end": (
                    backup_target[
                        "recommended_end"
                    ]
                ),
                "reason": (
                    backup_target[
                        "next_action"
                    ]
                ),
            }

    else:
        notes.append(
            "No imaging schedule was generated "
            "because conditions are unsuitable."
        )

    return {
        "decision": decision,
        "overall_rating": observing_rating,
        "start_imaging": darkness[
            "astronomical_darkness_start"
        ],
        "shutdown_time": darkness[
            "astronomical_darkness_end"
        ],
        "target_sequence": target_sequence,
        "backup_option": backup_option,
        "notes": notes,
    }