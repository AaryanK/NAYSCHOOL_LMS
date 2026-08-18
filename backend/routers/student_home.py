from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from backend.database import get_db
from backend.models import User, StudyActivity
from backend.schemas import (
    StudentHomeResponse, StreakResponse, UsageCounterResponse,
    PlanUpdateDevRequest, StudyActivityResponse
)
from backend.services.student_home_service import get_student_home
from backend.services.activity_service import get_study_streak, get_recent_activity
from backend.services.usage_service import get_or_create_current_usage, get_user_plan
from backend.deps import get_current_user

router = APIRouter(tags=["student-home"])

@router.get("/student/home", response_model=StudentHomeResponse)
def get_student_home_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        data = get_student_home(db, current_user.id)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch student home: {str(e)}"
        )

@router.get("/me/activity", response_model=List[StudyActivityResponse])
def get_user_activities(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    activities = get_recent_activity(db, current_user.id, limit=limit)
    return activities

@router.get("/me/streak", response_model=StreakResponse)
def get_user_streak(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    streak = get_study_streak(db, current_user.id)
    return streak

@router.get("/me/plan")
def get_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    plan = get_user_plan(db, current_user.id)
    return {"plan": plan}

@router.get("/me/usage", response_model=UsageCounterResponse)
def get_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    usage = get_or_create_current_usage(db, current_user.id)
    return usage

@router.patch("/me/plan-dev")
def update_plan_dev(
    req: PlanUpdateDevRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if req.plan not in ["free", "plus", "pro"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid plan style. Must be free, plus, or pro."
        )
    
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    user.plan = req.plan
    db.commit()
    db.refresh(user)
    
    return {"plan": user.plan, "message": "Plan updated for testing. Real payment is TODO."}
