from pydantic import BaseModel


class DarknessSummary(BaseModel):
    sunset: str
    astronomical_darkness_start: str
    astronomical_darkness_end: str