import json
import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.models import DocumentChunk
from backend.ai.embeddings import EmbeddingRouter
from backend.config import settings

router = EmbeddingRouter()

async def embed_chunk(db: Session, chunk: DocumentChunk) -> dict:
    """
    Generate and save embedding for a single chunk if it doesn't already have one.
    """
    if chunk.embedding_json is not None:
        return {
            "status": "skipped",
            "provider": chunk.embedding_provider,
            "model": chunk.embedding_model,
            "dimension": chunk.embedding_dimension,
        }
    
    try:
        res = await router.embed_texts([chunk.content])
        embeddings = res.get("embeddings")
        if not embeddings or not embeddings[0]:
            raise ValueError("No embeddings returned by provider")
        
        vector = embeddings[0]
        chunk.embedding_json = json.dumps(vector)
        chunk.embedding_provider = res.get("provider")
        chunk.embedding_model = res.get("model")
        chunk.embedding_dimension = res.get("dimension")
        chunk.embedding_created_at = datetime.datetime.utcnow()
        
        db.commit()
        db.refresh(chunk)
        
        return {
            "status": "success",
            "provider": chunk.embedding_provider,
            "model": chunk.embedding_model,
            "dimension": chunk.embedding_dimension,
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "failed",
            "error": str(e)
        }

async def embed_chunks_for_course_file(db: Session, course_file_id: int) -> dict:
    """
    Generate and save embeddings for all chunks of a course file.
    Only processes chunks that do not already have embeddings.
    """
    all_chunks = db.query(DocumentChunk).filter(DocumentChunk.course_file_id == course_file_id).all()
    chunks_total = len(all_chunks)
    
    to_embed = [c for c in all_chunks if c.embedding_json is None]
    chunks_skipped = chunks_total - len(to_embed)
    
    chunks_embedded = 0
    errors = []
    
    if to_embed:
        batch_size = 32
        for i in range(0, len(to_embed), batch_size):
            batch = to_embed[i:i+batch_size]
            texts = [c.content for c in batch]
            try:
                res = await router.embed_texts(texts)
                embeddings = res.get("embeddings", [])
                if len(embeddings) != len(batch):
                    raise ValueError(f"Provider returned {len(embeddings)} embeddings for {len(batch)} chunks")
                
                for chunk, vector in zip(batch, embeddings):
                    chunk.embedding_json = json.dumps(vector)
                    chunk.embedding_provider = res.get("provider")
                    chunk.embedding_model = res.get("model")
                    chunk.embedding_dimension = res.get("dimension")
                    chunk.embedding_created_at = datetime.datetime.utcnow()
                    chunks_embedded += 1
                
                db.commit()
            except Exception as e:
                db.rollback()
                errors.append(str(e))
                break
                
    return {
        "chunks_total": chunks_total,
        "chunks_embedded": chunks_embedded,
        "chunks_skipped": chunks_skipped,
        "errors": errors
    }

async def embed_course(db: Session, course_id: int, force: bool = False) -> dict:
    """
    Generate embeddings for all chunks in a course.
    If force=True, resets and regenerates all embeddings.
    """
    all_chunks = db.query(DocumentChunk).filter(DocumentChunk.course_id == course_id).all()
    chunks_total = len(all_chunks)
    
    if force:
        for c in all_chunks:
            c.embedding_json = None
            c.embedding_provider = None
            c.embedding_model = None
            c.embedding_dimension = None
            c.embedding_created_at = None
        db.commit()
        
    to_embed = [c for c in all_chunks if c.embedding_json is None]
    chunks_skipped = chunks_total - len(to_embed)
    
    chunks_embedded = 0
    errors = []
    
    if to_embed:
        batch_size = 32
        for i in range(0, len(to_embed), batch_size):
            batch = to_embed[i:i+batch_size]
            texts = [c.content for c in batch]
            try:
                res = await router.embed_texts(texts)
                embeddings = res.get("embeddings", [])
                if len(embeddings) != len(batch):
                    raise ValueError(f"Provider returned {len(embeddings)} embeddings for {len(batch)} chunks")
                
                for chunk, vector in zip(batch, embeddings):
                    chunk.embedding_json = json.dumps(vector)
                    chunk.embedding_provider = res.get("provider")
                    chunk.embedding_model = res.get("model")
                    chunk.embedding_dimension = res.get("dimension")
                    chunk.embedding_created_at = datetime.datetime.utcnow()
                    chunks_embedded += 1
                
                db.commit()
            except Exception as e:
                db.rollback()
                errors.append(str(e))
                break
                
    return {
        "course_id": course_id,
        "chunks_total": chunks_total,
        "chunks_embedded": chunks_embedded,
        "chunks_skipped": chunks_skipped if not force else 0,
        "errors": errors
    }

async def embed_query(query: str) -> List[float]:
    """
    Generate an embedding vector for a single query string.
    """
    if not query:
        raise ValueError("Query string cannot be empty")
        
    res = await router.embed_texts([query])
    embeddings = res.get("embeddings")
    if not embeddings or not embeddings[0]:
        raise ValueError("No embedding generated for query")
    return embeddings[0]
