import pytest
import json
from unittest.mock import patch
from backend.services.embedding_service import (
    embed_chunk,
    embed_chunks_for_course_file,
    embed_course,
    embed_query
)
from backend.models import DocumentChunk, CourseFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.mark.anyio
@patch("backend.services.embedding_service.router.embed_texts")
async def test_embed_chunk_success(mock_embed, db_session):
    mock_embed.return_value = {
        "provider": "ollama",
        "model": "nomic-embed-text",
        "dimension": 3,
        "embeddings": [[0.1, 0.2, 0.3]]
    }
    
    chunk = DocumentChunk(
        id=1,
        course_file_id=1,
        course_id=1,
        chunk_index=0,
        content="hello world"
    )
    db_session.add(chunk)
    db_session.commit()
    
    res = await embed_chunk(db_session, chunk)
    assert res["status"] == "success"
    assert chunk.embedding_json is not None
    assert json.loads(chunk.embedding_json) == [0.1, 0.2, 0.3]
    assert chunk.embedding_dimension == 3
    assert chunk.embedding_model == "nomic-embed-text"

@pytest.mark.anyio
@patch("backend.services.embedding_service.router.embed_texts")
async def test_embed_chunks_for_course_file(mock_embed, db_session):
    mock_embed.return_value = {
        "provider": "ollama",
        "model": "nomic-embed-text",
        "dimension": 3,
        "embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    }
    
    file = CourseFile(id=2, course_id=1, filename="test.txt", original_filename="test.txt", file_path="t")
    db_session.add(file)
    
    chunk1 = DocumentChunk(id=2, course_file_id=2, course_id=1, chunk_index=0, content="chunk one")
    chunk2 = DocumentChunk(id=3, course_file_id=2, course_id=1, chunk_index=1, content="chunk two")
    db_session.add_all([chunk1, chunk2])
    db_session.commit()
    
    status = await embed_chunks_for_course_file(db_session, course_file_id=2)
    assert status["chunks_total"] == 2
    assert status["chunks_embedded"] == 2
    assert chunk1.embedding_json is not None
    assert chunk2.embedding_json is not None

@pytest.mark.anyio
@patch("backend.services.embedding_service.router.embed_texts")
async def test_embed_course_force(mock_embed, db_session):
    mock_embed.return_value = {
        "provider": "ollama",
        "model": "nomic-embed-text",
        "dimension": 3,
        "embeddings": [[0.1, 0.2, 0.3]]
    }
    
    chunk = DocumentChunk(
        id=4,
        course_file_id=2,
        course_id=1,
        chunk_index=0,
        content="test content",
        embedding_json="[0.0, 0.0, 0.0]"
    )
    db_session.add(chunk)
    db_session.commit()
    
    res = await embed_course(db_session, course_id=1, force=False)
    assert res["chunks_skipped"] == 1
    assert res["chunks_embedded"] == 0
    
    res = await embed_course(db_session, course_id=1, force=True)
    assert res["chunks_embedded"] == 1
    assert res["chunks_skipped"] == 0

@pytest.mark.anyio
@patch("backend.services.embedding_service.router.embed_texts")
async def test_embed_query(mock_embed):
    mock_embed.return_value = {
        "provider": "ollama",
        "model": "nomic-embed-text",
        "dimension": 3,
        "embeddings": [[0.9, 0.8, 0.7]]
    }
    vec = await embed_query("search query")
    assert vec == [0.9, 0.8, 0.7]
