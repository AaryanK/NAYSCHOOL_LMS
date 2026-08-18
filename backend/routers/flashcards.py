from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User
from backend.schemas import FlashcardGenerateRequest, FlashcardGenerateResponse, FlashcardResponse
from backend.services.flashcard_service import FlashcardService
from backend.services.course_service import CourseService
from backend.ai.llm_router import LLMRouter
from backend.agy.orchestrator import Orchestrator
from backend.deps import get_current_user

router = APIRouter(prefix="/courses", tags=["flashcards"])

# Setup services
llm_router = LLMRouter()
orchestrator = Orchestrator(llm_router)
flashcard_service = FlashcardService(orchestrator)

@router.post("/{course_id}/flashcards/generate", response_model=FlashcardGenerateResponse)
async def generate_flashcards(
    course_id: int,
    request: FlashcardGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        response = await flashcard_service.generate_flashcards(db, course_id, current_user.id, request)
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Flashcard generation failed: {str(e)}"
        )

@router.get("/{course_id}/flashcards", response_model=list[FlashcardResponse])
def get_flashcards(
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
    return FlashcardService.get_course_flashcards(db, course_id)
