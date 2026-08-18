import os
import pytest
import datetime
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db
from backend.models import Course, CourseFile, User, DocumentChunk
from backend.deps import get_current_user
from backend.services.ingestion_service import process_course_file

@pytest.fixture(name="db_session")
def fixture_db_session():
    # Use a temporary file-based SQLite DB to handle multi-threaded requests correctly
    db_file = "./test_temp_ingestion.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass
            
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Override close to prevent background tasks from destroying the test session
    original_close = db.close
    db.close = lambda: None
    
    try:
        yield db
    finally:
        original_close()
        engine.dispose()
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except Exception:
                pass

@pytest.fixture(name="client")
def fixture_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    # Mock user auth without is_active parameter which is not on the User model
    mock_user = User(id=1, email="test@nayschool.com", hashed_password="pw")
    db_session.add(mock_user)
    
    mock_course = Course(id=1, name="CS 101", code="CS101", instructor="Dr. Smith", user_id=1)
    db_session.add(mock_course)
    db_session.commit()

    def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    with TestClient(app) as c:
        yield c
        
    app.dependency_overrides.clear()

def test_course_file_model_status_fields():
    # Verify the new columns exist on CourseFile
    assert hasattr(CourseFile, "processing_status")
    assert hasattr(CourseFile, "extraction_status")
    assert hasattr(CourseFile, "embedding_status")
    assert hasattr(CourseFile, "chunk_count")
    assert hasattr(CourseFile, "embedded_count")
    assert hasattr(CourseFile, "processing_error")
    assert hasattr(CourseFile, "processed_at")

@pytest.mark.anyio
@patch("backend.services.ingestion_service.extract_text_from_file")
@patch("backend.services.ingestion_service.create_chunks_for_course_file")
async def test_process_course_file_unsupported(mock_chunk, mock_extract, db_session):
    mock_extract.side_effect = ValueError("Unsupported file extension: .xyz")
    
    # Insert test file
    cf = CourseFile(
        id=1,
        course_id=1,
        filename="test.xyz",
        original_filename="test.xyz",
        file_path="/fake/test.xyz",
        file_type=".xyz"
    )
    db_session.add(cf)
    db_session.commit()

    # Need to override SessionLocal used inside background process_course_file
    with patch("backend.services.ingestion_service.SessionLocal", return_value=db_session):
        res = await process_course_file(cf.id)
        
    assert res["status"] == "unsupported"
    
    # Reload from DB
    db_session.refresh(cf)
    assert cf.processing_status == "completed"
    assert cf.extraction_status == "unsupported"
    assert cf.embedding_status == "skipped"
    assert cf.chunk_count == 0
    assert cf.embedded_count == 0
    assert cf.processed_at is not None

@pytest.mark.anyio
@patch("backend.services.ingestion_service.extract_text_from_file")
@patch("backend.services.ingestion_service.create_chunks_for_course_file")
@patch("backend.services.embedding_service.embed_chunks_for_course_file")
async def test_process_course_file_success(mock_embed, mock_chunk, mock_extract, db_session):
    mock_extract.return_value = "This is a great chunked file content."
    mock_chunk.return_value = 2
    mock_embed.return_value = {"chunks_embedded": 2, "errors": []}
    
    cf = CourseFile(
        id=2,
        course_id=1,
        filename="test.txt",
        original_filename="test.txt",
        file_path="/fake/test.txt",
        file_type=".txt"
    )
    db_session.add(cf)
    db_session.commit()

    with patch("backend.services.ingestion_service.SessionLocal", return_value=db_session):
        res = await process_course_file(cf.id)

    assert res["status"] == "completed"
    
    db_session.refresh(cf)
    assert cf.processing_status == "completed"
    assert cf.extraction_status == "success"
    assert cf.embedding_status == "success"
    assert cf.chunk_count == 2
    assert cf.embedded_count == 2
    assert cf.processed_at is not None

def test_get_file_status_endpoint(client, db_session):
    cf = CourseFile(
        id=10,
        course_id=1,
        filename="notes.pdf",
        original_filename="notes.pdf",
        file_path="/fake/notes.pdf",
        file_type=".pdf",
        processing_status="completed",
        extraction_status="success",
        embedding_status="success",
        chunk_count=15,
        embedded_count=15,
        processed_at=datetime.datetime.utcnow()
    )
    db_session.add(cf)
    db_session.commit()

    resp = client.get("/api/courses/1/files/10/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["file_id"] == 10
    assert data["processing_status"] == "completed"
    assert data["chunk_count"] == 15
    assert data["embedded_count"] == 15

def test_get_ingestion_status_summary_endpoint(client, db_session):
    cf1 = CourseFile(
        id=11, course_id=1, filename="notes1.pdf", original_filename="notes1.pdf",
        file_path="/fake/notes1.pdf", file_type=".pdf", processing_status="completed",
        extraction_status="success", embedding_status="success", chunk_count=5, embedded_count=5
    )
    cf2 = CourseFile(
        id=12, course_id=1, filename="notes2.pdf", original_filename="notes2.pdf",
        file_path="/fake/notes2.pdf", file_type=".pdf", processing_status="failed",
        extraction_status="failed", embedding_status="failed", chunk_count=0, embedded_count=0,
        processing_error="Extraction failed: read error"
    )
    cf3 = CourseFile(
        id=13, course_id=1, filename="notes3.pdf", original_filename="notes3.pdf",
        file_path="/fake/notes3.pdf", file_type=".pdf", processing_status="extracting",
        extraction_status="pending", embedding_status="pending", chunk_count=0, embedded_count=0
    )
    db_session.add_all([cf1, cf2, cf3])
    db_session.commit()

    resp = client.get("/api/courses/1/ingestion-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["course_id"] == 1
    assert data["files_total"] == 3
    assert data["completed"] == 1
    assert data["processing"] == 1
    assert data["failed"] == 1
    assert data["chunks_total"] == 5
    assert data["embedded_total"] == 5
    assert len(data["files"]) == 3

def test_reprocess_file_endpoint(client, db_session):
    cf = CourseFile(
        id=20,
        course_id=1,
        filename="reprocess.pdf",
        original_filename="reprocess.pdf",
        file_path="/fake/reprocess.pdf",
        file_type=".pdf",
        processing_status="completed",
        extraction_status="success",
        embedding_status="success",
        chunk_count=10,
        embedded_count=10
    )
    chunk = DocumentChunk(
        id=50,
        course_file_id=20,
        course_id=1,
        chunk_index=0,
        content="reprocess chunk text"
    )
    db_session.add_all([cf, chunk])
    db_session.commit()

    with patch("backend.routers.uploads.BackgroundTasks.add_task") as mock_add_task:
        resp = client.post("/api/courses/1/files/20/reprocess", json={"force_embeddings": True})
        assert resp.status_code == 200
        mock_add_task.assert_called_once()
        
    db_session.refresh(cf)
    assert cf.processing_status == "uploaded"
    assert cf.extraction_status == "pending"
    assert cf.embedding_status == "pending"
    assert cf.chunk_count == 0
    assert cf.embedded_count == 0
    
    # Old chunk should be deleted
    assert db_session.query(DocumentChunk).filter(DocumentChunk.course_file_id == 20).count() == 0
