from datetime import datetime, timedelta, date
from typing import List
from sqlalchemy.orm import Session
from app.models.models import Topic, Session as StudySession

class PlanService:
    @staticmethod
    def generate_study_plan(
        topics: List[dict],
        exam_date: date,
        daily_hours: float,
        start_date: date = None
    ) -> List[dict]:
        """Generate study plan with sessions distributed across available days"""
        if start_date is None:
            start_date = date.today()
        
        days_available = (exam_date - start_date).days
        if days_available <= 0:
            raise ValueError("Exam date must be in the future")
        
        total_hours = days_available * daily_hours
        total_weight = sum(topic['weight'] for topic in topics)
        
        # Allocate hours to each topic based on weight
        plan = []
        for idx, topic in enumerate(topics):
            allocated_hours = (topic['weight'] / total_weight) * total_hours * 0.9  # 90% for learning, 10% buffer
            
            plan.append({
                "name": topic['name'],
                "weight": topic['weight'],
                "allocated_hours": round(allocated_hours, 2),
                "order_index": idx
            })
        
        return plan
    
    @staticmethod
    def create_sessions(
        db: Session,
        topic_id: int,
        allocated_hours: float,
        start_date: date,
        daily_hours: float
    ) -> List[StudySession]:
        """Create study sessions for a topic"""
        sessions = []
        remaining_hours = allocated_hours
        current_date = start_date
        
        while remaining_hours > 0:
            session_duration = min(remaining_hours, daily_hours / 2)  # Max 2 topics per day
            
            session = StudySession(
                topic_id=topic_id,
                scheduled_date=current_date,
                duration=round(session_duration, 2),
                completed=False
            )
            sessions.append(session)
            db.add(session)
            
            remaining_hours -= session_duration
            current_date += timedelta(days=1)
        
        return sessions
