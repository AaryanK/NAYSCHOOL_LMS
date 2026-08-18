import re
from sqlalchemy.orm import Session
from backend.models import Course, DocumentChunk, Assignment, CourseTopic, TopicChunkMap, CourseFile
from backend.ai.llm_router import LLMRouter
from backend.agy.topic_extraction_agent import TopicExtractionAgent

async def extract_topics_for_course(db: Session, course_id: int, provider: str = "auto", model: str = None) -> dict:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError("Course not found.")

    # Fetch assignment titles
    assignments = db.query(Assignment).filter(Assignment.course_id == course_id).all()
    assignment_titles = [a.title for a in assignments if a.title]

    # Fetch document chunks
    chunks = db.query(DocumentChunk).filter(DocumentChunk.course_id == course_id).limit(30).all()
    chunk_texts = [c.content for c in chunks]

    # Try to find a syllabus file specifically to feed syllabus text
    syllabus_chunks = db.query(DocumentChunk).join(CourseFile).filter(
        DocumentChunk.course_id == course_id,
        CourseFile.original_filename.ilike("%syllabus%")
    ).order_by(DocumentChunk.chunk_index).all()
    
    syllabus_text = "\n".join([c.content for c in syllabus_chunks]) if syllabus_chunks else ""

    # Call TopicExtractionAgent
    llm_router = LLMRouter()
    agent = TopicExtractionAgent(llm_router)
    res = await agent.run({
        "chunks": chunk_texts,
        "syllabus_text": syllabus_text,
        "assignment_titles": assignment_titles,
        "course_name": course.name,
        "course_description": course.description or "",
        "provider": provider,
        "model": model
    })

    extracted_topics = res.get("topics", [])

    # Fetch existing topics
    existing_topics = db.query(CourseTopic).filter(CourseTopic.course_id == course_id).all()
    existing_names = {t.name.strip().lower() for t in existing_topics}

    topics_created = 0
    topics_existing = len(existing_topics)

    for topic_data in extracted_topics:
        name = topic_data.get("name", "").strip()
        if not name:
            continue
        if name.lower() not in existing_names:
            db_topic = CourseTopic(
                course_id=course_id,
                name=name,
                description=topic_data.get("description"),
                source="extracted",
                confidence=topic_data.get("confidence", 1.0)
            )
            db.add(db_topic)
            existing_names.add(name.lower())
            topics_created += 1

    db.commit()

    # Automatically map chunks to topics
    map_res = map_chunks_to_topics(db, course_id)

    return {
        "topics_created": topics_created,
        "topics_existing": topics_existing,
        "chunk_maps_created": map_res.get("chunk_maps_created", 0)
    }

def get_course_topics(db: Session, course_id: int) -> list:
    return db.query(CourseTopic).filter(CourseTopic.course_id == course_id).all()

def create_topic(db: Session, course_id: int, name: str, description: str = None, source: str = "manual") -> CourseTopic:
    # Normalized duplicate prevention
    name_clean = name.strip()
    existing = db.query(CourseTopic).filter(
        CourseTopic.course_id == course_id,
        CourseTopic.name == name_clean
    ).first()
    
    if existing:
        return existing
        
    db_topic = CourseTopic(
        course_id=course_id,
        name=name_clean,
        description=description,
        source=source,
        confidence=1.0
    )
    db.add(db_topic)
    db.commit()
    db.refresh(db_topic)
    
    # Run maps updates
    map_chunks_to_topics(db, course_id)
    
    return db_topic

def map_chunks_to_topics(db: Session, course_id: int) -> dict:
    # Fetch all chunks and topics for this course
    chunks = db.query(DocumentChunk).filter(DocumentChunk.course_id == course_id).all()
    topics = db.query(CourseTopic).filter(CourseTopic.course_id == course_id).all()

    # Clear existing maps to refresh cleanly
    db.query(TopicChunkMap).filter(TopicChunkMap.course_id == course_id).delete()

    maps_created = 0
    for topic in topics:
        topic_name_lower = topic.name.lower().strip()
        # Find word boundaries if possible
        pattern = re.compile(rf'\b{re.escape(topic_name_lower)}\b', re.IGNORECASE)

        for chunk in chunks:
            content_lower = chunk.content.lower()
            match = False
            occurrences = 0

            if topic_name_lower in content_lower:
                match = True
                occurrences = content_lower.count(topic_name_lower)
            elif pattern.search(chunk.content):
                match = True
                occurrences = len(pattern.findall(chunk.content))

            if match:
                relevance = min(1.0, 0.5 + 0.1 * occurrences)
                db_map = TopicChunkMap(
                    topic_id=topic.id,
                    document_chunk_id=chunk.id,
                    course_id=course_id,
                    relevance_score=relevance
                )
                db.add(db_map)
                maps_created += 1

    db.commit()
    return {"chunk_maps_created": maps_created}
