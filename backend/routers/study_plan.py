from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User
from backend.schemas import (
    StudyPlanTaskCreate,
    StudyPlanTaskResponse,
    StudyPlanTaskUpdate
)
from backend.services.course_service import CourseService
from backend.services.study_plan_service import (
    get_study_tasks,
    create_study_task,
    update_study_task,
    generate_study_tasks_from_weaknesses
)
from backend.deps import get_current_user
from pydantic import BaseModel

router = APIRouter(tags=["study-tasks"])

class GenerateTasksRequest(BaseModel):
    days: int = 7

def _verify_course(db: Session, course_id: int, user_id: int):
    course = CourseService.get_course_by_id(db, course_id, user_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or unauthorized access."
        )
    return course

@router.get("/courses/{course_id}/study-tasks", response_model=list[StudyPlanTaskResponse])
def get_study_tasks_endpoint(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _verify_course(db, course_id, current_user.id)
    return get_study_tasks(db, current_user.id, course_id)

@router.post("/courses/{course_id}/study-tasks", response_model=StudyPlanTaskResponse)
def create_study_task_endpoint(
    course_id: int,
    task_in: StudyPlanTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _verify_course(db, course_id, current_user.id)
    return create_study_task(
        db,
        user_id=current_user.id,
        course_id=course_id,
        title=task_in.title,
        topic_id=task_in.topic_id,
        description=task_in.description,
        due_at=task_in.due_at,
        priority=task_in.priority or "medium",
        status=task_in.status or "pending"
    )

@router.post("/courses/{course_id}/study-tasks/generate", response_model=list[StudyPlanTaskResponse])
def generate_study_tasks_endpoint(
    course_id: int,
    req: GenerateTasksRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _verify_course(db, course_id, current_user.id)
    return generate_study_tasks_from_weaknesses(
        db,
        user_id=current_user.id,
        course_id=course_id,
        days=req.days
    )

@router.patch("/study-tasks/{task_id}", response_model=StudyPlanTaskResponse)
def update_study_task_endpoint(
    task_id: int,
    task_in: StudyPlanTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Service function checks that the task belongs to current_user
        updates = task_in.model_dump(exclude_unset=True)
        return update_study_task(db, current_user.id, task_id, updates)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
