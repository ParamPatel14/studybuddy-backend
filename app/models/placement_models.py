from sqlalchemy import Boolean, Column, Integer, String, Float, Date, DateTime, JSON, ForeignKey,Text
from sqlalchemy.orm import relationship
from app.config.database import Base
from datetime import datetime

# ============================================================================
# PLACEMENT PREP - COMPLETELY INDEPENDENT FROM EXAM PREP
# ============================================================================

class PlacementUser(Base):
    """Separate user table for placement prep"""
    __tablename__ = "placement_users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    profiles = relationship("PlacementProfile", back_populates="user", cascade="all, delete-orphan")

class PlacementProfile(Base):
    """Interview preparation profile"""
    __tablename__ = "placement_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("placement_users.id"))
    
    # Company & Role
    company_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    
    # Schedule
    interview_date = Column(Date, nullable=False)
    hours_per_day = Column(Float, nullable=False)
    
    # Round Structure (JSON)
    # Example: [
    #   {"round_number": 1, "type": "aptitude", "duration": 60},
    #   {"round_number": 2, "type": "dsa_coding", "duration": 90}
    # ]
    round_structure = Column(JSON, nullable=False)
    
    # Status
    status = Column(String, default="active")  # active, completed, cancelled
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("PlacementUser", back_populates="profiles")
    preparation_plan = relationship("PlacementPlan", back_populates="profile", uselist=False)

class PlacementPlan(Base):
    __tablename__ = "placement_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("placement_profiles.id"), unique=True)
    
    plan_json = Column(JSON)
    total_days = Column(Integer)
    total_hours = Column(Float)
    total_tasks = Column(Integer, default=0)  # Add this
    
    completed_tasks = Column(Integer, default=0)
    total_topics = Column(Integer, default=0)
    progress_percentage = Column(Float, default=0.0)
    
    profile = relationship("PlacementProfile", back_populates="preparation_plan")
    created_at = Column(DateTime, default=datetime.utcnow)


class DSAPracticeSession(Base):
    """Track DSA practice sessions"""
    __tablename__ = "dsa_practice_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("placement_users.id"))
    profile_id = Column(Integer, ForeignKey("placement_profiles.id"))
    
    # Problem Details
    topic = Column(String, nullable=False)
    problem_name = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)  # easy, medium, hard
    
    # Attempt Details
    attempted = Column(Boolean, default=True)
    solved = Column(Boolean, default=False)
    time_spent_minutes = Column(Integer, default=0)
    
    # Solution Details (optional)
    code_submitted = Column(Text, nullable=True)
    approach_used = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    attempted_at = Column(DateTime, default=datetime.utcnow)
    solved_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("PlacementUser")

class TopicProgress(Base):
    """Aggregate topic-wise progress"""
    __tablename__ = "topic_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("placement_users.id"))
    profile_id = Column(Integer, ForeignKey("placement_profiles.id"))
    
    topic = Column(String, nullable=False, index=True)
    
    # Statistics
    problems_attempted = Column(Integer, default=0)
    problems_solved = Column(Integer, default=0)
    time_spent_minutes = Column(Integer, default=0)
    
    # Performance
    easy_solved = Column(Integer, default=0)
    medium_solved = Column(Integer, default=0)
    hard_solved = Column(Integer, default=0)
    
    # Weakness Score (higher = needs more practice)
    weakness_score = Column(Float, default=1.0)
    
    # Timestamps
    last_practiced = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("PlacementUser")

class DailyGoal(Base):
    """Track daily practice goals"""
    __tablename__ = "daily_goals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("placement_users.id"))
    profile_id = Column(Integer, ForeignKey("placement_profiles.id"))
    
    date = Column(Date, nullable=False)
    
    # Goals
    target_problems = Column(Integer, default=5)
    completed_problems = Column(Integer, default=0)
    
    # Topics for today
    topics_planned = Column(JSON)  # List of topics
    
    # Status
    completed = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("PlacementUser")