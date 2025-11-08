from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.config.database import Base
from datetime import datetime

# ============================================================================
# PEER-TO-PEER LEARNING SYSTEM
# ============================================================================

class PeerProfile(Base):
    """Student profile for peer matching"""
    __tablename__ = "peer_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True)
    name = Column(String)
    
    # Matching Criteria
    goal_type = Column(String)  # exam, placement
    subject = Column(String, nullable=True)
    company = Column(String, nullable=True)
    hours_per_day = Column(Float)
    skill_level = Column(String)  # beginner, intermediate, advanced
    confidence_rating = Column(Float)  # 1-5
    
    # Status
    is_looking_for_partner = Column(Boolean, default=False)
    current_study_streak = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    partnerships = relationship("StudyPartnership", foreign_keys="[StudyPartnership.user1_id]")

class StudyPartnership(Base):
    """Study partner connections"""
    __tablename__ = "study_partnerships"
    
    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(Integer, ForeignKey("peer_profiles.user_id"))
    user2_id = Column(Integer, ForeignKey("peer_profiles.user_id"))
    
    status = Column(String, default="active")  # active, paused, ended
    match_score = Column(Float)  # How well they match
    
    created_at = Column(DateTime, default=datetime.utcnow)

class DoubtThread(Base):
    """Doubt discussion threads"""
    __tablename__ = "doubt_threads"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    topic = Column(String)
    title = Column(String)
    question = Column(Text)
    
    upvotes = Column(Integer, default=0)
    is_resolved = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    responses = relationship("DoubtResponse", back_populates="thread")

class DoubtResponse(Base):
    """Responses to doubt threads"""
    __tablename__ = "doubt_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("doubt_threads.id"))
    user_id = Column(Integer)
    response_text = Column(Text)
    is_ai_response = Column(Boolean, default=False)
    
    upvotes = Column(Integer, default=0)
    is_accepted = Column(Boolean, default=False)  # Marked as best answer
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    thread = relationship("DoubtThread", back_populates="responses")

class StudyGroup(Base):
    """Group prep rooms"""
    __tablename__ = "study_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    room_type = Column(String)  # subject_prep, dsa_prep, placement_prep
    goal = Column(String)  # Specific goal (e.g., "Amazon SDE", "DBMS Exam")
    
    max_members = Column(Integer, default=6)
    current_members = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    members = relationship("GroupMembership", back_populates="group")
    sessions = relationship("GroupSession", back_populates="group")

class GroupMembership(Base):
    """Group members"""
    __tablename__ = "group_memberships"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("study_groups.id"))
    user_id = Column(Integer)
    role = Column(String, default="member")  # member, admin
    
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    group = relationship("StudyGroup", back_populates="members")

class GroupSession(Base):
    """Shared practice sessions"""
    __tablename__ = "group_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("study_groups.id"))
    
    session_type = Column(String)  # dsa_practice, revision_challenge, mock_interview
    problem_name = Column(String, nullable=True)
    duration_minutes = Column(Integer)
    
    scheduled_at = Column(DateTime)
    status = Column(String, default="scheduled")  # scheduled, active, completed
    
    # Results
    participants = Column(JSON)  # [{user_id, score, time_taken}]
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    group = relationship("StudyGroup", back_populates="sessions")

class RevisionChallenge(Base):
    """Gamified revision challenges"""
    __tablename__ = "revision_challenges"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("study_groups.id"))
    
    title = Column(String)  # "5 Questions in 20 Minutes"
    description = Column(Text)
    questions = Column(JSON)  # List of questions
    time_limit_minutes = Column(Integer)
    
    status = Column(String, default="upcoming")  # upcoming, active, completed
    
    # Leaderboard
    scores = Column(JSON)  # [{user_id, score, time_taken}]
    
    created_at = Column(DateTime, default=datetime.utcnow)

class WeaknessAnalysis(Base):
    """Group weakness tracking"""
    __tablename__ = "weakness_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("study_groups.id"))
    
    topic = Column(String)
    avg_score = Column(Float)
    total_attempts = Column(Integer)
    weakness_level = Column(String)  # high, medium, low
    
    # Scheduled intervention
    next_session_date = Column(DateTime, nullable=True)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
