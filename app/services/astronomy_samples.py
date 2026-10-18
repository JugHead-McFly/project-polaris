"""Exact threshold samples shared by scalar and batched visibility paths."""
from datetime import timedelta, timezone


def threshold_refinement_times(times, altitudes, minimum_altitude):
    for left, right, low, high in zip(times, times[1:], altitudes, altitudes[1:]):
        if (low >= minimum_altitude) == (high >= minimum_altitude):
            continue
        at = left.astimezone(timezone.utc) + timedelta(minutes=1)
        while at < right.astimezone(timezone.utc):
            yield at.astimezone(left.tzinfo)
            at += timedelta(minutes=1)
