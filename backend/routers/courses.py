from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, DocumentChunk
from backend.schemas import CourseCreate, CourseResponse, CourseSearchRequest, CourseSearchResponse, CourseSearchResult
from backend.services.course_service import CourseService
from backend.services.search_service import search_course_chunks
from backend.deps import get_current_user

router = APIRouter(prefix="/courses", tags=["courses"])

@router.get("", response_model=list[CourseResponse])
def get_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return CourseService.get_courses_by_user(db, current_user.id)

@router.post("", response_model=CourseResponse)
def create_course(
    course_in: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return CourseService.create_course(db, course_in, current_user.id)

@router.get("/{course_id}", response_model=CourseResponse)
def get_course(
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
    return course

@router.delete("/{course_id}")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    success = CourseService.delete_course(db, course_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or unauthorized access."
        )
    return {"message": "Course deleted successfully."}

@router.post("/{course_id}/search", response_model=CourseSearchResponse)
async def search_course(
    course_id: int,
    request: CourseSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = CourseService.get_course_by_id(db, course_id, current_user.id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or unauthorized access."
        )
    
    from backend.services.search_service import (
        search_course_chunks,
        semantic_search_course_chunks,
        hybrid_search_course_chunks
    )
    
    mode = request.mode or "hybrid"
    limit = request.limit or 5
    
    results = []
    actual_mode = mode
    
    try:
        if mode == "semantic":
            results = await semantic_search_course_chunks(db, course_id, request.query, limit=limit)
        elif mode == "hybrid":
            results = await hybrid_search_course_chunks(db, course_id, request.query, final_limit=limit)
        else: # keyword search
            kw_results = search_course_chunks(db, course_id, request.query, limit=limit)
            max_kw = max([r["score"] for r in kw_results]) if kw_results else 0.0
            results = [{
                "chunk_id": r["chunk_id"],
                "course_file_id": r["course_file_id"],
                "score": r["score"],
                "semantic_score": 0.0,
                "keyword_score": r["score"] / max_kw if max_kw > 0 else 0.0,
                "final_score": r["score"] / max_kw if max_kw > 0 else 0.0,
                "content": r["content"]
            } for r in kw_results]
    except Exception:
        actual_mode = "keyword_fallback"
        kw_results = search_course_chunks(db, course_id, request.query, limit=limit)
        max_kw = max([r["score"] for r in kw_results]) if kw_results else 0.0
        results = [{
            "chunk_id": r["chunk_id"],
            "course_file_id": r["course_file_id"],
            "score": r["score"],
            "semantic_score": 0.0,
            "keyword_score": r["score"] / max_kw if max_kw > 0 else 0.0,
            "final_score": r["score"] / max_kw if max_kw > 0 else 0.0,
            "content": r["content"]
        } for r in kw_results]
        
    mapped_results = [
        CourseSearchResult(
            chunk_id=r["chunk_id"],
            course_file_id=r["course_file_id"],
            score=r.get("final_score") or r.get("score") or 0.0,
            semantic_score=r.get("semantic_score"),
            keyword_score=r.get("keyword_score"),
            final_score=r.get("final_score"),
            content=r["content"]
        ) for r in results
    ]
    return CourseSearchResponse(mode=actual_mode, results=mapped_results)

from pydantic import BaseModel

class ForceEmbedRequest(BaseModel):
    force: bool = False

@router.post("/{course_id}/embed")
async def generate_course_embeddings(
    course_id: int,
    req_body: ForceEmbedRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = CourseService.get_course_by_id(db, course_id, current_user.id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or unauthorized access."
        )
        
    from backend.services.embedding_service import embed_course
    try:
        res = await embed_course(db, course_id, force=req_body.force)
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding generation failed: {str(e)}"
        )

@router.get("/{course_id}/embedding-status")
def get_course_embedding_status(
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
        
    from backend.config import settings
    chunks = db.query(DocumentChunk).filter(DocumentChunk.course_id == course_id).all()
    chunks_total = len(chunks)
    chunks_with_embeddings = len([c for c in chunks if c.embedding_json is not None])
    chunks_without_embeddings = chunks_total - chunks_with_embeddings
    
    return {
        "course_id": course_id,
        "chunks_total": chunks_total,
        "chunks_with_embeddings": chunks_with_embeddings,
        "chunks_without_embeddings": chunks_without_embeddings,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL
    }

@router.get("/{course_id}/chunks")
def get_course_chunks(
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
    
    chunks = db.query(DocumentChunk).filter(DocumentChunk.course_id == course_id).all()
    return [
        {
            "id": c.id,
            "course_file_id": c.course_file_id,
            "chunk_index": c.chunk_index,
            "length": len(c.content),
            "preview": c.content[:500]
        } for c in chunks
    ]

