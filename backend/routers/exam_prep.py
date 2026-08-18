from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User
from backend.schemas import ExamPrepRequest, ExamPrepResponse
from backend.services.exam_service import ExamService
from backend.ai.llm_router import LLMRouter
from backend.agy.orchestrator import Orchestrator
from backend.deps import get_current_user

router = APIRouter(prefix="/courses", tags=["exam-prep"])

# Setup services
llm_router = LLMRouter()
orchestrator = Orchestrator(llm_router)
exam_service = ExamService(orchestrator)

@router.post("/{course_id}/exam-prep", response_model=ExamPrepResponse)
async def generate_exam_prep(
    course_id: int,
    request: ExamPrepRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check limit first
    from backend.services.usage_service import check_usage_limit, increment_usage, get_user_plan
    from fastapi.responses import JSONResponse
    if not check_usage_limit(db, current_user.id, "exam_prep_generate"):
        plan = get_user_plan(db, current_user.id)
        return JSONResponse(
            status_code=403,
            content={
                "error": "usage_limit_exceeded",
                "message": "You have reached your free monthly exam prep generation limit.",
                "plan": plan,
                "upgrade_options": ["plus", "pro"]
            }
        )

    try:
        response = await exam_service.generate_exam_prep(db, course_id, current_user.id, request)
        # Increment usage counter
        increment_usage(db, current_user.id, "exam_prep_generate")
        # Log study activity
        from backend.services.activity_service import log_study_activity
        log_study_activity(db, current_user.id, "exam_prep_generated", course_id)
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Exam prep generation failed: {str(e)}"
        )
