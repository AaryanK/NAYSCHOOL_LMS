from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, CourseTopic
from backend.schemas import (
    CourseTopicCreate,
    CourseTopicResponse,
    TopicExtractionRequest
)
from backend.services.course_service import CourseService
from backend.services.topic_service import (
    get_course_topics,
    create_topic,
    extract_topics_for_course,
    map_chunks_to_topics
)
from backend.deps import get_current_user

router = APIRouter(prefix="/courses/{course_id}/topics", tags=["topics"])

def _verify_course(db: Session, course_id: int, user_id: int):
    course = CourseService.get_course_by_id(db, course_id, user_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or unauthorized access."
        )
    return course

@router.get("", response_model=list[CourseTopicResponse])
def get_topics_endpoint(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _verify_course(db, course_id, current_user.id)
    return get_course_topics(db, course_id)

@router.post("", response_model=CourseTopicResponse)
def create_topic_endpoint(
    course_id: int,
    topic_in: CourseTopicCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _verify_course(db, course_id, current_user.id)
    return create_topic(
        db,
        course_id=course_id,
        name=topic_in.name,
        description=topic_in.description,
        source=topic_in.source or "manual"
    )

@router.post("/extract")
async def extract_topics_endpoint(
    course_id: int,
    req: TopicExtractionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _verify_course(db, course_id, current_user.id)
    try:
        res = await extract_topics_for_course(
            db,
            course_id=course_id,
            provider=req.provider or "auto",
            model=req.model
        )
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract topics: {str(e)}"
        )

@router.post("/map-chunks")
def map_chunks_endpoint(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _verify_course(db, course_id, current_user.id)
    return map_chunks_to_topics(db, course_id)

@router.get("/{topic_id}", response_model=CourseTopicResponse)
def get_topic_detail_endpoint(
    course_id: int,
    topic_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _verify_course(db, course_id, current_user.id)
    topic = db.query(CourseTopic).filter(
        CourseTopic.id == topic_id,
        CourseTopic.course_id == course_id
    ).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found in this course."
        )
    return topic
