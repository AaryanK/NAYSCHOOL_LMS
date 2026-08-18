import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.models import User, Notification, Course, Assignment, StudyPlanTask
from backend.schemas import NotificationResponse
from backend.deps import get_current_user

router = APIRouter(tags=["notifications"])

@router.get("/notifications", response_model=List[NotificationResponse])
def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).all()
    return notifications

@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found."
        )
    
    notif.read_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(notif)
    return notif

@router.post("/courses/{course_id}/notifications/generate-study-reminders", response_model=List[NotificationResponse])
def generate_study_reminders(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verify course ownership
    course = db.query(Course).filter(Course.id == course_id, Course.user_id == current_user.id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or unauthorized access."
        )

    now = datetime.datetime.utcnow()
    one_week_later = now + datetime.timedelta(days=7)
    created_notifications = []

    # 2. Get assignments due soon (not completed)
    assignments = db.query(Assignment).filter(
        Assignment.course_id == course_id,
        Assignment.status != "completed"
    ).all()

    for a in assignments:
        if a.due_date:
            try:
                # Basic parsing or checking
                due_dt = datetime.datetime.strptime(a.due_date[:10], "%Y-%m-%d")
                if now.date() <= due_dt.date() <= one_week_later.date():
                    # Check if notification already exists to avoid duplication
                    exists = db.query(Notification).filter(
                        Notification.user_id == current_user.id,
                        Notification.course_id == course_id,
                        Notification.notification_type == "assignment",
                        Notification.title.like(f"%{a.title}%")
                    ).first() is not None

                    if not exists:
                        notif = Notification(
                            user_id=current_user.id,
                            course_id=course_id,
                            title=f"Assignment Due: {a.title}",
                            message=f"The assignment '{a.title}' for {course.name} is due on {a.due_date}.",
                            notification_type="assignment",
                            delivered_at=now,
                            created_at=now
                        )
                        db.add(notif)
                        created_notifications.append(notif)
            except Exception:
                # Fallback if unparseable
                exists = db.query(Notification).filter(
                    Notification.user_id == current_user.id,
                    Notification.course_id == course_id,
                    Notification.notification_type == "assignment",
                    Notification.title.like(f"%{a.title}%")
                ).first() is not None

                if not exists:
                    notif = Notification(
                        user_id=current_user.id,
                        course_id=course_id,
                        title=f"Assignment Due: {a.title}",
                        message=f"The assignment '{a.title}' for {course.name} is due soon: {a.due_date}.",
                        notification_type="assignment",
                        delivered_at=now,
                        created_at=now
                    )
                    db.add(notif)
                    created_notifications.append(notif)

    # 3. Get study plan tasks due soon (not completed)
    tasks = db.query(StudyPlanTask).filter(
        StudyPlanTask.course_id == course_id,
        StudyPlanTask.user_id == current_user.id,
        StudyPlanTask.status != "completed",
        StudyPlanTask.due_at <= one_week_later
    ).all()

    for t in tasks:
        # Check if notification already exists
        exists = db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.course_id == course_id,
            Notification.notification_type == "study_task",
            Notification.title.like(f"%{t.title}%")
        ).first() is not None

        if not exists:
            due_str = t.due_at.strftime("%Y-%m-%d") if t.due_at else "soon"
            notif = Notification(
                user_id=current_user.id,
                course_id=course_id,
                title=f"Study Task: {t.title}",
                message=f"Don't forget to study '{t.title}' for {course.name}. Scheduled for {due_str}.",
                notification_type="study_task",
                delivered_at=now,
                created_at=now
            )
            db.add(notif)
            created_notifications.append(notif)

    if created_notifications:
        db.commit()
        for n in created_notifications:
            db.refresh(n)

    return created_notifications
