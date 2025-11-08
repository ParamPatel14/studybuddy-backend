from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.services.srs_service import SRSService
from datetime import date
from typing import Optional

router = APIRouter(prefix="/api/srs", tags=["spaced-repetition"])
srs_service = SRSService()

@router.get("/due-reviews/{user_id}")
async def get_due_reviews(
    user_id: int,
    plan_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get topics due for review today"""
    try:
        reviews = srs_service.get_due_reviews(db, user_id, plan_id)
        return {
            "due_today": reviews,
            "count": len(reviews)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/upcoming-reviews/{user_id}")
async def get_upcoming_reviews(
    user_id: int,
    days_ahead: int = Query(7, ge=1, le=30),
    plan_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get review schedule for upcoming days"""
    try:
        schedule = srs_service.get_upcoming_reviews(db, user_id, days_ahead, plan_id)
        return {
            "schedule": schedule,
            "days_ahead": days_ahead
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update-schedule")
async def update_schedule(
    user_id: int,
    topic_id: int,
    performance_score: float = Query(..., ge=0, le=1),
    db: Session = Depends(get_db)
):
    """Update SRS schedule after practice"""
    try:
        schedule = srs_service.update_schedule(db, user_id, topic_id, performance_score)
        
        return {
            "topic_id": topic_id,
            "next_review_date": schedule.next_review_date.isoformat(),
            "interval_days": schedule.interval_days,
            "ease_factor": schedule.ease_factor,
            "review_count": schedule.review_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
