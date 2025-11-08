from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from app.config.database import get_db
from app.services.question_service import QuestionService
from app.schemas.schemas import (
    PracticeSessionRequest,
    MCQQuestionResponse,
    WrittenQuestionResponse,
    QuestionAttemptCreate,
    QuestionAttemptResponse
)
from app.models.models import (
    Topic, Question, MCQOption, WrittenAnswer, QuestionAttempt,
    SpacedRepetitionSchedule, WeaknessPattern, User
)
from typing import List, Optional
from datetime import date, datetime, timedelta
import traceback

router = APIRouter(prefix="/api/practice", tags=["practice"])
question_service = QuestionService()

# ============================================================================
# QUESTION GENERATION ENDPOINTS
# ============================================================================

@router.post("/generate-questions")
async def generate_practice_questions(
    request: PracticeSessionRequest,
    db: Session = Depends(get_db)
):
    """
    Generate practice questions for a topic
    - Generates 10 MCQs and 5 written questions
    - Caches questions for reuse
    """
    
    try:
        topic = db.query(Topic).filter(Topic.id == request.topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        print(f"\n{'='*60}")
        print(f"🎯 Generating questions for: {topic.name}")
        print(f"   Difficulty: {request.difficulty}")
        print(f"   Count: {request.question_count}")
        print(f"{'='*60}")
        
        # Check if questions already exist
        existing_count = db.query(func.count(Question.id)).filter(
            Question.topic_id == request.topic_id,
            Question.difficulty == request.difficulty
        ).scalar()
        
        if existing_count >= request.question_count:
            print(f"✓ Using existing {existing_count} questions")
            return {
                "topic": topic.name,
                "mcq_count": existing_count,
                "written_count": 0,
                "total_questions": existing_count,
                "difficulty": request.difficulty,
                "cached": True
            }
        
        # Generate new questions
        mcqs = await question_service.generate_mcqs(
            topic=topic,
            difficulty=request.difficulty,
            count=10,
            db=db
        )
        
        written = await question_service.generate_written_questions(
            topic=topic,
            difficulty=request.difficulty,
            count=5,
            db=db
        )
        
        print(f"✓ Generated {len(mcqs)} MCQs + {len(written)} written questions")
        print(f"{'='*60}\n")
        
        return {
            "topic": topic.name,
            "mcq_count": len(mcqs),
            "written_count": len(written),
            "total_questions": len(mcqs) + len(written),
            "difficulty": request.difficulty,
            "cached": False
        }
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ Error generating questions:")
        print(error_trace)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/regenerate-questions/{topic_id}")
async def regenerate_questions(
    topic_id: int,
    difficulty: str = "medium",
    db: Session = Depends(get_db)
):
    """
    Delete existing questions and generate fresh ones
    """
    
    try:
        # Delete existing questions
        deleted = db.query(Question).filter(
            Question.topic_id == topic_id,
            Question.difficulty == difficulty
        ).delete()
        db.commit()
        
        print(f"🗑️ Deleted {deleted} existing questions")
        
        # Generate new ones
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        mcqs = await question_service.generate_mcqs(topic, difficulty, 10, db)
        written = await question_service.generate_written_questions(topic, difficulty, 5, db)
        
        return {
            "message": "Questions regenerated successfully",
            "deleted": deleted,
            "generated": len(mcqs) + len(written)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# QUESTION RETRIEVAL ENDPOINTS
# ============================================================================

@router.get("/questions/{topic_id}")
async def get_practice_questions(
    topic_id: int,
    difficulty: str = Query("medium", regex="^(easy|medium|hard)$"),
    question_type: str = Query("mcq", regex="^(mcq|written|all)$"),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get practice questions for a topic
    - Supports pagination
    - Filter by type and difficulty
    - Randomized order for each session
    """
    
    try:
        query = db.query(Question).filter(
            Question.topic_id == topic_id,
            Question.difficulty == difficulty
        )
        
        if question_type != "all":
            query = query.filter(Question.question_type == question_type)
        
        # Randomize order
        query = query.order_by(func.random())
        
        # Pagination
        total = query.count()
        questions = query.offset(offset).limit(limit).all()
        
        result = []
        for q in questions:
            if q.question_type == "mcq":
                options = db.query(MCQOption).filter(
                    MCQOption.question_id == q.id
                ).all()
                
                result.append({
                    "id": q.id,
                    "type": "mcq",
                    "question_text": q.question_text,
                    "marks": q.marks,
                    "time_limit": q.time_limit,
                    "difficulty": q.difficulty,
                    "options": [
                        {
                            "label": opt.option_label,
                            "text": opt.option_text
                        }
                        for opt in sorted(options, key=lambda x: x.option_label)
                    ]
                })
            else:
                result.append({
                    "id": q.id,
                    "type": "written",
                    "question_text": q.question_text,
                    "marks": q.marks,
                    "time_limit": q.time_limit,
                    "difficulty": q.difficulty,
                    "expected_length": q.written_answer.expected_length if q.written_answer else "200-300 words"
                })
        
        return {
            "questions": result,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total
        }
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ Error fetching questions:")
        print(error_trace)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/question/{question_id}/details")
async def get_question_details(
    question_id: int,
    include_answer: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific question
    - Optionally include correct answer (for review mode)
    """
    
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    result = {
        "id": question.id,
        "topic_id": question.topic_id,
        "topic_name": question.topic.name,
        "type": question.question_type,
        "difficulty": question.difficulty,
        "question_text": question.question_text,
        "marks": question.marks,
        "time_limit": question.time_limit
    }
    
    if question.question_type == "mcq":
        options = db.query(MCQOption).filter(
            MCQOption.question_id == question_id
        ).all()
        
        result["options"] = [
            {
                "label": opt.option_label,
                "text": opt.option_text,
                "is_correct": opt.is_correct if include_answer else None,
                "explanation": opt.explanation if include_answer else None
            }
            for opt in sorted(options, key=lambda x: x.option_label)
        ]
    else:
        if include_answer and question.written_answer:
            result["model_answer"] = question.written_answer.model_answer
            result["marking_scheme"] = question.written_answer.marking_scheme
            result["keywords"] = question.written_answer.keywords
    
    return result

# ============================================================================
# ANSWER SUBMISSION & EVALUATION
# ============================================================================

@router.post("/submit-answer")
async def submit_answer(
    attempt: QuestionAttemptCreate,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Submit answer and get instant evaluation
    - MCQ: Immediate correct/incorrect feedback
    - Written: AI evaluation with detailed feedback
    """
    
    try:
        question = db.query(Question).filter(Question.id == attempt.question_id).first()
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        print(f"\n{'='*60}")
        print(f"📝 Evaluating answer for Q{question.id}")
        print(f"   User: {user_id}")
        print(f"   Type: {question.question_type}")
        print(f"   Answer: {attempt.student_answer[:100]}...")
        print(f"{'='*60}")
        
        # Create attempt record
        question_attempt = QuestionAttempt(
            user_id=user_id,
            question_id=attempt.question_id,
            student_answer=attempt.student_answer,
            time_taken=attempt.time_taken,
            confidence_level=attempt.confidence_level
        )
        
        if question.question_type == "mcq":
            # MCQ Evaluation
            correct_option = db.query(MCQOption).filter(
                MCQOption.question_id == question.id,
                MCQOption.is_correct == True
            ).first()
            
            is_correct = (attempt.student_answer.upper() == correct_option.option_label.upper())
            question_attempt.is_correct = is_correct
            question_attempt.score = question.marks if is_correct else 0
            
            db.add(question_attempt)
            db.commit()
            db.refresh(question_attempt)
            
            print(f"✓ MCQ evaluated: {'Correct' if is_correct else 'Incorrect'}")
            
            return {
                "attempt_id": question_attempt.id,
                "correct": is_correct,
                "score": question_attempt.score,
                "max_score": question.marks,
                "correct_answer": correct_option.option_label,
                "explanation": correct_option.explanation,
                "time_taken": attempt.time_taken
            }
        
        else:
            # Written Answer Evaluation
            written_answer = question.written_answer
            if not written_answer:
                raise HTTPException(status_code=500, detail="Model answer not found")
            
            print(f"🤖 Sending to AI for evaluation...")
            
            evaluation = await question_service.evaluate_written_answer(
                question=question,
                student_answer=attempt.student_answer,
                model_answer=written_answer.model_answer,
                marking_scheme=written_answer.marking_scheme,
                keywords=written_answer.keywords
            )
            
            question_attempt.score = evaluation.get("score", 0)
            question_attempt.is_correct = (evaluation.get("score", 0) / question.marks) >= 0.6
            
            db.add(question_attempt)
            db.commit()
            db.refresh(question_attempt)
            
            print(f"✓ Written answer evaluated: {evaluation.get('score')}/{question.marks}")
            print(f"{'='*60}\n")
            
            return {
                "attempt_id": question_attempt.id,
                "score": evaluation.get("score"),
                "max_score": question.marks,
                "percentage": round((evaluation.get("score", 0) / question.marks) * 100, 1),
                "feedback": evaluation.get("feedback"),
                "strengths": evaluation.get("strengths", []),
                "improvements": evaluation.get("improvements", []),
                "keyword_coverage": evaluation.get("keyword_coverage", 0),
                "keyword_total": evaluation.get("keyword_total", 0),
                "model_answer": written_answer.model_answer,
                "time_taken": attempt.time_taken
            }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        error_trace = traceback.format_exc()
        print(f"❌ Error submitting answer:")
        print(error_trace)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-submit")
async def bulk_submit_answers(
    attempts: List[QuestionAttemptCreate],
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Submit multiple answers at once (for practice sessions)
    """
    
    results = []
    for attempt in attempts:
        try:
            result = await submit_answer(attempt, user_id, db)
            results.append(result)
        except Exception as e:
            results.append({"error": str(e), "question_id": attempt.question_id})
    
    return {
        "total_submitted": len(attempts),
        "results": results
    }

# ============================================================================
# PROGRESS & ANALYTICS
# ============================================================================

@router.get("/progress/{topic_id}")
async def get_topic_progress(
    topic_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive practice progress for a topic
    """
    
    try:
        # Total questions available
        total_questions = db.query(func.count(Question.id)).filter(
            Question.topic_id == topic_id
        ).scalar() or 0
        
        # Questions attempted
        attempted = db.query(func.count(QuestionAttempt.id.distinct())).join(Question).filter(
            Question.topic_id == topic_id,
            QuestionAttempt.user_id == user_id
        ).scalar() or 0
        
        # Average score
        avg_score = db.query(func.avg(QuestionAttempt.score)).join(Question).filter(
            Question.topic_id == topic_id,
            QuestionAttempt.user_id == user_id
        ).scalar() or 0
        
        # Accuracy rate (MCQs only)
        mcq_correct = db.query(func.count(QuestionAttempt.id)).join(Question).filter(
            Question.topic_id == topic_id,
            Question.question_type == "mcq",
            QuestionAttempt.user_id == user_id,
            QuestionAttempt.is_correct == True
        ).scalar() or 0
        
        mcq_total = db.query(func.count(QuestionAttempt.id)).join(Question).filter(
            Question.topic_id == topic_id,
            Question.question_type == "mcq",
            QuestionAttempt.user_id == user_id
        ).scalar() or 1  # Avoid division by zero
        
        accuracy = (mcq_correct / mcq_total * 100) if mcq_total > 0 else 0
        
        # By difficulty breakdown
        difficulty_stats = []
        for diff in ["easy", "medium", "hard"]:
            diff_attempted = db.query(func.count(QuestionAttempt.id)).join(Question).filter(
                Question.topic_id == topic_id,
                Question.difficulty == diff,
                QuestionAttempt.user_id == user_id
            ).scalar() or 0
            
            diff_avg = db.query(func.avg(QuestionAttempt.score)).join(Question).filter(
                Question.topic_id == topic_id,
                Question.difficulty == diff,
                QuestionAttempt.user_id == user_id
            ).scalar() or 0
            
            difficulty_stats.append({
                "difficulty": diff,
                "attempted": diff_attempted,
                "average_score": round(float(diff_avg), 2)
            })
        
        # Calculate mastery level (0-100)
        mastery = 0
        if attempted > 0:
            completion_factor = min(attempted / total_questions, 1.0) if total_questions > 0 else 0
            accuracy_factor = accuracy / 100
            mastery = (completion_factor * 0.4 + accuracy_factor * 0.6) * 100
        
        # Update topic mastery in database
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if topic:
            topic.mastery_level = mastery
            db.commit()
        
        return {
            "topic_id": topic_id,
            "topic_name": topic.name if topic else "Unknown",
            "total_questions": total_questions,
            "attempted": attempted,
            "completion_percentage": round((attempted / total_questions * 100), 1) if total_questions > 0 else 0,
            "average_score": round(float(avg_score), 2),
            "accuracy_rate": round(accuracy, 1),
            "mastery_level": round(mastery, 1),
            "difficulty_breakdown": difficulty_stats
        }
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ Error getting progress:")
        print(error_trace)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/overall-progress/{user_id}")
async def get_overall_progress(
    user_id: int,
    plan_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get overall practice progress across all topics
    """
    
    try:
        query = db.query(Topic)
        if plan_id:
            query = query.filter(Topic.plan_id == plan_id)
        
        topics = query.all()
        
        topic_progress = []
        total_attempted = 0
        total_questions = 0
        
        for topic in topics:
            progress = await get_topic_progress(topic.id, user_id, db)
            topic_progress.append(progress)
            total_attempted += progress["attempted"]
            total_questions += progress["total_questions"]
        
        return {
            "user_id": user_id,
            "topics": topic_progress,
            "summary": {
                "total_topics": len(topics),
                "total_questions": total_questions,
                "total_attempted": total_attempted,
                "overall_completion": round((total_attempted / total_questions * 100), 1) if total_questions > 0 else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/attempt-history/{user_id}")
async def get_attempt_history(
    user_id: int,
    topic_id: Optional[int] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get recent question attempt history
    """
    
    query = db.query(QuestionAttempt).filter(
        QuestionAttempt.user_id == user_id
    )
    
    if topic_id:
        query = query.join(Question).filter(Question.topic_id == topic_id)
    
    attempts = query.order_by(desc(QuestionAttempt.attempted_at)).limit(limit).all()
    
    result = []
    for att in attempts:
        result.append({
            "id": att.id,
            "question_id": att.question_id,
            "question_text": att.question.question_text[:100] + "...",
            "topic": att.question.topic.name,
            "type": att.question.question_type,
            "difficulty": att.question.difficulty,
            "score": att.score,
            "max_score": att.question.marks,
            "is_correct": att.is_correct,
            "time_taken": att.time_taken,
            "confidence": att.confidence_level,
            "attempted_at": att.attempted_at.isoformat()
        })
    
    return {
        "attempts": result,
        "total": len(result)
    }

# ============================================================================
# WEAKNESS DETECTION
# ============================================================================

@router.get("/weak-topics/{user_id}")
async def get_weak_topics(
    user_id: int,
    plan_id: int,
    threshold: float = 60.0,
    db: Session = Depends(get_db)
):
    """
    Identify topics where student is struggling
    - Based on accuracy and mastery level
    """
    
    topics = db.query(Topic).filter(Topic.plan_id == plan_id).all()
    
    weak_topics = []
    
    for topic in topics:
        progress = await get_topic_progress(topic.id, user_id, db)
        
        if progress["attempted"] >= 5 and progress["mastery_level"] < threshold:
            weak_topics.append({
                "topic_id": topic.id,
                "topic_name": topic.name,
                "mastery_level": progress["mastery_level"],
                "accuracy_rate": progress["accuracy_rate"],
                "attempted": progress["attempted"],
                "needs_review": True
            })
    
    return {
        "weak_topics": sorted(weak_topics, key=lambda x: x["mastery_level"]),
        "count": len(weak_topics)
    }

@router.post("/mark-for-review/{topic_id}")
async def mark_topic_for_review(
    topic_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Manually mark a topic for spaced repetition review
    """
    
    # Check if schedule already exists
    schedule = db.query(SpacedRepetitionSchedule).filter(
        SpacedRepetitionSchedule.user_id == user_id,
        SpacedRepetitionSchedule.topic_id == topic_id
    ).first()
    
    if schedule:
        schedule.next_review_date = date.today()
        schedule.interval_days = 1
    else:
        schedule = SpacedRepetitionSchedule(
            user_id=user_id,
            topic_id=topic_id,
            next_review_date=date.today(),
            interval_days=1
        )
        db.add(schedule)
    
    db.commit()
    
    return {
        "message": "Topic marked for review",
        "next_review": schedule.next_review_date.isoformat()
    }

# ============================================================================
# STATISTICS & INSIGHTS
# ============================================================================

@router.get("/stats/{user_id}")
async def get_practice_stats(
    user_id: int,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    Get practice statistics for dashboard
    """
    
    since_date = datetime.now() - timedelta(days=days)
    
    # Questions attempted
    total_attempts = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.attempted_at >= since_date
    ).scalar() or 0
    
    # Average score
    avg_score = db.query(func.avg(QuestionAttempt.score)).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.attempted_at >= since_date
    ).scalar() or 0
    
    # Time spent (in minutes)
    total_time = db.query(func.sum(QuestionAttempt.time_taken)).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.attempted_at >= since_date
    ).scalar() or 0
    
    # Daily breakdown
    daily_stats = db.query(
        func.date(QuestionAttempt.attempted_at).label('date'),
        func.count(QuestionAttempt.id).label('count'),
        func.avg(QuestionAttempt.score).label('avg_score')
    ).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.attempted_at >= since_date
    ).group_by(func.date(QuestionAttempt.attempted_at)).all()
    
    return {
        "period_days": days,
        "total_attempts": total_attempts,
        "average_score": round(float(avg_score), 2),
        "total_time_minutes": round(total_time / 60, 1),
        "daily_breakdown": [
            {
                "date": str(stat.date),
                "attempts": stat.count,
                "average_score": round(float(stat.avg_score), 2)
            }
            for stat in daily_stats
        ]
    }

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@router.delete("/clear-attempts/{user_id}")
async def clear_all_attempts(
    user_id: int,
    topic_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Clear attempt history (for testing/reset)
    """
    
    query = db.query(QuestionAttempt).filter(QuestionAttempt.user_id == user_id)
    
    if topic_id:
        query = query.join(Question).filter(Question.topic_id == topic_id)
    
    deleted = query.delete(synchronize_session=False)
    db.commit()
    
    return {
        "message": "Attempts cleared",
        "deleted_count": deleted
    }

@router.get("/health")
async def practice_health_check(db: Session = Depends(get_db)):
    """Check practice system health"""
    
    question_count = db.query(func.count(Question.id)).scalar()
    attempt_count = db.query(func.count(QuestionAttempt.id)).scalar()
    
    return {
        "status": "healthy",
        "questions_generated": question_count,
        "total_attempts": attempt_count
    }
