from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, CourseFile
from backend.schemas import (
    CourseFileResponse,
    CourseFileUploadResponse,
    CourseFileStatusResponse,
    CourseIngestionStatusSummary
)
from backend.services.file_service import FileService
from backend.services.course_service import CourseService
from backend.deps import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/courses", tags=["uploads"])

@router.post("/{course_id}/upload", response_model=CourseFileUploadResponse)
async def upload_course_file(
    course_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = CourseService.get_course_by_id(db, course_id, current_user.id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or unauthorized access."
        )

    # Check upload usage limit
    from backend.services.usage_service import check_usage_limit, increment_usage, get_user_plan
    from fastapi.responses import JSONResponse
    if not check_usage_limit(db, current_user.id, "upload"):
        plan = get_user_plan(db, current_user.id)
        return JSONResponse(
            status_code=403,
            content={
                "error": "usage_limit_exceeded",
                "message": "You have reached your free monthly upload limit.",
                "plan": plan,
                "upgrade_options": ["plus", "pro"]
            }
        )

    try:
        db_file = await FileService.upload_file(db, course_id, file)
        
        # Increment upload limit counter
        increment_usage(db, current_user.id, "upload")
        
        # Log study activity
        from backend.services.activity_service import log_study_activity
        log_study_activity(db, current_user.id, "file_uploaded", course_id)
        
        # Trigger background processing task
        from backend.services.ingestion_service import process_course_file
        background_tasks.add_task(process_course_file, db_file.id)
        
        status_url = f"/api/courses/{course_id}/files/{db_file.id}/status"
        return CourseFileUploadResponse(
            file=db_file,
            message="File uploaded. Processing started in the background.",
            processing_status="uploaded",
            status_url=status_url
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )

@router.get("/{course_id}/files", response_model=list[CourseFileResponse])
def get_course_files(
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
    return FileService.get_course_files(db, course_id)

@router.get("/{course_id}/files/{file_id}/status", response_model=CourseFileStatusResponse)
def get_file_status(
    course_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = CourseService.get_course_by_id(db, course_id, current_user.id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or unauthorized access."
        )
    
    cf = db.query(CourseFile).filter(CourseFile.id == file_id, CourseFile.course_id == course_id).first()
    if not cf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course file not found."
        )
        
    return CourseFileStatusResponse(
        file_id=cf.id,
        course_id=cf.course_id,
        filename=cf.filename,
        processing_status=cf.processing_status,
        extraction_status=cf.extraction_status,
        embedding_status=cf.embedding_status,
        chunk_count=cf.chunk_count,
        embedded_count=cf.embedded_count,
        processing_error=cf.processing_error,
        processed_at=cf.processed_at
    )

class ReprocessRequest(BaseModel):
    force_embeddings: bool = False

@router.post("/{course_id}/files/{file_id}/reprocess", response_model=CourseFileStatusResponse)
async def reprocess_file(
    course_id: int,
    file_id: int,
    background_tasks: BackgroundTasks,
    request: ReprocessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = CourseService.get_course_by_id(db, course_id, current_user.id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or unauthorized access."
        )
    
    cf = db.query(CourseFile).filter(CourseFile.id == file_id, CourseFile.course_id == course_id).first()
    if not cf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course file not found."
        )
        
    # Delete existing chunks for this file
    from backend.models import DocumentChunk
    db.query(DocumentChunk).filter(DocumentChunk.course_file_id == file_id).delete()
    
    # Reset status fields
    cf.processing_status = "uploaded"
    cf.extraction_status = "pending"
    cf.embedding_status = "pending"
    cf.chunk_count = 0
    cf.embedded_count = 0
    cf.processing_error = None
    cf.processed_at = None
    
    db.commit()
    db.refresh(cf)
    
    # Trigger background task
    from backend.services.ingestion_service import process_course_file
    background_tasks.add_task(process_course_file, cf.id)
    
    return CourseFileStatusResponse(
        file_id=cf.id,
        course_id=cf.course_id,
        filename=cf.filename,
        processing_status=cf.processing_status,
        extraction_status=cf.extraction_status,
        embedding_status=cf.embedding_status,
        chunk_count=cf.chunk_count,
        embedded_count=cf.embedded_count,
        processing_error=cf.processing_error,
        processed_at=cf.processed_at
    )

@router.get("/{course_id}/ingestion-status", response_model=CourseIngestionStatusSummary)
def get_course_ingestion_status(
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
        
    files = db.query(CourseFile).filter(CourseFile.course_id == course_id).all()
    
    files_total = len(files)
    completed = 0
    processing = 0
    failed = 0
    chunks_total = 0
    embedded_total = 0
    
    files_status_list = []
    for cf in files:
        if cf.processing_status == "completed":
            completed += 1
        elif cf.processing_status in ["uploaded", "extracting", "chunking", "embedding"]:
            processing += 1
        elif cf.processing_status == "failed":
            failed += 1
        elif cf.processing_status == "partial":
            completed += 1
            
        chunks_total += cf.chunk_count
        embedded_total += cf.embedded_count
        
        files_status_list.append(
            CourseFileStatusResponse(
                file_id=cf.id,
                course_id=cf.course_id,
                filename=cf.filename,
                processing_status=cf.processing_status,
                extraction_status=cf.extraction_status,
                embedding_status=cf.embedding_status,
                chunk_count=cf.chunk_count,
                embedded_count=cf.embedded_count,
                processing_error=cf.processing_error,
                processed_at=cf.processed_at
            )
        )
        
    return CourseIngestionStatusSummary(
        course_id=course_id,
        files_total=files_total,
        completed=completed,
        processing=processing,
        failed=failed,
        chunks_total=chunks_total,
        embedded_total=embedded_total,
        files=files_status_list
    )
