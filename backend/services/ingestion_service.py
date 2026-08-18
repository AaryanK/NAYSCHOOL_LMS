import datetime
import logging
from backend.database import SessionLocal
from backend.models import CourseFile
from backend.services.document_service import extract_text_from_file, create_chunks_for_course_file
from backend.config import settings

logger = logging.getLogger(__name__)

async def process_course_file(course_file_id: int) -> dict:
    """
    Background job to ingest a CourseFile. It extracts text, chunks it,
    saves the chunks, and optionally runs embeddings.
    """
    db = SessionLocal()
    try:
        course_file = db.query(CourseFile).filter(CourseFile.id == course_file_id).first()
        if not course_file:
            logger.error(f"CourseFile with ID {course_file_id} not found in database.")
            return {"status": "error", "message": f"CourseFile {course_file_id} not found"}

        logger.info(f"Starting ingestion background job for CourseFile: {course_file.filename}")

        # Set status to extracting
        course_file.processing_status = "extracting"
        course_file.extraction_status = "pending"
        course_file.embedding_status = "pending"
        course_file.processing_error = None
        db.commit()

        # Try to extract text
        try:
            extracted_text = extract_text_from_file(course_file.file_path, course_file.file_type)
        except ValueError as val_err:
            course_file.extraction_status = "unsupported"
            course_file.processing_status = "completed"
            course_file.embedding_status = "skipped"
            course_file.chunk_count = 0
            course_file.embedded_count = 0
            course_file.processed_at = datetime.datetime.utcnow()
            db.commit()
            return {"status": "unsupported", "message": str(val_err)}
        except Exception as parse_err:
            course_file.extraction_status = "failed"
            course_file.processing_status = "failed"
            course_file.processing_error = f"Extraction failed: {str(parse_err)}"
            course_file.processed_at = datetime.datetime.utcnow()
            db.commit()
            return {"status": "failed", "message": str(parse_err)}

        if not extracted_text.strip():
            course_file.extraction_status = "success"
            course_file.processing_status = "completed"
            course_file.embedding_status = "skipped"
            course_file.chunk_count = 0
            course_file.embedded_count = 0
            course_file.processed_at = datetime.datetime.utcnow()
            db.commit()
            return {"status": "completed", "message": "File was empty, no chunks created"}

        # 2. Chunking
        course_file.processing_status = "chunking"
        db.commit()
        
        try:
            chunk_count = create_chunks_for_course_file(db, course_file, extracted_text)
            course_file.chunk_count = chunk_count
            course_file.extraction_status = "success"
            db.commit()
        except Exception as chunk_err:
            course_file.processing_status = "failed"
            course_file.processing_error = f"Chunking failed: {str(chunk_err)}"
            course_file.processed_at = datetime.datetime.utcnow()
            db.commit()
            return {"status": "failed", "message": str(chunk_err)}

        # 3. Embedding
        embedded_count = 0
        embedding_status = "skipped"
        if chunk_count > 0 and settings.AUTO_EMBED_ON_UPLOAD:
            course_file.processing_status = "embedding"
            db.commit()
            
            from backend.services.embedding_service import embed_chunks_for_course_file
            try:
                embed_res = await embed_chunks_for_course_file(db, course_file.id)
                embedded_count = embed_res.get("chunks_embedded", 0)
                errors = embed_res.get("errors", [])
                if errors:
                    embedding_status = "failed" if embedded_count == 0 else "partial"
                    course_file.processing_error = f"Embeddings generation error: {'; '.join(errors)}"
                    course_file.processing_status = "partial"
                else:
                    embedding_status = "success"
                    course_file.processing_status = "completed"
            except Exception as embed_err:
                embedding_status = "failed"
                course_file.processing_error = f"Embedding error: {str(embed_err)}"
                course_file.processing_status = "partial"
        else:
            course_file.processing_status = "completed"

        course_file.embedding_status = embedding_status
        course_file.embedded_count = embedded_count
        course_file.processed_at = datetime.datetime.utcnow()
        db.commit()
        
        return {
            "status": course_file.processing_status,
            "chunk_count": chunk_count,
            "embedded_count": embedded_count
        }

    except Exception as general_err:
        logger.exception("General failure in background file ingestion task.")
        try:
            course_file = db.query(CourseFile).filter(CourseFile.id == course_file_id).first()
            if course_file:
                course_file.processing_status = "failed"
                course_file.processing_error = f"General failure: {str(general_err)}"
                course_file.processed_at = datetime.datetime.utcnow()
                db.commit()
        except Exception:
            pass
        return {"status": "error", "message": str(general_err)}
    finally:
        db.close()
