from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.schemas.schemas import (
    StudyPlanCreate, StudyPlanResponse, TopicUpdateRequest, UserCreate
)
from app.models.models import StudyPlan, Topic, User
from app.services.plan_service import PlanService
from typing import List
from datetime import date

router = APIRouter(prefix="/api/study-plan", tags=["study-plan"])
plan_service = PlanService()

@router.post("/create", response_model=StudyPlanResponse)
async def create_study_plan(
    plan_data: StudyPlanCreate,
    db: Session = Depends(get_db)
):
    """Create a new study plan"""
    try:
        print(f"\n{'='*60}")
        print(f"📋 Creating study plan")
        print(f"   User ID: {plan_data.user_id}")
        print(f"   Subject: {plan_data.subject}")
        print(f"   Exam Date: {plan_data.exam_date}")
        print(f"{'='*60}")
        
        # Check if user exists, if not create a default user
        user = db.query(User).filter(User.id == plan_data.user_id).first()
        if not user:
            print(f"⚠️ User {plan_data.user_id} not found, creating default user...")
            user = User(
                id=plan_data.user_id,
                email=f"user{plan_data.user_id}@studybuddy.com",
                name=f"User {plan_data.user_id}"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✓ Created user: {user.email}")
        
        # Create study plan
        study_plan = StudyPlan(
            user_id=plan_data.user_id,
            subject=plan_data.subject,
            exam_type=plan_data.exam_type,
            exam_date=plan_data.exam_date,
            daily_hours=plan_data.daily_hours,
            target_grade=plan_data.target_grade
        )
        
        db.add(study_plan)
        db.commit()
        db.refresh(study_plan)
        
        print(f"✓ Study plan created with ID: {study_plan.id}")
        print(f"{'='*60}\n")
        
        return study_plan
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error creating study plan:")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to create study plan: {str(e)}"
        )

@router.post("/{plan_id}/generate-plan")
async def generate_plan(
    plan_id: int,
    topics_data: TopicUpdateRequest,
    db: Session = Depends(get_db)
):
    """Generate study plan from topics"""
    try:
        print(f"\n{'='*60}")
        print(f"🎯 Generating study plan")
        print(f"   Plan ID: {plan_id}")
        print(f"   Topics: {len(topics_data.topics)}")
        print(f"{'='*60}")
        
        study_plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
        if not study_plan:
            raise HTTPException(status_code=404, detail="Study plan not found")
        
        # Generate plan
        plan = plan_service.generate_study_plan(
            topics=[{"name": t.name, "weight": t.weight} for t in topics_data.topics],
            exam_date=study_plan.exam_date,
            daily_hours=study_plan.daily_hours
        )
        
        print(f"✓ Plan generated with {len(plan)} topics")
        
        # Save topics
        current_date = date.today()
        for topic_data in plan:
            topic = Topic(
                plan_id=plan_id,
                name=topic_data['name'],
                weight=topic_data['weight'],
                allocated_hours=topic_data['allocated_hours'],
                order_index=topic_data['order_index']
            )
            db.add(topic)
            db.flush()
            
            print(f"   → {topic.name}: {topic.allocated_hours}h (weight: {topic.weight})")
            
            # Create sessions for this topic
            plan_service.create_sessions(
                db=db,
                topic_id=topic.id,
                allocated_hours=topic_data['allocated_hours'],
                start_date=current_date,
                daily_hours=study_plan.daily_hours
            )
        
        db.commit()
        
        print(f"✓ Study plan saved to database")
        print(f"{'='*60}\n")
        
        return {"message": "Study plan generated successfully", "plan_id": plan_id}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error generating plan:")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate plan: {str(e)}"
        )

@router.get("/{plan_id}/dashboard")
async def get_dashboard_data(
    plan_id: int,
    db: Session = Depends(get_db)
):
    """Get dashboard data for a study plan"""
    from sqlalchemy import func
    from app.models.models import Session as StudySession
    
    try:
        study_plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
        if not study_plan:
            raise HTTPException(status_code=404, detail="Study plan not found")
        
        # Calculate stats
        total_sessions = db.query(func.count(StudySession.id)).join(Topic).filter(
            Topic.plan_id == plan_id
        ).scalar() or 0
        
        completed_sessions = db.query(func.count(StudySession.id)).join(Topic).filter(
            Topic.plan_id == plan_id,
            StudySession.completed == True
        ).scalar() or 0
        
        progress = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        # Get today's sessions WITH topic_id
        today_sessions = db.query(StudySession).join(Topic).filter(
            Topic.plan_id == plan_id,
            StudySession.scheduled_date == date.today()
        ).all()
        
        return {
            "exam_date": study_plan.exam_date.isoformat(),
            "days_remaining": (study_plan.exam_date - date.today()).days,
            "progress": round(progress, 2),
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "today_tasks": [
                {
                    "topic_id": session.topic.id,  # Add topic_id
                    "topic": session.topic.name,
                    "duration": session.duration,
                    "completed": session.completed
                }
                for session in today_sessions
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
