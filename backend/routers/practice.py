from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from backend.database import get_db
from backend.models import User, PracticeQuestion, PracticeAttempt
from backend.schemas import (
    PracticeQuestionGenerateRequest,
    PracticeQuestionResponse,
    PracticeAttemptGradeRequest,
    PracticeAttemptResponse
)
from backend.services.course_service import CourseService
from backend.services.practice_service import (
    generate_practice_questions,
    grade_practice_attempt
)
from backend.deps import get_current_user

router = APIRouter(prefix="/courses/{course_id}/practice", tags=["practice"])

def _verify_course(db: Session, course_id: int, user_id: int):
    course = CourseService.get_course_by_id(db, course_id, user_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or unauthorized access."
        )
    return course

@router.post("/generate", response_model=list[PracticeQuestionResponse])
async def generate_practice_endpoint(
    course_id: int,
    req: PracticeQuestionGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _verify_course(db, course_id, current_user.id)
    
    # Check usage limit
    from backend.services.usage_service import check_usage_limit, increment_usage, get_user_plan
    from fastapi.responses import JSONResponse
    if not check_usage_limit(db, current_user.id, "practice_generate"):
        plan = get_user_plan(db, current_user.id)
        return JSONResponse(
            status_code=403,
            content={
                "error": "usage_limit_exceeded",
                "message": "You have reached your free monthly practice generation limit.",
                "plan": plan,
                "upgrade_options": ["plus", "pro"]
            }
        )

    try:
        questions = await generate_practice_questions(
            db,
            course_id=course_id,
            topic_id=req.topic_id,
            count=req.count or 5,
            difficulty=req.difficulty or "medium",
            provider=req.provider or "auto",
            model=req.model
        )
        
        # Increment usage counter
        increment_usage(db, current_user.id, "practice_generate")
        return questions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate practice questions: {str(e)}"
        )

@router.get("", response_model=list[PracticeQuestionResponse])
def get_practice_questions_endpoint(
    course_id: int,
    topic_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _verify_course(db, course_id, current_user.id)
    query = db.query(PracticeQuestion).filter(PracticeQuestion.course_id == course_id)
    if topic_id is not None:
        query = query.filter(PracticeQuestion.topic_id == topic_id)
    return query.all()

@router.post("/{question_id}/attempt", response_model=PracticeAttemptResponse)
async def grade_attempt_endpoint(
    course_id: int,
    question_id: int,
    req: PracticeAttemptGradeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _verify_course(db, course_id, current_user.id)
    try:
        attempt = await grade_practice_attempt(
            db,
            user_id=current_user.id,
            course_id=course_id,
            practice_question_id=question_id,
            student_answer=req.student_answer,
            provider=req.provider or "auto",
            model=req.model
        )
        
        # Log study activity for practice attempts
        from backend.services.activity_service import log_study_activity
        log_study_activity(
            db, 
            current_user.id, 
            "practice_attempt", 
            course_id, 
            metadata={"question_id": question_id, "score": attempt.score}
        )
        
        return attempt
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to grade attempt: {str(e)}"
        )

@router.get("/attempts", response_model=list[PracticeAttemptResponse])
def get_attempts_endpoint(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _verify_course(db, course_id, current_user.id)
    return db.query(PracticeAttempt).filter(
        PracticeAttempt.course_id == course_id,
        PracticeAttempt.user_id == current_user.id
    ).all()
