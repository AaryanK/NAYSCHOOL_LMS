from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User
from backend.schemas import TutorAskRequest, TutorAskResponse
from backend.services.tutor_service import TutorService
from backend.ai.llm_router import LLMRouter
from backend.agy.orchestrator import Orchestrator
from backend.deps import get_current_user

from typing import List, Any
from fastapi.responses import JSONResponse
from backend.models import ChatSession, Course
from backend.schemas import (
    TutorAskRequest, TutorAskResponse, 
    ChatSessionCreate, ChatSessionResponse, ChatSessionDetailResponse
)
from backend.services.usage_service import check_usage_limit, increment_usage, get_user_plan

router = APIRouter(prefix="/courses", tags=["tutor"])

# Setup services
llm_router = LLMRouter()
orchestrator = Orchestrator(llm_router)
tutor_service = TutorService(orchestrator)

@router.post("/{course_id}/tutor/ask", response_model=TutorAskResponse)
async def ask_tutor(
    course_id: int,
    request: TutorAskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verify course ownership
    course = db.query(Course).filter(Course.id == course_id, Course.user_id == current_user.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found or unauthorized access.")

    # 2. Check usage limit
    if not check_usage_limit(db, current_user.id, "tutor_ask"):
        plan = get_user_plan(db, current_user.id)
        return JSONResponse(
            status_code=403,
            content={
                "error": "usage_limit_exceeded",
                "message": "You have reached your free monthly tutor question limit.",
                "plan": plan,
                "upgrade_options": ["plus", "pro"]
            }
        )

    try:
        response = await tutor_service.ask_tutor(db, course_id, current_user.id, request)
        # 3. Increment usage counter
        increment_usage(db, current_user.id, "tutor_ask")
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tutor query failed: {str(e)}"
        )

@router.get("/{course_id}/chat-sessions", response_model=List[ChatSessionResponse])
def get_chat_sessions(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = db.query(Course).filter(Course.id == course_id, Course.user_id == current_user.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found or unauthorized access.")
    
    sessions = db.query(ChatSession).filter(
        ChatSession.course_id == course_id
    ).order_by(ChatSession.created_at.desc()).all()
    return sessions

@router.post("/{course_id}/chat-sessions", response_model=ChatSessionResponse)
def create_chat_session(
    course_id: int,
    request: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = db.query(Course).filter(Course.id == course_id, Course.user_id == current_user.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found or unauthorized access.")
    
    title = request.title or f"Chat Session for {course.name}"
    session = ChatSession(course_id=course_id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@router.get("/{course_id}/chat-sessions/{session_id}", response_model=ChatSessionDetailResponse)
def get_chat_session_detail(
    course_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = db.query(Course).filter(Course.id == course_id, Course.user_id == current_user.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found or unauthorized access.")
    
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.course_id == course_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    
    return session

@router.delete("/{course_id}/chat-sessions/{session_id}")
def delete_chat_session(
    course_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = db.query(Course).filter(Course.id == course_id, Course.user_id == current_user.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found or unauthorized access.")
    
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.course_id == course_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    
    db.delete(session)
    db.commit()
    return {"message": "Chat session deleted successfully."}
