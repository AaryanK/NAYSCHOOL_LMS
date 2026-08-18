from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User
from backend.schemas import AssignmentCreate, AssignmentUpdate, AssignmentResponse
from backend.services.assignment_service import AssignmentService
from backend.services.course_service import CourseService
from backend.deps import get_current_user

course_router = APIRouter(prefix="/courses", tags=["course-assignments"])
router = APIRouter(prefix="/assignments", tags=["assignments"])

@course_router.get("/{course_id}/assignments", response_model=list[AssignmentResponse])
def get_assignments(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = CourseService.get_course_by_id(db, course_id, current_user.id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or unauthorized access."
        )
    return AssignmentService.get_assignments_by_course(db, course_id)

@course_router.post("/{course_id}/assignments", response_model=AssignmentResponse)
def create_assignment(
    course_id: int,
    assignment_in: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = CourseService.get_course_by_id(db, course_id, current_user.id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or unauthorized access."
        )
    return AssignmentService.create_assignment(db, course_id, assignment_in)

@router.patch("/{assignment_id}", response_model=AssignmentResponse)
def update_assignment(
    assignment_id: int,
    assignment_in: AssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    assign = AssignmentService.get_assignment_by_id(db, assignment_id)
    if not assign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found."
        )
    
    course = CourseService.get_course_by_id(db, assign.course_id, current_user.id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access to assignment's course."
        )
    
    return AssignmentService.update_assignment(db, assignment_id, assignment_in)
