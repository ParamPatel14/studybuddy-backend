from typing import Dict, List, Optional
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.placement_models import (
    DSAPracticeSession, TopicProgress, DailyGoal, PlacementUser
)

class PracticeTracker:
    """Track and analyze DSA practice sessions"""
    
    def record_attempt(
        self,
        user_id: int,
        profile_id: int,
        topic: str,
        problem_name: str,
        difficulty: str,
        solved: bool,
        time_spent_minutes: int,
        db: Session,
        code: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """Record a practice attempt"""
        
        # Create practice session
        session = DSAPracticeSession(
            user_id=user_id,
            profile_id=profile_id,
            topic=topic,
            problem_name=problem_name,
            difficulty=difficulty.lower(),
            attempted=True,
            solved=solved,
            time_spent_minutes=time_spent_minutes,
            code_submitted=code,
            notes=notes,
            solved_at=datetime.utcnow() if solved else None
        )
        
        db.add(session)
        
        # Update topic progress
        self._update_topic_progress(
            user_id, profile_id, topic, difficulty, solved, time_spent_minutes, db
        )
        
        # Update daily goal
        self._update_daily_goal(user_id, profile_id, db)
        
        db.commit()
        
        print(f"✓ Recorded: {problem_name} ({topic}) - {'✓ Solved' if solved else '✗ Attempted'}")
        
        return {
            "session_id": session.id,
            "recorded": True,
            "topic": topic,
            "solved": solved
        }
    
    def _update_topic_progress(
        self,
        user_id: int,
        profile_id: int,
        topic: str,
        difficulty: str,
        solved: bool,
        time_spent: int,
        db: Session
    ):
        """Update aggregate topic progress"""
        
        # Get or create topic progress
        progress = db.query(TopicProgress).filter(
            TopicProgress.user_id == user_id,
            TopicProgress.profile_id == profile_id,
            TopicProgress.topic == topic
        ).first()
        
        if not progress:
            progress = TopicProgress(
                user_id=user_id,
                profile_id=profile_id,
                topic=topic
            )
            db.add(progress)
        
        # Update stats
        progress.problems_attempted += 1
        if solved:
            progress.problems_solved += 1
            
            # Update difficulty-wise count
            if difficulty == 'easy':
                progress.easy_solved += 1
            elif difficulty == 'medium':
                progress.medium_solved += 1
            elif difficulty == 'hard':
                progress.hard_solved += 1
        
        progress.time_spent_minutes += time_spent
        progress.last_practiced = datetime.utcnow()
        
        # Calculate weakness score
        # Higher score = more practice needed
        solve_rate = progress.problems_solved / max(progress.problems_attempted, 1)
        progress.weakness_score = 1.0 - (solve_rate * 0.8)  # 0.2 to 1.0 range
    
    def _update_daily_goal(self, user_id: int, profile_id: int, db: Session):
        """Update today's goal progress"""
        
        today = date.today()
        
        goal = db.query(DailyGoal).filter(
            DailyGoal.user_id == user_id,
            DailyGoal.profile_id == profile_id,
            DailyGoal.date == today
        ).first()
        
        if not goal:
            # Create today's goal
            goal = DailyGoal(
                user_id=user_id,
                profile_id=profile_id,
                date=today,
                target_problems=5
            )
            db.add(goal)
        
        # Count today's problems
        today_count = db.query(func.count(DSAPracticeSession.id)).filter(
            DSAPracticeSession.user_id == user_id,
            DSAPracticeSession.profile_id == profile_id,
            func.date(DSAPracticeSession.attempted_at) == today
        ).scalar()
        
        goal.completed_problems = today_count or 0
        goal.completed = goal.completed_problems >= goal.target_problems
    
    def get_topic_analytics(
        self,
        user_id: int,
        profile_id: int,
        db: Session
    ) -> List[Dict]:
        """Get analytics for all topics"""
        
        progress = db.query(TopicProgress).filter(
            TopicProgress.user_id == user_id,
            TopicProgress.profile_id == profile_id
        ).order_by(TopicProgress.weakness_score.desc()).all()
        
        result = []
        for p in progress:
            solve_rate = (p.problems_solved / max(p.problems_attempted, 1)) * 100
            
            result.append({
                "topic": p.topic,
                "attempted": p.problems_attempted,
                "solved": p.problems_solved,
                "solve_rate": round(solve_rate, 1),
                "time_spent": p.time_spent_minutes,
                "weakness_score": round(p.weakness_score, 2),
                "by_difficulty": {
                    "easy": p.easy_solved,
                    "medium": p.medium_solved,
                    "hard": p.hard_solved
                },
                "last_practiced": p.last_practiced.isoformat() if p.last_practiced else None
            })
        
        return result
    
    def get_daily_problems(
        self,
        user_id: int,
        profile_id: int,
        roadmap_day: int,
        db: Session
    ) -> Dict:
        """Get today's problems from roadmap"""
        
        # This would integrate with the roadmap
        # For now, return sample structure
        
        today = date.today()
        
        goal = db.query(DailyGoal).filter(
            DailyGoal.user_id == user_id,
            DailyGoal.profile_id == profile_id,
            DailyGoal.date == today
        ).first()
        
        if not goal:
            goal = DailyGoal(
                user_id=user_id,
                profile_id=profile_id,
                date=today,
                target_problems=5
            )
            db.add(goal)
            db.commit()
        
        # Get today's attempts
        attempts = db.query(DSAPracticeSession).filter(
            DSAPracticeSession.user_id == user_id,
            DSAPracticeSession.profile_id == profile_id,
            func.date(DSAPracticeSession.attempted_at) == today
        ).all()
        
        return {
            "date": today.isoformat(),
            "target": goal.target_problems,
            "completed": goal.completed_problems,
            "progress_percentage": (goal.completed_problems / goal.target_problems * 100) if goal.target_problems > 0 else 0,
            "attempts_today": [
                {
                    "problem": a.problem_name,
                    "topic": a.topic,
                    "difficulty": a.difficulty,
                    "solved": a.solved,
                    "time_spent": a.time_spent_minutes
                }
                for a in attempts
            ]
        }
    
    def get_practice_history(
        self,
        user_id: int,
        profile_id: int,
        days: int,
        db: Session
    ) -> List[Dict]:
        """Get practice history for last N days"""
        
        start_date = date.today() - timedelta(days=days)
        
        sessions = db.query(DSAPracticeSession).filter(
            DSAPracticeSession.user_id == user_id,
            DSAPracticeSession.profile_id == profile_id,
            DSAPracticeSession.attempted_at >= start_date
        ).order_by(DSAPracticeSession.attempted_at.desc()).all()
        
        return [
            {
                "id": s.id,
                "problem": s.problem_name,
                "topic": s.topic,
                "difficulty": s.difficulty,
                "solved": s.solved,
                "time_spent": s.time_spent_minutes,
                "attempted_at": s.attempted_at.isoformat()
            }
            for s in sessions
        ]
