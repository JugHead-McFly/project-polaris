"""Conservative sampled windows for an explicitly complete obstruction survey."""
import math
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from app.core.obstruction_profile import ObstructionProfile


PROFILE_SAMPLE_MINUTES = 1
MAXIMUM_AZIMUTH_STEP_DEGREES = 5.0
HorizontalPosition = Optional[Tuple[float, float]]  # azimuth, altitude; unrounded


def _valid(position: HorizontalPosition) -> bool:
    return (position is not None and len(position) == 2
            and all(math.isfinite(value) for value in position)
            and 0 <= position[0] < 360 and -90 <= position[1] <= 90)


def interval_exclusion_reason(
    profile: ObstructionProfile,
    start: HorizontalPosition,
    end: HorizontalPosition,
    minimum_altitude: float,
) -> Optional[str]:
    """Check a swept angular box, not just endpoints; no continuous-path guarantee."""
    if not _valid(start) or not _valid(end):
        return "Position unavailable"
    azimuth, altitude = start
    end_azimuth, end_altitude = end
    low_altitude, high_altitude = sorted((altitude, end_altitude))
    if low_altitude < minimum_altitude:
        return "Below the minimum imaging altitude"
    step = (end_azimuth - azimuth + 180) % 360 - 180
    if abs(step) > MAXIMUM_AZIMUTH_STEP_DEGREES:
        return "Direction changes too quickly for obstruction sampling"
    arc_start = azimuth if step >= 0 else end_azimuth
    arc_width = abs(step)

    def in_arc(value):
        return (value - arc_start) % 360 <= arc_width

    horizon_ceiling = max(
        profile.horizon_altitude(azimuth),
        profile.horizon_altitude(end_azimuth),
        *(point.altitude_degrees for point in profile.horizon if in_arc(point.azimuth_degrees)),
    )
    if low_altitude <= horizon_ceiling + profile.clearance_degrees:
        return "Local horizon obstruction or clearance margin"
    for sector in profile.sectors:
        direction_overlap = (sector.contains_azimuth(azimuth)
                             or sector.contains_azimuth(end_azimuth)
                             or in_arc(sector.start_azimuth_degrees)
                             or in_arc(sector.end_azimuth_degrees))
        if (direction_overlap
                and high_altitude >= sector.minimum_altitude_degrees - profile.clearance_degrees
                and low_altitude <= sector.maximum_altitude_degrees + profile.clearance_degrees):
            return "Overhead/sector obstruction or clearance margin"
    return None


def profile_sample_times(start: datetime, end: datetime):
    """Whole-minute UTC grid avoids rounding a schedule into a blocked interval."""
    if start.utcoffset() is None or end.utcoffset() is None:
        raise ValueError("Obstruction planning requires timezone-aware datetimes")
    cursor = start.astimezone(timezone.utc)
    if cursor.second or cursor.microsecond:
        cursor = cursor.replace(second=0, microsecond=0) + timedelta(minutes=1)
    end = end.astimezone(timezone.utc).replace(second=0, microsecond=0)
    times = []
    while cursor <= end:
        times.append(cursor.astimezone(start.tzinfo))
        cursor += timedelta(minutes=PROFILE_SAMPLE_MINUTES)
    return times


def evaluate_profile_visibility(profile, times, positions, minimum_altitude):
    """Keep disjoint windows separate; recommend only the longest complete run."""
    if len(times) != len(positions):
        raise ValueError("Each obstruction sample requires a position or explicit None")
    if any(at.utcoffset() is None for at in times):
        raise ValueError("Obstruction samples require timezone-aware datetimes")
    if any(not timedelta(0) < right.astimezone(timezone.utc) - left.astimezone(timezone.utc)
           <= timedelta(minutes=PROFILE_SAMPLE_MINUTES)
           for left, right in zip(times, times[1:])):
        raise ValueError("Obstruction samples must increase with no missing intervals")
    reasons = set()
    windows = []
    run_start = None
    # Existing schedule labels cannot disambiguate a repeated DST hour. Fail closed.
    offset_change = len({at.utcoffset() for at in times}) > 1
    ambiguous_time = any(at.replace(fold=0).utcoffset() != at.replace(fold=1).utcoffset()
                         for at in times)
    for index in range(max(0, len(times) - 1)):
        reason = ("Timezone offset transition is unsupported for obstruction schedules"
                  if offset_change else
                  "Ambiguous local time is unsupported for obstruction schedules"
                  if ambiguous_time else interval_exclusion_reason(
                      profile, positions[index], positions[index + 1], minimum_altitude))
        if reason is None:
            if run_start is None:
                run_start = times[index]
        else:
            reasons.add(reason)
            if run_start is not None:
                windows.append((run_start, times[index]))
                run_start = None
    if run_start is not None:
        windows.append((run_start, times[-1]))
    if len(times) < 2:
        reasons.add("No complete obstruction sampling interval")
    return windows, sorted(reasons)
