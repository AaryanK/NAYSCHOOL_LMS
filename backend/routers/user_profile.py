import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, UserProfile
from backend.schemas import UserProfileResponse, UserProfileUpdate, OnboardingCompleteRequest
from backend.deps import get_current_user

router = APIRouter(prefix="/me", tags=["profile"])

@router.get("/profile", response_model=UserProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        # Auto-create profile if missing
        profile = UserProfile(
            user_id=current_user.id,
            onboarding_completed=False,
            created_at=datetime.datetime.utcnow()
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile

@router.patch("/profile", response_model=UserProfileResponse)
def update_profile(
    req: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(
            user_id=current_user.id,
            onboarding_completed=False,
            created_at=datetime.datetime.utcnow()
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)
    
    profile.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile

@router.post("/onboarding/complete", response_model=UserProfileResponse)
def complete_onboarding(
    req: OnboardingCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(
            user_id=current_user.id,
            created_at=datetime.datetime.utcnow()
        )
        db.add(profile)
    
    update_data = req.model_dump()
    for key, value in update_data.items():
        setattr(profile, key, value)
        
    profile.onboarding_completed = True
    profile.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile
