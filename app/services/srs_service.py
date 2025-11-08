from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.models import SpacedRepetitionSchedule, Topic, QuestionAttempt
from typing import List, Dict
import math

class SRSService:
    """
    Spaced Repetition System using modified Leitner algorithm
    """
    
    # Interval multipliers based on performance
    INTERVALS = [1, 3, 7, 14, 30, 60]  # days
    
    def __init__(self):
        pass
    
    def calculate_next_review(
        self,
        current_interval: int,
        ease_factor: float,
        performance: float
    ) -> tuple[int, float]:
        """
        Calculate next review interval and ease factor
        
        Args:
            current_interval: Current interval in days
            ease_factor: Current ease factor (1.3 - 2.5)
            performance: Score percentage (0-1)
        
        Returns:
            (next_interval_days, new_ease_factor)
        """
        # Adjust ease factor based on performance
        if performance >= 0.9:  # Excellent
            ease_factor = min(ease_factor + 0.15, 2.5)
        elif performance >= 0.7:  # Good
            ease_factor = min(ease_factor + 0.05, 2.5)
        elif performance >= 0.6:  # Acceptable
            ease_factor = max(ease_factor - 0.05, 1.3)
        else:  # Poor
            ease_factor = max(ease_factor - 0.2, 1.3)
            current_interval = 1  # Reset to day 1
        
        # Calculate next interval
        next_interval = math.ceil(current_interval * ease_factor)
        
        # Cap at maximum interval
        next_interval = min(next_interval, 90)
        
        return next_interval, ease_factor
    
    def update_schedule(
        self,
        db: Session,
        user_id: int,
        topic_id: int,
        performance_score: float
    ) -> SpacedRepetitionSchedule:
        """
        Update SRS schedule after practice session
        """
        # Get existing schedule or create new
        schedule = db.query(SpacedRepetitionSchedule).filter(
            SpacedRepetitionSchedule.user_id == user_id,
            SpacedRepetitionSchedule.topic_id == topic_id
        ).first()
        
        if not schedule:
            schedule = SpacedRepetitionSchedule(
                user_id=user_id,
                topic_id=topic_id,
                interval_days=1,
                ease_factor=2.5,
                review_count=0
            )
            db.add(schedule)
        
        # Calculate next review
        next_interval, new_ease = self.calculate_next_review(
            current_interval=schedule.interval_days,
            ease_factor=schedule.ease_factor,
            performance=performance_score
        )
        
        # Update schedule
        schedule.interval_days = next_interval
        schedule.ease_factor = new_ease
        schedule.next_review_date = date.today() + timedelta(days=next_interval)
        schedule.review_count += 1
        schedule.last_reviewed = date.today()
        
        db.commit()
        db.refresh(schedule)
        
        return schedule
    
    def get_due_reviews(
        self,
        db: Session,
        user_id: int,
        plan_id: int = None
    ) -> List[Dict]:
        """
        Get topics due for review today
        """
        query = db.query(SpacedRepetitionSchedule).join(Topic).filter(
            SpacedRepetitionSchedule.user_id == user_id,
            SpacedRepetitionSchedule.next_review_date <= date.today()
        )
        
        if plan_id:
            query = query.filter(Topic.plan_id == plan_id)
        
        schedules = query.all()
        
        result = []
        for schedule in schedules:
            result.append({
                "topic_id": schedule.topic_id,
                "topic_name": schedule.topic.name,
                "next_review_date": schedule.next_review_date,
                "days_overdue": (date.today() - schedule.next_review_date).days,
                "review_count": schedule.review_count,
                "interval_days": schedule.interval_days
            })
        
        return sorted(result, key=lambda x: x['days_overdue'], reverse=True)
    
    def get_upcoming_reviews(
        self,
        db: Session,
        user_id: int,
        days_ahead: int = 7,
        plan_id: int = None
    ) -> Dict[str, List]:
        """
        Get review schedule for next N days
        """
        end_date = date.today() + timedelta(days=days_ahead)
        
        query = db.query(SpacedRepetitionSchedule).join(Topic).filter(
            SpacedRepetitionSchedule.user_id == user_id,
            SpacedRepetitionSchedule.next_review_date.between(date.today(), end_date)
        )
        
        if plan_id:
            query = query.filter(Topic.plan_id == plan_id)
        
        schedules = query.all()
        
        # Group by date
        reviews_by_date = {}
        current = date.today()
        for i in range(days_ahead + 1):
            reviews_by_date[str(current + timedelta(days=i))] = []
        
        for schedule in schedules:
            date_key = str(schedule.next_review_date)
            if date_key in reviews_by_date:
                reviews_by_date[date_key].append({
                    "topic_id": schedule.topic_id,
                    "topic_name": schedule.topic.name,
                    "review_count": schedule.review_count
                })
        
        return reviews_by_date
