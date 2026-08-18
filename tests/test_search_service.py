from backend.services.search_service import search_course_chunks
from backend.models import DocumentChunk
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base

def test_search_scoring_logic():
    # Establish an in-memory SQL database session to test retrieval logic
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Create test mock passages
        chunk1 = DocumentChunk(
            id=1,
            course_file_id=5,
            course_id=50,
            chunk_index=0,
            content="Binary search operates in logarithmic O(log n) time complexity by dividing arrays."
        )
        chunk2 = DocumentChunk(
            id=2,
            course_file_id=5,
            course_id=50,
            chunk_index=1,
            content="Linear search has O(n) complexity, checking elements sequentially one-by-one."
        )
        db.add(chunk1)
        db.add(chunk2)
        db.commit()
        
        # Test exact phrase match boost
        results = search_course_chunks(db, course_id=50, query="logarithmic O(log n)")
        assert len(results) == 1
        assert results[0]["chunk_id"] == 1
        assert results[0]["score"] >= 5  # Phrase match boost points applied
        
        # Test term frequencies sorting
        results_t = search_course_chunks(db, course_id=50, query="linear complexity")
        # Both contain 'complexity', chunk2 has 'linear' + 'complexity'
        assert len(results_t) == 2
        assert results_t[0]["chunk_id"] == 2
        assert results_t[0]["score"] > results_t[1]["score"]
        
    finally:
        db.close()
