import pytest
import json
from unittest.mock import patch
from backend.services.search_service import (
    cosine_similarity,
    semantic_search_course_chunks,
    hybrid_search_course_chunks,
    search_course_chunks
)
from backend.models import DocumentChunk
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

def test_cosine_similarity_ordering():
    a = [1.0, 0.0]
    b = [1.0, 0.0]
    c = [0.0, 1.0]
    d = [-1.0, 0.0]
    
    sim_ab = cosine_similarity(a, b)
    sim_ac = cosine_similarity(a, c)
    sim_ad = cosine_similarity(a, d)
    
    assert sim_ab > sim_ac
    assert sim_ac > sim_ad
    assert abs(sim_ab - 1.0) < 1e-6
    assert abs(sim_ac - 0.0) < 1e-6
    assert abs(sim_ad - (-1.0)) < 1e-6

@pytest.mark.anyio
@patch("backend.services.embedding_service.embed_query")
async def test_semantic_search_ignores_chunks_without_embeddings(mock_embed_query, db_session):
    mock_embed_query.return_value = [1.0, 0.0]
    
    chunk1 = DocumentChunk(
        id=1,
        course_file_id=1,
        course_id=1,
        chunk_index=0,
        content="Match me",
        embedding_json="[1.0, 0.0]"
    )
    chunk2 = DocumentChunk(
        id=2,
        course_file_id=1,
        course_id=1,
        chunk_index=1,
        content="Ignore me",
        embedding_json=None
    )
    db_session.add_all([chunk1, chunk2])
    db_session.commit()
    
    results = await semantic_search_course_chunks(db_session, course_id=1, query="match", limit=5)
    
    assert len(results) == 1
    assert results[0]["chunk_id"] == 1
    assert results[0]["score_type"] == "semantic"

@pytest.mark.anyio
@patch("backend.services.embedding_service.embed_query")
async def test_hybrid_search_merge(mock_embed_query, db_session):
    mock_embed_query.return_value = [1.0, 0.0]
    
    chunk1 = DocumentChunk(
        id=1,
        course_file_id=1,
        course_id=1,
        chunk_index=0,
        content="UniqueKeywordTerm to test search",
        embedding_json="[0.0, 1.0]"
    )
    chunk2 = DocumentChunk(
        id=2,
        course_file_id=1,
        course_id=1,
        chunk_index=1,
        content="Different words, but conceptually same",
        embedding_json="[0.9, 0.1]"
    )
    chunk3 = DocumentChunk(
        id=3,
        course_file_id=1,
        course_id=1,
        chunk_index=2,
        content="UniqueKeywordTerm with high alignment",
        embedding_json="[1.0, 0.0]"
    )
    db_session.add_all([chunk1, chunk2, chunk3])
    db_session.commit()
    
    results = await hybrid_search_course_chunks(
        db=db_session,
        course_id=1,
        query="UniqueKeywordTerm",
        semantic_limit=5,
        keyword_limit=5,
        final_limit=5
    )
    
    assert len(results) >= 2
    assert results[0]["chunk_id"] == 3
    assert results[0]["semantic_score"] > 0.8
    assert results[0]["keyword_score"] > 0.0

@pytest.mark.anyio
@patch("backend.services.embedding_service.embed_query")
async def test_keyword_fallback_if_embeddings_fail(mock_embed_query, db_session):
    mock_embed_query.side_effect = Exception("Embedding provider offline")
    
    chunk = DocumentChunk(
        id=1,
        course_file_id=1,
        course_id=1,
        chunk_index=0,
        content="Fallback target content to find"
    )
    db_session.add(chunk)
    db_session.commit()
    
    results = await hybrid_search_course_chunks(
        db=db_session,
        course_id=1,
        query="Fallback target content",
        semantic_limit=5,
        keyword_limit=5,
        final_limit=5
    )
    
    assert len(results) == 1
    assert results[0]["chunk_id"] == 1
    assert results[0]["semantic_score"] == 0.0
    assert results[0]["keyword_score"] > 0.0
