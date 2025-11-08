from pydantic import BaseModel, Field
from typing import List
from datetime import date

class RoundInfo(BaseModel):
    round_number: int
    type: str  # aptitude, technical, dsa_coding, system_design, hr
    duration: int = 60  # minutes

class PlacementProfileCreate(BaseModel):
    company_name: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    interview_date: date
    hours_per_day: float = Field(..., gt=0, le=24)
    round_structure: List[RoundInfo]

class PlacementProfileResponse(BaseModel):
    id: int
    user_id: int
    company_name: str
    role: str
    interview_date: str
    hours_per_day: float
    round_structure: List[dict]
    status: str
    days_remaining: int
    total_rounds: int
    created_at: str
    class Config:
        from_attributes = True
 