import datetime
from sqlalchemy.orm import Session
from backend.models import StudentMastery, CourseTopic

def get_or_create_mastery(db: Session, user_id: int, course_id: int, topic_id: int) -> StudentMastery:
    m = db.query(StudentMastery).filter(
        StudentMastery.user_id == user_id,
        StudentMastery.course_id == course_id,
        StudentMastery.topic_id == topic_id
    ).first()
    
    if not m:
        m = StudentMastery(
            user_id=user_id,
            course_id=course_id,
            topic_id=topic_id,
            mastery_score=0.0,
            confidence=0.0,
            attempts_count=0,
            correct_count=0,
            created_at=datetime.datetime.utcnow()
        )
        db.add(m)
        db.commit()
        db.refresh(m)
    return m

def update_mastery_from_attempt(db: Session, user_id: int, course_id: int, topic_id: int, score: float) -> StudentMastery:
    m = get_or_create_mastery(db, user_id, course_id, topic_id)
    
    m.attempts_count += 1
    if score >= 0.8:
        m.correct_count += 1
        
    # Heuristic decay update formula:
    # new_mastery = old_mastery * 0.75 + score * 0.25
    # confidence = min(1.0, attempts_count / 10)
    new_score = m.mastery_score * 0.75 + score * 0.25
    m.mastery_score = max(0.0, min(1.0, new_score))
    m.confidence = min(1.0, m.attempts_count / 10.0)
    
    now = datetime.datetime.utcnow()
    m.last_practiced_at = now
    m.updated_at = now
    
    db.commit()
    db.refresh(m)
    return m

def get_course_mastery_dashboard(db: Session, user_id: int, course_id: int) -> list:
    topics = db.query(CourseTopic).filter(CourseTopic.course_id == course_id).all()
    dashboard = []
    
    for topic in topics:
        m = get_or_create_mastery(db, user_id, course_id, topic.id)
        dashboard.append({
            "topic_id": topic.id,
            "topic_name": topic.name,
            "mastery_score": m.mastery_score,
            "confidence": m.confidence,
            "attempts_count": m.attempts_count,
            "correct_count": m.correct_count,
            "last_practiced_at": m.last_practiced_at
        })
        
    # Sort weakest topics ascending (0.0 first)
    dashboard.sort(key=lambda x: x["mastery_score"])
    return dashboard
