import re
import json
import numpy as np
from sqlalchemy.orm import Session
from backend.models import DocumentChunk

def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    """
    Computes the cosine similarity between two numeric vectors.
    """
    if not vector_a or not vector_b:
        return 0.0
    a = np.array(vector_a, dtype=np.float32)
    b = np.array(vector_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

def search_course_chunks(db: Session, course_id: int, query: str, limit: int = 5) -> list[dict]:
    """
    Performs simple keyword and exact phrase matching across course chunks.
    Ranks chunks by term occurrence count using word boundaries and returns the top results.
    """
    query_lower = query.lower().strip()
    if not query_lower:
        return []

    # Extract terms and ignore common stop words to keep search meaningful
    stop_words = {"the", "a", "an", "and", "or", "of", "to", "in", "is", "for", "on", "with", "at", "by", "from", "that", "this", "it", "as", "are"}
    raw_terms = re.split(r'\W+', query_lower)
    terms = [t for t in raw_terms if t and t not in stop_words]
    
    # Fallback if query consists entirely of stop words
    if not terms:
        terms = [t for t in raw_terms if t]
        if not terms:
            return []

    # Query all document chunks belonging to this course
    chunks = db.query(DocumentChunk).filter(DocumentChunk.course_id == course_id).all()
    
    scored_results = []
    for chunk in chunks:
        content_lower = chunk.content.lower()
        score = 0
        
        # 1. Boost score if the exact query phrase appears
        if query_lower in content_lower:
            score += 5
            
        # 2. Add points for individual query term occurrences using word boundaries
        for term in terms:
            # Ignore single-letter terms to prevent false positives on common letters (e.g. O(n) math symbols)
            if len(term) < 2:
                continue
            
            # Find occurrences as whole words
            occurrences = len(re.findall(rf"\b{re.escape(term)}\b", content_lower))
            score += occurrences

        if score > 0:
            scored_results.append({
                "chunk_id": chunk.id,
                "course_file_id": chunk.course_file_id,
                "score": float(score),
                "content": chunk.content
            })

    # Sort descending by score, returning top matching chunks
    scored_results.sort(key=lambda x: x["score"], reverse=True)
    return scored_results[:limit]

async def semantic_search_course_chunks(
    db: Session,
    course_id: int,
    query: str,
    limit: int = 5
) -> list[dict]:
    """
    Generates embedding for a query, loads all chunk embeddings in a course,
    and returns chunks sorted by cosine similarity score.
    """
    from backend.services.embedding_service import embed_query
    
    # 1. Generate embedding for query
    query_vector = await embed_query(query)
    
    # 2. Load chunks with non-null embedding_json
    chunks = db.query(DocumentChunk).filter(
        DocumentChunk.course_id == course_id,
        DocumentChunk.embedding_json != None
    ).all()
    
    if not chunks:
        return []
        
    scored_results = []
    for chunk in chunks:
        try:
            vector = json.loads(chunk.embedding_json)
            sim = cosine_similarity(query_vector, vector)
            scored_results.append({
                "chunk_id": chunk.id,
                "course_file_id": chunk.course_file_id,
                "score": sim,
                "score_type": "semantic",
                "content": chunk.content
            })
        except Exception:
            continue
            
    # 3. Sort descending by similarity score
    scored_results.sort(key=lambda x: x["score"], reverse=True)
    return scored_results[:limit]

async def hybrid_search_course_chunks(
    db: Session,
    course_id: int,
    query: str,
    semantic_limit: int = 5,
    keyword_limit: int = 5,
    final_limit: int = 5
) -> list[dict]:
    """
    Combines semantic and keyword search. Normalizes scores and combines them
    using: final_score = 0.70 * semantic_score + 0.30 * keyword_score
    """
    semantic_results = []
    semantic_failed = False
    
    try:
        semantic_results = await semantic_search_course_chunks(db, course_id, query, limit=semantic_limit)
    except Exception:
        semantic_failed = True
        
    keyword_results = search_course_chunks(db, course_id, query, limit=keyword_limit)
    
    if semantic_failed or not semantic_results:
        # Fallback mode
        max_kw = max([r["score"] for r in keyword_results]) if keyword_results else 0.0
        results = []
        for r in keyword_results:
            kw_norm = r["score"] / max_kw if max_kw > 0 else 0.0
            results.append({
                "chunk_id": r["chunk_id"],
                "course_file_id": r["course_file_id"],
                "semantic_score": 0.0,
                "keyword_score": kw_norm,
                "final_score": kw_norm,
                "content": r["content"]
            })
        return results

    # Merge semantic and keyword search
    semantic_map = {r["chunk_id"]: r for r in semantic_results}
    keyword_map = {r["chunk_id"]: r for r in keyword_results}
    
    all_chunk_ids = set(semantic_map.keys()) | set(keyword_map.keys())
    max_keyword_score = max([r["score"] for r in keyword_results]) if keyword_results else 0.0
    
    merged_results = []
    for cid in all_chunk_ids:
        sem_r = semantic_map.get(cid)
        sem_score = sem_r["score"] if sem_r else 0.0
        
        kw_r = keyword_map.get(cid)
        kw_score_raw = kw_r["score"] if kw_r else 0.0
        kw_score = kw_score_raw / max_keyword_score if max_keyword_score > 0 else 0.0
        
        final_score = 0.70 * sem_score + 0.30 * kw_score
        
        content = sem_r["content"] if sem_r else kw_r["content"]
        course_file_id = sem_r["course_file_id"] if sem_r else kw_r["course_file_id"]
        
        merged_results.append({
            "chunk_id": cid,
            "course_file_id": course_file_id,
            "semantic_score": sem_score,
            "keyword_score": kw_score,
            "final_score": final_score,
            "content": content
        })
        
    merged_results.sort(key=lambda x: x["final_score"], reverse=True)
    return merged_results[:final_limit]
