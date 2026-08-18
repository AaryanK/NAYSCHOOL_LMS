import json
import datetime
from sqlalchemy.orm import Session
from backend.models import StudyActivity

def log_study_activity(db: Session, user_id: int, activity_type: str, course_id: int = None, metadata: dict = None) -> StudyActivity:
    metadata_str = json.dumps(metadata) if metadata else None
    
    activity = StudyActivity(
        user_id=user_id,
        course_id=course_id,
        activity_type=activity_type,
        metadata_json=metadata_str,
        created_at=datetime.datetime.utcnow()
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity

def get_study_streak(db: Session, user_id: int) -> dict:
    activities = db.query(StudyActivity.created_at).filter(
        StudyActivity.user_id == user_id
    ).order_by(StudyActivity.created_at.desc()).all()
    
    if not activities:
        return {
            "current_streak_days": 0,
            "active_today": False,
            "last_activity_at": None
        }
        
    unique_dates = sorted(list({a.created_at.date() for a in activities}), reverse=True)
    today = datetime.datetime.utcnow().date()
    latest_date = unique_dates[0]
    
    active_today = (latest_date == today)
    
    # Check if streak is alive (activity today or yesterday)
    yesterday = today - datetime.timedelta(days=1)
    if latest_date != today and latest_date != yesterday:
        streak = 0
    else:
        streak = 1
        for i in range(len(unique_dates) - 1):
            if unique_dates[i] - unique_dates[i+1] == datetime.timedelta(days=1):
                streak += 1
            else:
                break
                
    last_activity_at = activities[0].created_at
    
    return {
        "current_streak_days": streak,
        "active_today": active_today,
        "last_activity_at": last_activity_at
    }

def get_recent_activity(db: Session, user_id: int, limit: int = 20) -> list:
    return db.query(StudyActivity).filter(
        StudyActivity.user_id == user_id
    ).order_by(StudyActivity.created_at.desc()).limit(limit).all()
