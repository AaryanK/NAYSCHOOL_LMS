from backend.models import DocumentChunk
from backend.services.document_service import chunk_text

def test_document_chunk_model_import():
    # Verify all columns are present on the model class
    assert hasattr(DocumentChunk, "id")
    assert hasattr(DocumentChunk, "course_file_id")
    assert hasattr(DocumentChunk, "course_id")
    assert hasattr(DocumentChunk, "chunk_index")
    assert hasattr(DocumentChunk, "content")
    assert hasattr(DocumentChunk, "created_at")

def test_chunk_text_basic():
    sample_text = (
        "Binary search is an efficient algorithm for finding an item from a sorted list of items. "
        "It works by repeatedly dividing in half the portion of the list that could contain the item, "
        "until you have narrowed down the possible locations to just one."
    )
    chunks = chunk_text(sample_text, max_chars=80, overlap=15)
    assert len(chunks) > 0
    for chunk in chunks:
        assert len(chunk) > 0
        # No duplicate continuous spaces
        assert "  " not in chunk
