from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Date, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.config.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    study_plans = relationship("StudyPlan", back_populates="user")

class StudyPlan(Base):
    __tablename__ = "study_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String)
    exam_type = Column(String)
    exam_date = Column(Date)
    daily_hours = Column(Float)
    target_grade = Column(String)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="study_plans")
    topics = relationship("Topic", back_populates="study_plan", cascade="all, delete-orphan")

class Topic(Base):
    __tablename__ = "topics"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("study_plans.id"))
    name = Column(String)
    weight = Column(Float)
    allocated_hours = Column(Float)
    order_index = Column(Integer)
    mastery_level = Column(Float, default=0.0)  # 0-100%
    
    study_plan = relationship("StudyPlan", back_populates="topics")
    sessions = relationship("Session", back_populates="topic", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="topic", cascade="all, delete-orphan")

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"))
    scheduled_date = Column(Date)
    duration = Column(Float)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    
    topic = relationship("Topic", back_populates="sessions")

# NEW: Questions table
class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"))
    question_type = Column(String)  # 'mcq' or 'written'
    difficulty = Column(String)  # 'easy', 'medium', 'hard'
    question_text = Column(Text)
    marks = Column(Integer, default=1)
    time_limit = Column(Integer)  # seconds
    source = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    topic = relationship("Topic", back_populates="questions")
    mcq_options = relationship("MCQOption", back_populates="question", cascade="all, delete-orphan")
    written_answer = relationship("WrittenAnswer", back_populates="question", uselist=False, cascade="all, delete-orphan")
    attempts = relationship("QuestionAttempt", back_populates="question", cascade="all, delete-orphan")

# NEW: MCQ Options
class MCQOption(Base):
    __tablename__ = "mcq_options"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    option_label = Column(String(1))  # A, B, C, D
    option_text = Column(Text)
    is_correct = Column(Boolean)
    explanation = Column(Text, nullable=True)
    
    question = relationship("Question", back_populates="mcq_options")

# NEW: Written Answers
class WrittenAnswer(Base):
    __tablename__ = "written_answers"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    model_answer = Column(Text)
    marking_scheme = Column(JSON)  # {"introduction": 2, "body": 5, "conclusion": 1}
    keywords = Column(JSON)  # [{"word": "chlorophyll", "importance": "high"}]
    expected_length = Column(String)  # "200-300 words"
    
    question = relationship("Question", back_populates="written_answer")

# NEW: Question Attempts
class QuestionAttempt(Base):
    __tablename__ = "question_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    student_answer = Column(Text)
    is_correct = Column(Boolean, nullable=True)
    score = Column(Float, nullable=True)  # For written answers
    time_taken = Column(Integer)  # seconds
    confidence_level = Column(Integer)  # 1-5
    attempted_at = Column(DateTime, default=datetime.utcnow)
    
    question = relationship("Question", back_populates="attempts")

# NEW: Spaced Repetition Schedule
class SpacedRepetitionSchedule(Base):
    __tablename__ = "spaced_repetition_schedule"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    topic_id = Column(Integer, ForeignKey("topics.id"))
    next_review_date = Column(Date)
    interval_days = Column(Integer, default=1)
    ease_factor = Column(Float, default=2.5)
    review_count = Column(Integer, default=0)
    last_reviewed = Column(DateTime, nullable=True)

# NEW: Weakness Patterns
class WeaknessPattern(Base):
    __tablename__ = "weakness_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    topic_id = Column(Integer, ForeignKey("topics.id"))
    error_category = Column(String)
    occurrence_count = Column(Integer, default=1)
    last_detected = Column(DateTime, default=datetime.utcnow)
    remedial_content_generated = Column(Boolean, default=False)

class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("study_plans.id"))
    filename = Column(String)
    file_type = Column(String)
    extracted_text = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
