from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.services.practice_tracker import PracticeTracker
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/placement/practice", tags=["placement-practice"])
practice_tracker = PracticeTracker()

class PracticeAttempt(BaseModel):
    topic: str
    problem_name: str
    difficulty: str  # easy, medium, hard
    solved: bool
    time_spent_minutes: int
    code: Optional[str] = None
    notes: Optional[str] = None

@router.post("/record")
async def record_practice(
    attempt: PracticeAttempt,
    user_id: int = 1,
    profile_id: int = 1,
    db: Session = Depends(get_db)
):
    """Record a DSA practice attempt"""
    
    try:
        result = practice_tracker.record_attempt(
            user_id=user_id,
            profile_id=profile_id,
            topic=attempt.topic,
            problem_name=attempt.problem_name,
            difficulty=attempt.difficulty,
            solved=attempt.solved,
            time_spent_minutes=attempt.time_spent_minutes,
            code=attempt.code,
            notes=attempt.notes,
            db=db
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/{profile_id}")
async def get_analytics(
    profile_id: int,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """Get topic-wise analytics"""
    
    analytics = practice_tracker.get_topic_analytics(user_id, profile_id, db)
    
    return {
        "topics": analytics,
        "total_topics": len(analytics)
    }

@router.get("/daily/{profile_id}")
async def get_daily_progress(
    profile_id: int,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """Get today's practice progress"""
    
    progress = practice_tracker.get_daily_problems(user_id, profile_id, 1, db)
    
    return progress

@router.get("/history/{profile_id}")
async def get_practice_history(
    profile_id: int,
    days: int = 7,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """Get practice history"""
    
    history = practice_tracker.get_practice_history(user_id, profile_id, days, db)
    
    return {
        "history": history,
        "days": days
    }
