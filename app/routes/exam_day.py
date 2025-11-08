from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.config.database import get_db
from app.models.models import Topic, Question, MCQOption, QuestionAttempt, StudyPlan
from app.services.ai_service import AIService
from datetime import date, timedelta
from typing import List, Dict
import traceback

router = APIRouter(prefix="/api/exam-day", tags=["exam-day"])
ai_service = AIService()

@router.get("/quick-revision/{plan_id}")
async def get_quick_revision_sheets(
    plan_id: int,
    db: Session = Depends(get_db)
):
    """
    Generate 1-page revision sheets for each topic
    Perfect for last-minute review
    """
    try:
        study_plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
        if not study_plan:
            raise HTTPException(status_code=404, detail="Study plan not found")
        
        # Get all topics
        topics = db.query(Topic).filter(Topic.plan_id == plan_id).all()
        
        revision_sheets = []
        
        for topic in topics:
            # Get some sample questions for this topic
            sample_questions = db.query(Question).filter(
                Question.topic_id == topic.id,
                Question.question_type == "mcq"
            ).limit(3).all()
            
            sheet = {
                "topic_id": topic.id,
                "topic_name": topic.name,
                "mastery_level": topic.mastery_level,
                "key_formulas": await _generate_key_formulas(topic),
                "important_definitions": await _generate_definitions(topic),
                "must_know_facts": await _generate_facts(topic),
                "common_exam_questions": [
                    q.question_text for q in sample_questions
                ],
                "quick_tips": await _generate_tips(topic)
            }
            
            revision_sheets.append(sheet)
        
        return {
            "exam_date": study_plan.exam_date.isoformat(),
            "days_remaining": (study_plan.exam_date - date.today()).days,
            "revision_sheets": revision_sheets
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating revision sheets: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rapid-quiz/{topic_id}")
async def get_rapid_fire_quiz(
    topic_id: int,
    count: int = 10,
    db: Session = Depends(get_db)
):
    """
    5-minute rapid-fire quiz for confidence boost
    Only high-yield questions
    """
    try:
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Get questions ordered by difficulty (easy first for confidence)
        questions = db.query(Question).filter(
            Question.topic_id == topic_id,
            Question.question_type == "mcq"
        ).order_by(Question.difficulty).limit(count).all()
        
        quiz_questions = []
        for q in questions:
            options = db.query(MCQOption).filter(
                MCQOption.question_id == q.id
            ).all()
            
            quiz_questions.append({
                "id": q.id,
                "question": q.question_text,
                "options": [
                    {"label": opt.option_label, "text": opt.option_text}
                    for opt in sorted(options, key=lambda x: x.option_label)
                ],
                "difficulty": q.difficulty
            })
        
        return {
            "topic_name": topic.name,
            "quiz_type": "rapid_fire",
            "time_limit": 300,  # 5 minutes total
            "questions": quiz_questions,
            "instructions": "Answer quickly - trust your instincts!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/formula-sheet/{plan_id}")
async def get_formula_sheet(
    plan_id: int,
    db: Session = Depends(get_db)
):
    """
    Searchable formula/fact lookup
    Quick reference for last-minute review
    """
    try:
        topics = db.query(Topic).filter(Topic.plan_id == plan_id).all()
        
        formulas = []
        for topic in topics:
            topic_formulas = await _generate_key_formulas(topic)
            for formula in topic_formulas:
                formulas.append({
                    "topic": topic.name,
                    "formula": formula,
                    "category": "formula"
                })
        
        return {
            "total_formulas": len(formulas),
            "formulas": formulas,
            "searchable": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/confidence-booster/{user_id}")
async def get_confidence_booster(
    user_id: int,
    plan_id: int,
    db: Session = Depends(get_db)
):
    """
    Show achievements and success predictions
    Motivational content before exam
    """
    try:
        # Get statistics
        total_attempts = db.query(func.count(QuestionAttempt.id)).filter(
            QuestionAttempt.user_id == user_id
        ).scalar() or 0
        
        avg_score = db.query(func.avg(QuestionAttempt.score)).filter(
            QuestionAttempt.user_id == user_id
        ).scalar() or 0
        
        # Get mastery levels
        topics = db.query(Topic).filter(Topic.plan_id == plan_id).all()
        avg_mastery = sum(t.mastery_level for t in topics) / len(topics) if topics else 0
        
        mastered_topics = sum(1 for t in topics if t.mastery_level >= 80)
        
        # Predict score
        predicted_score = min(95, avg_mastery + 10)  # Optimistic prediction
        
        achievements = []
        if total_attempts > 100:
            achievements.append("🏆 Practice Champion - 100+ questions solved")
        if mastered_topics >= 3:
            achievements.append(f"🎯 Topic Master - Mastered {mastered_topics} topics")
        if avg_score >= 8:
            achievements.append("⭐ High Scorer - Average score above 8")
        
        return {
            "total_questions_solved": total_attempts,
            "average_score": round(float(avg_score), 2),
            "mastery_level": round(avg_mastery, 1),
            "mastered_topics": mastered_topics,
            "predicted_score_range": f"{int(predicted_score - 5)}-{int(predicted_score)}%",
            "achievements": achievements,
            "motivational_message": _get_motivational_message(avg_mastery),
            "strengths": await _get_user_strengths(user_id, db),
            "ready_score": min(100, avg_mastery + 15)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/exam-strategy/{plan_id}")
async def get_exam_strategy_guide(
    plan_id: int,
    db: Session = Depends(get_db)
):
    """
    Time management and question selection strategy
    """
    try:
        study_plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
        if not study_plan:
            raise HTTPException(status_code=404, detail="Study plan not found")
        
        topics = db.query(Topic).filter(Topic.plan_id == plan_id).all()
        
        # Calculate time allocation
        total_topics = len(topics)
        exam_duration = 180  # 3 hours default
        time_per_topic = exam_duration / total_topics if total_topics > 0 else 0
        
        strategy = {
            "exam_type": study_plan.exam_type,
            "total_duration": exam_duration,
            "time_allocation": {
                "reading_questions": 10,
                "planning": 5,
                "answering": exam_duration - 25,
                "review": 10
            },
            "topic_wise_time": {
                topic.name: round(time_per_topic, 1)
                for topic in topics
            },
            "question_selection_tips": [
                "Read all questions first (10 minutes)",
                "Identify easy questions and do them first",
                "Mark difficult questions for later",
                "Allocate time based on marks",
                "Reserve 10 minutes for review"
            ],
            "stress_management": [
                "Take 3 deep breaths before starting",
                "If stuck, move to next question",
                "Don't panic about one difficult question",
                "Keep track of time but don't obsess",
                "Stay hydrated during exam"
            ],
            "dos_and_donts": {
                "do": [
                    "Read questions carefully",
                    "Show your working for partial marks",
                    "Write legibly",
                    "Answer what is asked"
                ],
                "dont": [
                    "Spend too long on one question",
                    "Leave questions blank",
                    "Change answers unless sure",
                    "Rush in the last 10 minutes"
                ]
            }
        }
        
        return strategy
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
async def _generate_key_formulas(topic: Topic) -> List[str]:
    """Generate key formulas for a topic"""
    # In production, use AI or database
    return [
        f"Key formula for {topic.name} #1",
        f"Important equation for {topic.name} #2",
        f"Essential relationship in {topic.name} #3"
    ]

async def _generate_definitions(topic: Topic) -> List[Dict]:
    """Generate important definitions"""
    return [
        {
            "term": f"Concept A in {topic.name}",
            "definition": "Definition of the concept..."
        },
        {
            "term": f"Concept B in {topic.name}",
            "definition": "Definition of the concept..."
        }
    ]

async def _generate_facts(topic: Topic) -> List[str]:
    """Generate must-know facts"""
    return [
        f"Important fact about {topic.name} #1",
        f"Key point to remember in {topic.name} #2",
        f"Critical information for {topic.name} #3"
    ]

async def _generate_tips(topic: Topic) -> List[str]:
    """Generate quick tips"""
    return [
        f"Remember the mnemonic for {topic.name}",
        f"Common mistake to avoid in {topic.name}",
        f"Quick trick for solving {topic.name} problems"
    ]

def _get_motivational_message(mastery: float) -> str:
    """Get motivational message based on mastery"""
    if mastery >= 80:
        return "You're exceptionally well-prepared! Trust your preparation and stay confident. You've got this! 🌟"
    elif mastery >= 60:
        return "Great preparation! You've covered all the important topics. A quick revision and you'll ace it! 💪"
    else:
        return "You've put in the effort! Focus on the topics you know best and do your best. Believe in yourself! 🚀"

async def _get_user_strengths(user_id: int, db: Session) -> List[str]:
    """Identify user's strong topics"""
    from sqlalchemy import desc
    
    # Get topics where user performed well
    strong_attempts = db.query(
        Question.topic_id,
        func.avg(QuestionAttempt.score).label('avg_score')
    ).join(QuestionAttempt).filter(
        QuestionAttempt.user_id == user_id
    ).group_by(Question.topic_id).order_by(desc('avg_score')).limit(3).all()
    
    strengths = []
    for attempt in strong_attempts:
        topic = db.query(Topic).filter(Topic.id == attempt.topic_id).first()
        if topic and attempt.avg_score >= 7:
            strengths.append(f"{topic.name} (avg score: {attempt.avg_score:.1f})")
    
    return strengths if strengths else ["Consistent effort across all topics"]


