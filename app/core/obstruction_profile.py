"""Validated immutable obstruction geometry; not a photographic calibration."""
from bisect import bisect_right
from typing import Annotated, Tuple

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator


Azimuth = Annotated[float, Field(strict=True, ge=0, lt=360, allow_inf_nan=False)]
Altitude = Annotated[float, Field(strict=True, ge=0, le=90, allow_inf_nan=False)]


class _Geometry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class HorizonPoint(_Geometry):
    azimuth_degrees: Azimuth
    altitude_degrees: Altitude


class ObstructionSector(_Geometry):
    """Clockwise inclusive sector, with a bounded vertical extent (e.g. a roof)."""

    start_azimuth_degrees: Azimuth
    end_azimuth_degrees: Azimuth
    minimum_altitude_degrees: Altitude
    maximum_altitude_degrees: Altitude

    @model_validator(mode="after")
    def ordered_bounds(self):
        if self.start_azimuth_degrees == self.end_azimuth_degrees:
            raise ValueError("Sector endpoints must differ; split full-circle roofs into sectors")
        if self.minimum_altitude_degrees >= self.maximum_altitude_degrees:
            raise ValueError("Sector minimum altitude must be below maximum altitude")
        return self

    def contains_azimuth(self, azimuth: float) -> bool:
        return ((azimuth - self.start_azimuth_degrees) % 360
                <= (self.end_azimuth_degrees - self.start_azimuth_degrees) % 360)


class ObstructionProfile(_Geometry):
    # Required explicit assertion: partial surveys are not treated as clear sky.
    complete_coverage: StrictBool
    horizon: Annotated[Tuple[HorizonPoint, ...], Field(min_length=2, max_length=720)]
    sectors: Annotated[Tuple[ObstructionSector, ...], Field(max_length=64)] = ()
    clearance_degrees: Annotated[
        float, Field(strict=True, ge=0, le=10, allow_inf_nan=False)
    ] = 1.0

    @model_validator(mode="after")
    def complete_ordered_horizon(self):
        if not self.complete_coverage:
            raise ValueError("Partial/unknown directional coverage is unsupported")
        azimuths = [point.azimuth_degrees for point in self.horizon]
        if any(left >= right for left, right in zip(azimuths, azimuths[1:])):
            raise ValueError("Horizon azimuths must be unique and strictly increasing")
        return self

    def horizon_altitude(self, azimuth: float) -> float:
        """Linear interpolation including the last-to-first segment across north."""
        azimuth %= 360
        index = bisect_right([point.azimuth_degrees for point in self.horizon], azimuth)
        left = self.horizon[index - 1]
        right = self.horizon[index % len(self.horizon)]
        span = (right.azimuth_degrees - left.azimuth_degrees) % 360
        fraction = ((azimuth - left.azimuth_degrees) % 360) / span
        return left.altitude_degrees + fraction * (right.altitude_degrees - left.altitude_degrees)
