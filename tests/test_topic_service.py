import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import Course, CourseTopic, DocumentChunk, TopicChunkMap
from backend.services.topic_service import (
    create_topic,
    get_course_topics,
    map_chunks_to_topics,
    extract_topics_for_course
)
from unittest.mock import patch

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    
    # Create a dummy course
    course = Course(id=1, user_id=1, name="Test Course", code="TEST101")
    session.add(course)
    session.commit()
    
    try:
        yield session
    finally:
        session.close()

def test_create_topic(db):
    # Test normal creation
    topic = create_topic(db, course_id=1, name="Introduction to SQL", description="Basic queries")
    assert topic.id is not None
    assert topic.name == "Introduction to SQL"
    assert topic.source == "manual"
    
    # Test duplicate prevention (case-insensitive and whitespace trimmed)
    dup = create_topic(db, course_id=1, name="  Introduction to SQL  ")
    assert dup.id == topic.id
    
    topics = get_course_topics(db, course_id=1)
    assert len(topics) == 1

def test_map_chunks_to_topics(db):
    # Create topic
    topic = create_topic(db, course_id=1, name="SQL Join", description="Inner/Outer joins")
    
    # Create chunks
    chunk_match = DocumentChunk(
        id=1, course_id=1, course_file_id=1, chunk_index=0,
        content="In this lecture we cover the SQL Join concept."
    )
    chunk_no_match = DocumentChunk(
        id=2, course_id=1, course_file_id=1, chunk_index=1,
        content="Different data types in database tables."
    )
    db.add(chunk_match)
    db.add(chunk_no_match)
    db.commit()
    
    # Test mapping
    res = map_chunks_to_topics(db, course_id=1)
    assert res["chunk_maps_created"] == 1
    
    mappings = db.query(TopicChunkMap).filter(TopicChunkMap.course_id == 1).all()
    assert len(mappings) == 1
    assert mappings[0].topic_id == topic.id
    assert mappings[0].document_chunk_id == 1

@pytest.mark.anyio
@patch("backend.agy.topic_extraction_agent.LLMRouter.chat")
async def test_extract_topics_for_course_fallback(mock_chat, db):
    # Mock LLM Router failing
    mock_chat.side_effect = Exception("LLM connection failed")
    
    # Add some chunks
    chunk = DocumentChunk(
        id=1, course_id=1, course_file_id=1, chunk_index=0,
        content="Syllabus topic: Introduction to Python syntax and variables."
    )
    db.add(chunk)
    db.commit()
    
    # Extract topics
    res = await extract_topics_for_course(db, course_id=1)
    assert "topics_created" in res
    assert res["topics_created"] > 0
    
    topics = get_course_topics(db, course_id=1)
    assert len(topics) > 0
