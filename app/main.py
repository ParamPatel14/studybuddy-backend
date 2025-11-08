from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config.database import engine, Base
from app.routes import upload, study_plan, lessons, test_gemini, practice  # Add practice
from app.models import models
from app.routes import upload, study_plan, lessons, test_gemini, practice, srs
from app.routes import upload, study_plan, lessons, test_gemini, practice, srs, exam_day
from app.routes import upload, study_plan, lessons, test_gemini, practice, srs, exam_day, chatbot
from app.routes import placement_practice
from app.routes import placement
from app.routes import youtube
from app.routes import peer
from app.models import models, placement_models, peer_models  # Add peer_models
from app.routes import (
    upload, study_plan, lessons, test_gemini, practice, 
    srs, exam_day, chatbot, placement, placement_practice, 
    youtube, peer  # Add peer
)
import traceback

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart Exam Prep API",
    description="AI-powered exam preparation - Phase 3: Chatbot",
    version="3.0.0"
)

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_trace = traceback.format_exc()
    print(f"\n{'='*60}")
    print(f"❌ UNHANDLED EXCEPTION")
    print(f"Path: {request.method} {request.url.path}")
    print(f"Error: {str(exc)}")
    print(f"Traceback:")
    print(error_trace)
    print(f"{'='*60}\n")
    
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "path": str(request.url.path)},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router)
app.include_router(study_plan.router)
app.include_router(lessons.router)
app.include_router(test_gemini.router)
app.include_router(practice.router)
app.include_router(srs.router)
app.include_router(exam_day.router)
app.include_router(chatbot.router)  # Phase 3
app.include_router(placement.router)
app.include_router(placement_practice.router)
app.include_router(youtube.router) 
app.include_router(peer.router)
app.include_router(peer.router)

@app.get("/")
async def root():
    return {
        "message": "Smart Exam Prep API - Phase 3: AI Chatbot",
        "version": "3.0.0",
        "features": [
            "Phase 1: Onboarding & Study Plan",
            "Phase 2: Practice & Questions",
            "Phase 3: AI Chatbot with Voice"
        ]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "phase": "3",
        "features": ["chatbot", "practice", "exam-day"]
    }

@app.get("/debug/db-status")
async def check_database():
    """Check database connection and tables"""
    from app.config.database import SessionLocal
    from sqlalchemy import inspect
    
    try:
        db = SessionLocal()
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Count users
        user_count = db.query(models.User).count()
        plan_count = db.query(models.StudyPlan).count()
        
        db.close()
        
        return {
            "status": "connected",
            "tables": tables,
            "user_count": user_count,
            "plan_count": plan_count
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
