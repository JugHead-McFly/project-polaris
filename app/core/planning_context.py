from dataclasses import dataclass
from typing import Optional

from app.core.observatory import DEFAULT_POSTAL_CODE
from app.core.observatory import ELEVATION_METERS
from app.core.observatory import LATITUDE
from app.core.observatory import LONGITUDE
from app.core.observatory import OBSERVATORY_NAME
from app.core.observatory import TIMEZONE


@dataclass(frozen=True)
class ObservatoryContext:
    """The observing home used for one complete planning calculation."""

    name: str
    latitude: float
    longitude: float
    timezone_name: str
    elevation_meters: float = 0.0
    postal_code: Optional[str] = None
    bortle_class: Optional[int] = None
    coordinates_are_approximate: bool = False


LOCAL_OBSERVATORY_CONTEXT = ObservatoryContext(
    name=OBSERVATORY_NAME,
    postal_code=DEFAULT_POSTAL_CODE,
    timezone_name=TIMEZONE,
    latitude=LATITUDE,
    longitude=LONGITUDE,
    elevation_meters=ELEVATION_METERS,
)


def use_observatory_context(
    context: Optional[ObservatoryContext],
) -> ObservatoryContext:
    return context or LOCAL_OBSERVATORY_CONTEXT
