from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.services.ai_service import AIService
from app.models.models import Topic, Session as StudySession
from app.schemas.schemas import LessonContentResponse

router = APIRouter(prefix="/api/lessons", tags=["lessons"])
ai_service = AIService()

@router.get("/{topic_id}", response_model=LessonContentResponse)
async def get_lesson(
    topic_id: int,
    db: Session = Depends(get_db)
):
    """Get lesson content for a topic"""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    # Generate content
    content = await ai_service.generate_lesson_content(
        topic_name=topic.name,
        subject=topic.study_plan.subject
    )
    
    return {
        "topic_name": topic.name,
        "content": content
    }

@router.post("/{session_id}/complete")
async def mark_session_complete(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Mark a study session as complete"""
    from datetime import datetime
    
    session = db.query(StudySession).filter(StudySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.completed = True
    session.completed_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Session marked as complete"}
