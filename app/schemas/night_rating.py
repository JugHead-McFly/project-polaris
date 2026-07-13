from pydantic import BaseModel


class NightRating(BaseModel):
    score: int
    quality: str