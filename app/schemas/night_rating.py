from pydantic import BaseModel, Field


class NightRatingDeduction(BaseModel):
    label: str
    points: float


class NightRating(BaseModel):
    score: int
    quality: str
    deductions: list[NightRatingDeduction] = Field(default_factory=list)
