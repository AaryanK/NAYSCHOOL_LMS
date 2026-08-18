import datetime
from sqlalchemy.orm import Session
from backend.models import User, UsageCounter

PLAN_LIMITS = {
    "free": {
        "tutor_ask": 50,
        "upload": 5,
        "practice_generate": 10,
        "exam_prep_generate": 3
    },
    "plus": {
        "tutor_ask": 500,
        "upload": 50,
        "practice_generate": 100,
        "exam_prep_generate": 20
    },
    "pro": {
        "tutor_ask": 2000,
        "upload": 200,
        "practice_generate": 500,
        "exam_prep_generate": 100
    }
}

def get_user_plan(db: Session, user_id: int) -> str:
    user = db.query(User).filter(User.id == user_id).first()
    return user.plan if user else "free"

def get_or_create_current_usage(db: Session, user_id: int) -> UsageCounter:
    now = datetime.datetime.utcnow()
    
    # Query for active period
    counter = db.query(UsageCounter).filter(
        UsageCounter.user_id == user_id,
        UsageCounter.period_start <= now,
        UsageCounter.period_end >= now
    ).first()
    
    if not counter:
        # Create monthly bounds
        period_start = datetime.datetime(now.year, now.month, 1, 0, 0, 0)
        if now.month == 12:
            period_end = datetime.datetime(now.year + 1, 1, 1, 23, 59, 59) - datetime.timedelta(seconds=1)
        else:
            period_end = datetime.datetime(now.year, now.month + 1, 1, 23, 59, 59) - datetime.timedelta(seconds=1)
            
        counter = UsageCounter(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            tutor_questions_count=0,
            uploads_count=0,
            practice_generations_count=0,
            exam_prep_generations_count=0,
            created_at=now
        )
        db.add(counter)
        db.commit()
        db.refresh(counter)
        
    return counter

def check_usage_limit(db: Session, user_id: int, action: str) -> bool:
    plan = get_user_plan(db, user_id)
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    
    if action not in limits:
        return True # Action not restricted
        
    usage = get_or_create_current_usage(db, user_id)
    
    if action == "tutor_ask":
        return usage.tutor_questions_count < limits["tutor_ask"]
    elif action == "upload":
        return usage.uploads_count < limits["upload"]
    elif action == "practice_generate":
        return usage.practice_generations_count < limits["practice_generate"]
    elif action == "exam_prep_generate":
        return usage.exam_prep_generations_count < limits["exam_prep_generate"]
        
    return True

def increment_usage(db: Session, user_id: int, action: str) -> UsageCounter:
    usage = get_or_create_current_usage(db, user_id)
    
    if action == "tutor_ask":
        usage.tutor_questions_count += 1
    elif action == "upload":
        usage.uploads_count += 1
    elif action == "practice_generate":
        usage.practice_generations_count += 1
    elif action == "exam_prep_generate":
        usage.exam_prep_generations_count += 1
        
    usage.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(usage)
    return usage
