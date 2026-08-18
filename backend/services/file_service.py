import os
import re
import aiofiles
from fastapi import UploadFile
from sqlalchemy.orm import Session
from backend.models import CourseFile

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".pptx", ".png", ".jpg", ".jpeg"}

# Resolve local storage/uploads path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "storage", "uploads")

def sanitize_filename(filename: str) -> str:
    # 1. Block path traversal by taking basename
    base = os.path.basename(filename)
    # 2. Extract extension and name
    name_only, ext = os.path.splitext(base)
    # 3. Clean characters
    cleaned_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name_only)
    cleaned_ext = re.sub(r'[^a-zA-Z0-9\.]', '', ext)
    return f"{cleaned_name}{cleaned_ext}"

class FileService:
    @staticmethod
    def get_course_upload_dir(course_id: int) -> str:
        course_dir = os.path.join(UPLOAD_DIR, str(course_id))
        os.makedirs(course_dir, exist_ok=True)
        return course_dir

    @staticmethod
    async def upload_file(db: Session, course_id: int, file: UploadFile) -> CourseFile:
        orig_filename = file.filename or "unnamed_file"
        _, ext = os.path.splitext(orig_filename.lower())
        
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"File extension '{ext}' is not supported. "
                f"Supported types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        sanitized = sanitize_filename(orig_filename)
        course_dir = FileService.get_course_upload_dir(course_id)
        file_path = os.path.join(course_dir, sanitized)
        
        # Avoid collisions
        counter = 1
        name_only, extension = os.path.splitext(sanitized)
        while os.path.exists(file_path):
            file_path = os.path.join(course_dir, f"{name_only}_{counter}{extension}")
            counter += 1

        final_filename = os.path.basename(file_path)

        # Async write to disk
        async with aiofiles.open(file_path, "wb") as out_file:
            while content := await file.read(1024 * 1024):  # 1MB chunks
                await out_file.write(content)

        # Store DB record
        db_file = CourseFile(
            course_id=course_id,
            filename=final_filename,
            original_filename=orig_filename,
            file_path=file_path,
            file_type=ext,
            processing_status="uploaded",
            extraction_status="pending",
            embedding_status="pending",
            chunk_count=0,
            embedded_count=0
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)

        return db_file


    @staticmethod
    def get_course_files(db: Session, course_id: int) -> list[CourseFile]:
        return db.query(CourseFile).filter(CourseFile.course_id == course_id).all()
