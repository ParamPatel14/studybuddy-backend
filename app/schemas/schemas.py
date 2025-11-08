from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from typing import List, Optional, Dict, Any

class UserCreate(BaseModel):
    email: EmailStr
    name: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    
    class Config:
        from_attributes = True

class StudyPlanCreate(BaseModel):
    user_id: int
    subject: str
    exam_type: str
    exam_date: date
    daily_hours: float
    target_grade: str

class TopicResponse(BaseModel):
    id: int
    name: str
    weight: float
    allocated_hours: float
    order_index: int
    mastery_level: float
    
    class Config:
        from_attributes = True

class SessionResponse(BaseModel):
    id: int
    topic_id: int
    scheduled_date: date
    duration: float
    completed: bool
    
    class Config:
        from_attributes = True

class StudyPlanResponse(BaseModel):
    id: int
    subject: str
    exam_type: str
    exam_date: date
    daily_hours: float
    target_grade: str
    status: str
    topics: List[TopicResponse]
    
    class Config:
        from_attributes = True

class TopicInput(BaseModel):
    name: str
    weight: float

class TopicUpdateRequest(BaseModel):
    topics: List[TopicInput]

# NEW: Question Schemas
class MCQOptionSchema(BaseModel):
    option_label: str
    option_text: str
    is_correct: bool
    explanation: Optional[str] = None

class MCQQuestionCreate(BaseModel):
    question_text: str
    options: List[MCQOptionSchema]
    difficulty: str
    marks: int = 1
    time_limit: int = 60

class WrittenQuestionCreate(BaseModel):
    question_text: str
    model_answer: str
    marking_scheme: Dict[str, int]
    keywords: List[Dict[str, str]]
    expected_length: str
    difficulty: str
    marks: int
    time_limit: int

class QuestionResponse(BaseModel):
    id: int
    topic_id: int
    question_type: str
    difficulty: str
    question_text: str
    marks: int
    time_limit: int
    
    class Config:
        from_attributes = True

class MCQQuestionResponse(QuestionResponse):
    options: List[MCQOptionSchema]

class WrittenQuestionResponse(QuestionResponse):
    model_answer: str
    marking_scheme: Dict[str, int]
    keywords: List[Dict[str, str]]
    expected_length: str

class QuestionAttemptCreate(BaseModel):
    question_id: int
    student_answer: str
    time_taken: int
    confidence_level: int

class QuestionAttemptResponse(BaseModel):
    id: int
    question_id: int
    is_correct: Optional[bool]
    score: Optional[float]
    time_taken: int
    confidence_level: int
    attempted_at: datetime
    
    class Config:
        from_attributes = True

class PracticeSessionRequest(BaseModel):
    topic_id: int
    difficulty: str
    question_count: int = 10

class LessonContentResponse(BaseModel):
    topic_name: str
    content: dict
