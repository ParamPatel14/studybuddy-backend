from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.peer_models import (
    PeerProfile, StudyPartnership, DoubtThread, DoubtResponse,
    StudyGroup, GroupMembership, GroupSession, RevisionChallenge, WeaknessAnalysis
)
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/peer", tags=["peer-learning"])

# ============================================================================
# HARDCODED DEMO DATA
# ============================================================================

DEMO_PEERS = [
    {
        "id": 1,
        "name": "Rahul Sharma",
        "goal_type": "placement",
        "company": "Amazon",
        "hours_per_day": 3,
        "skill_level": "intermediate",
        "confidence_rating": 3.5,
        "match_score": 95
    },
    {
        "id": 2,
        "name": "Priya Patel",
        "goal_type": "placement",
        "company": "Amazon",
        "hours_per_day": 2.5,
        "skill_level": "intermediate",
        "confidence_rating": 3.8,
        "match_score": 92
    },
    {
        "id": 3,
        "name": "Amit Kumar",
        "goal_type": "exam",
        "subject": "DBMS",
        "hours_per_day": 2,
        "skill_level": "beginner",
        "confidence_rating": 2.5,
        "match_score": 88
    }
]

DEMO_GROUPS = [
    {
        "id": 1,
        "name": "Amazon SDE Prep Warriors",
        "room_type": "placement_prep",
        "goal": "Amazon SDE Interview",
        "current_members": 4,
        "max_members": 6,
        "members": ["Rahul", "Priya", "Ankit", "Neha"]
    },
    {
        "id": 2,
        "name": "DSA Masters Group",
        "room_type": "dsa_prep",
        "goal": "Competitive Programming",
        "current_members": 5,
        "max_members": 6,
        "members": ["Vikas", "Sanya", "Rohan", "Divya", "Karan"]
    },
    {
        "id": 3,
        "name": "DBMS Final Exam Squad",
        "room_type": "subject_prep",
        "goal": "DBMS Semester Exam",
        "current_members": 3,
        "max_members": 6,
        "members": ["Amit", "Sneha", "Rajesh"]
    }
]

DEMO_DOUBTS = [
    {
        "id": 1,
        "topic": "Binary Trees",
        "title": "How to find height of a Binary Tree?",
        "question": "I'm confused about the recursive approach. Can someone explain with an example?",
        "user": "Rahul",
        "upvotes": 12,
        "responses": 5,
        "is_resolved": True
    },
    {
        "id": 2,
        "topic": "Dynamic Programming",
        "title": "Difference between memoization and tabulation?",
        "question": "When should I use top-down vs bottom-up approach?",
        "user": "Priya",
        "upvotes": 8,
        "responses": 3,
        "is_resolved": False
    }
]

DEMO_SESSIONS = [
    {
        "id": 1,
        "type": "dsa_practice",
        "problem": "Two Sum Problem",
        "scheduled": "Today 6:00 PM",
        "participants": 4,
        "status": "upcoming"
    },
    {
        "id": 2,
        "type": "revision_challenge",
        "problem": "5 Questions in 20 Minutes",
        "scheduled": "Tomorrow 7:00 PM",
        "participants": 5,
        "status": "upcoming"
    }
]

DEMO_WEAKNESS = [
    {
        "topic": "Graphs",
        "avg_score": 42,
        "level": "high",
        "next_session": "Tomorrow 6:00 PM"
    },
    {
        "topic": "Dynamic Programming",
        "avg_score": 58,
        "level": "medium",
        "next_session": "Day after tomorrow"
    }
]

# ============================================================================
# 1. STUDY PARTNER MATCHING
# ============================================================================

@router.get("/find-partners")
async def find_study_partners(
    goal_type: str = "placement",
    user_id: int = 1
):
    """Find matched study partners"""
    
    return {
        "matches": DEMO_PEERS,
        "total": len(DEMO_PEERS),
        "message": "These students match your study goals and schedule"
    }

@router.post("/partner/connect/{peer_id}")
async def connect_with_partner(peer_id: int):
    """Connect with a study partner"""
    
    peer = next((p for p in DEMO_PEERS if p["id"] == peer_id), None)
    
    if not peer:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    return {
        "success": True,
        "message": f"Connected with {peer['name']}!",
        "partner": peer
    }

# ============================================================================
# 2. DOUBT THREADING SYSTEM
# ============================================================================

@router.get("/doubts")
async def get_doubts(topic: Optional[str] = None):
    """Get doubt threads"""
    
    doubts = DEMO_DOUBTS
