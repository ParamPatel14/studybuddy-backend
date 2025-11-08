from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db, Base, engine
from app.models.placement_models import PlacementUser, PlacementProfile, PlacementPlan
from app.schemas.placement_schemas import PlacementProfileCreate, PlacementProfileResponse
from datetime import date

router = APIRouter(prefix="/api/placement", tags=["placement"])

# Initialize placement tables
Base.metadata.create_all(bind=engine)

@router.post("/profile", response_model=PlacementProfileResponse)
async def create_placement_profile(
    profile: PlacementProfileCreate,
    email: str = "placement@example.com",
    db: Session = Depends(get_db)
):
    """
    Create a new placement preparation profile
    Completely independent from exam prep
    """
    try:
        print(f"\n{'='*60}")
        print(f"💼 Creating Placement Profile")
        print(f"   Company: {profile.company_name}")
        print(f"   Role: {profile.role}")
        print(f"   Interview Date: {profile.interview_date}")
        print(f"{'='*60}")
        
        # Get or create placement user
        user = db.query(PlacementUser).filter(PlacementUser.email == email).first()
        if not user:
            user = PlacementUser(
                email=email,
                name=email.split('@')[0]
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"   ✓ Created placement user: {user.id}")
        
        # Calculate days remaining
        days_remaining = (profile.interview_date - date.today()).days
        
        if days_remaining < 0:
            raise HTTPException(status_code=400, detail="Interview date cannot be in the past")
        
        # Convert round structure to JSON
        round_structure_json = [r.dict() for r in profile.round_structure]
        
        # Create profile
        placement_profile = PlacementProfile(
            user_id=user.id,
            company_name=profile.company_name,
            role=profile.role,
            interview_date=profile.interview_date,
            hours_per_day=profile.hours_per_day,
            round_structure=round_structure_json,
            status="active"
        )
        
        db.add(placement_profile)
        db.commit()
        db.refresh(placement_profile)
        
        print(f"   ✓ Profile created: ID {placement_profile.id}")
        print(f"   ✓ Days until interview: {days_remaining}")
        print(f"   ✓ Total rounds: {len(round_structure_json)}")
        
        return PlacementProfileResponse(
            id=placement_profile.id,
            user_id=placement_profile.user_id,
            company_name=placement_profile.company_name,
            role=placement_profile.role,
            interview_date=placement_profile.interview_date.isoformat(),
            hours_per_day=placement_profile.hours_per_day,
            round_structure=placement_profile.round_structure,
            status=placement_profile.status,
            days_remaining=days_remaining,
            total_rounds=len(round_structure_json),
            created_at=placement_profile.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profile/{profile_id}", response_model=PlacementProfileResponse)
async def get_placement_profile(
    profile_id: int,
    db: Session = Depends(get_db)
):
    """Get placement profile details"""
    
    profile = db.query(PlacementProfile).filter(PlacementProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    days_remaining = (profile.interview_date - date.today()).days
    
    return PlacementProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        company_name=profile.company_name,
        role=profile.role,
        interview_date=profile.interview_date.isoformat(),
        hours_per_day=profile.hours_per_day,
        round_structure=profile.round_structure,
        status=profile.status,
        days_remaining=days_remaining,
        total_rounds=len(profile.round_structure),
        created_at=profile.created_at.isoformat()
    )

@router.get("/profiles")
async def get_all_profiles(
    email: str = "placement@example.com",
    db: Session = Depends(get_db)
):
    """Get all placement profiles for a user"""
    
    user = db.query(PlacementUser).filter(PlacementUser.email == email).first()
    if not user:
        return {"profiles": [], "count": 0}
    
    profiles = db.query(PlacementProfile).filter(
        PlacementProfile.user_id == user.id
    ).order_by(PlacementProfile.created_at.desc()).all()
    
    result = []
    for profile in profiles:
        days_remaining = (profile.interview_date - date.today()).days
        result.append({
            "id": profile.id,
            "company_name": profile.company_name,
            "role": profile.role,
            "interview_date": profile.interview_date.isoformat(),
            "days_remaining": days_remaining,
            "status": profile.status,
            "total_rounds": len(profile.round_structure)
        })
    
    return {"profiles": result, "count": len(result)}

@router.delete("/profile/{profile_id}")
async def delete_placement_profile(
    profile_id: int,
    db: Session = Depends(get_db)
):
    """Delete a placement profile"""
    
    profile = db.query(PlacementProfile).filter(PlacementProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    db.delete(profile)
    db.commit()
    
    return {"message": "Profile deleted successfully"}

from app.services.company_questions_service import CompanyQuestionsService

company_questions_service = CompanyQuestionsService()

@router.get("/company-questions/{company_name}")
async def get_company_questions(
    company_name: str,
    role: str = "SDE"
):
    """
    Get interview questions for a specific company
    Uses curated data or AI fallback
    """
    try:
        questions = company_questions_service.get_company_questions(company_name, role)
        return questions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/available-companies")
async def get_available_companies():
    """Get list of companies with curated question data"""
    companies = company_questions_service.get_available_companies()
    return {
        "companies": companies,
        "count": len(companies),
        "note": "Other companies use AI-generated patterns"
    }


from app.services.roadmap_generator import RoadmapGenerator
from datetime import datetime

roadmap_generator = RoadmapGenerator()

@router.post("/generate-roadmap/{profile_id}")
async def generate_roadmap(
    profile_id: int,
    db: Session = Depends(get_db)
):
    """
    Generate personalized day-by-day roadmap for placement prep
    """
    try:
        # Get profile
        profile = db.query(PlacementProfile).filter(PlacementProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Get company questions
        company_questions = company_questions_service.get_company_questions(
            profile.company_name,
            profile.role
        )
        
        # Generate roadmap
        roadmap_data = roadmap_generator.generate_roadmap(
            company_questions=company_questions,
            interview_date=profile.interview_date,
            hours_per_day=profile.hours_per_day,
            round_structure=profile.round_structure
        )
        
        # Save to database
        existing_plan = db.query(PlacementPlan).filter(
            PlacementPlan.profile_id == profile_id
        ).first()
        
        if existing_plan:
            existing_plan.plan_json = roadmap_data['roadmap']
            existing_plan.total_days = roadmap_data['statistics']['total_days']
            existing_plan.total_hours = roadmap_data['statistics']['total_hours']
            existing_plan.total_tasks = roadmap_data['statistics']['total_questions']
        else:
            plan = PlacementPlan(
                profile_id=profile_id,
                plan_json=roadmap_data['roadmap'],
                total_days=roadmap_data['statistics']['total_days'],
                total_hours=roadmap_data['statistics']['total_hours'],
                total_tasks=roadmap_data['statistics']['total_questions']
            )
            db.add(plan)
        
        db.commit()
        
        return {
            "roadmap": roadmap_data['roadmap'],
            "statistics": roadmap_data['statistics'],
            "daily_dsa_count": roadmap_data['daily_dsa_count']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/roadmap/{profile_id}")
async def get_roadmap(
    profile_id: int,
    db: Session = Depends(get_db)
):
    """Get existing roadmap"""
    
    plan = db.query(PlacementPlan).filter(PlacementPlan.profile_id == profile_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Roadmap not found. Generate it first.")
    
    return {
        "roadmap": plan.plan_json,
        "total_days": plan.total_days,
        "total_hours": plan.total_hours,
        "progress": plan.progress_percentage
    }
