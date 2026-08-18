from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, CourseTopic, DocumentChunk, PracticeQuestion, PracticeAttempt, StudentMastery, StudyPlanTask
from backend.schemas import CourseLearningDashboardResponse, CourseResponse
from backend.services.course_service import CourseService
from backend.services.mastery_service import get_or_create_mastery
from backend.deps import get_current_user

router = APIRouter(prefix="/courses/{course_id}/learning-dashboard", tags=["learning-dashboard"])

def _verify_course(db: Session, course_id: int, user_id: int):
    course = CourseService.get_course_by_id(db, course_id, user_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or unauthorized access."
        )
    return course

@router.get("", response_model=CourseLearningDashboardResponse)
def get_learning_dashboard_endpoint(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = _verify_course(db, course_id, current_user.id)

    # 1. Counts
    topics_count = db.query(CourseTopic).filter(CourseTopic.course_id == course_id).count()
    chunks_count = db.query(DocumentChunk).filter(DocumentChunk.course_id == course_id).count()
    practice_questions_count = db.query(PracticeQuestion).filter(PracticeQuestion.course_id == course_id).count()
    attempts_count = db.query(PracticeAttempt).filter(
        PracticeAttempt.course_id == course_id,
        PracticeAttempt.user_id == current_user.id
    ).count()

    # 2. Mastery Calculations
    topics = db.query(CourseTopic).filter(CourseTopic.course_id == course_id).all()
    masteries = []
    for topic in topics:
        m = get_or_create_mastery(db, current_user.id, course_id, topic.id)
        masteries.append({
            "topic_id": topic.id,
            "name": topic.name,
            "mastery_score": m.mastery_score,
            "confidence": m.confidence,
            "attempts_count": m.attempts_count,
            "correct_count": m.correct_count
        })

    average_mastery = sum(m["mastery_score"] for m in masteries) / len(masteries) if masteries else 0.0

    # Sort topics
    sorted_masteries = sorted(masteries, key=lambda x: x["mastery_score"])
    
    # Weak topics (lowest mastery)
    weak_topics = sorted_masteries[:5]
    
    # Strong topics (highest mastery, descending)
    strong_topics = sorted(masteries, key=lambda x: x["mastery_score"], reverse=True)[:5]

    # 3. Upcoming Study Tasks
    upcoming_tasks = db.query(StudyPlanTask).filter(
        StudyPlanTask.user_id == current_user.id,
        StudyPlanTask.course_id == course_id,
        StudyPlanTask.status != "completed"
    ).order_by(StudyPlanTask.due_at.asc()).limit(5).all()

    # 4. Recent Attempts
    recent_attempts_db = db.query(PracticeAttempt).filter(
        PracticeAttempt.user_id == current_user.id,
        PracticeAttempt.course_id == course_id
    ).order_by(PracticeAttempt.created_at.desc()).limit(5).all()

    recent_attempts = []
    for attempt in recent_attempts_db:
        # Load topic name
        topic_name = "General"
        if attempt.topic_id:
            topic_obj = db.query(CourseTopic).filter(CourseTopic.id == attempt.topic_id).first()
            if topic_obj:
                topic_name = topic_obj.name
        
        recent_attempts.append({
            "id": attempt.id,
            "user_id": attempt.user_id,
            "course_id": attempt.course_id,
            "topic_id": attempt.topic_id,
            "topic_name": topic_name,
            "practice_question_id": attempt.practice_question_id,
            "student_answer": attempt.student_answer,
            "is_correct": attempt.is_correct,
            "score": attempt.score,
            "feedback": attempt.feedback,
            "created_at": attempt.created_at
        })

    return CourseLearningDashboardResponse(
        course=CourseResponse.model_validate(course),
        topics_count=topics_count,
        chunks_count=chunks_count,
        practice_questions_count=practice_questions_count,
        attempts_count=attempts_count,
        average_mastery=round(average_mastery, 2),
        weak_topics=weak_topics,
        strong_topics=strong_topics,
        upcoming_study_tasks=upcoming_tasks,
        recent_attempts=recent_attempts
    )
