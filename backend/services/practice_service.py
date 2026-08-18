import json
import re
import datetime
from sqlalchemy.orm import Session
from backend.models import PracticeQuestion, PracticeAttempt, CourseTopic, DocumentChunk, TopicChunkMap
from backend.ai.llm_router import LLMRouter
from backend.agy.practice_question_agent import PracticeQuestionAgent
from backend.services.mastery_service import update_mastery_from_attempt

async def generate_practice_questions(
    db: Session,
    course_id: int,
    topic_id: int = None,
    count: int = 5,
    difficulty: str = "medium",
    provider: str = "auto",
    model: str = None
) -> list:
    if topic_id:
        topic_obj = db.query(CourseTopic).filter(
            CourseTopic.id == topic_id,
            CourseTopic.course_id == course_id
        ).first()
        if not topic_obj:
            raise ValueError("Topic not found.")
        topic_name = topic_obj.name
    else:
        topic_obj = db.query(CourseTopic).filter(CourseTopic.course_id == course_id).first()
        if not topic_obj:
            raise ValueError("No topics exist for this course. Please extract topics first.")
        topic_id = topic_obj.id
        topic_name = topic_obj.name

    # Retrieve relevant chunks for this topic from mapping
    chunks = db.query(DocumentChunk).join(
        TopicChunkMap, TopicChunkMap.document_chunk_id == DocumentChunk.id
    ).filter(
        TopicChunkMap.topic_id == topic_id
    ).order_by(TopicChunkMap.relevance_score.desc()).limit(5).all()
    chunk_texts = [c.content for c in chunks]

    # Fallback to search query matches if no map exists
    if not chunk_texts:
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.course_id == course_id,
            DocumentChunk.content.ilike(f"%{topic_name}%")
        ).limit(5).all()
        chunk_texts = [c.content for c in chunks]

    # Overall fallback
    if not chunk_texts:
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.course_id == course_id
        ).limit(5).all()
        chunk_texts = [c.content for c in chunks]

    llm_router = LLMRouter()
    agent = PracticeQuestionAgent(llm_router)
    res = await agent.run({
        "topic": topic_name,
        "chunks": chunk_texts,
        "difficulty": difficulty,
        "count": count,
        "provider": provider,
        "model": model
    })

    questions = res.get("questions", [])
    db_questions = []
    
    for q in questions:
        db_q = PracticeQuestion(
            course_id=course_id,
            topic_id=topic_id,
            question_text=q["question_text"],
            answer_text=q["answer_text"],
            explanation=q.get("explanation"),
            difficulty=q.get("difficulty", difficulty),
            source="generated",
            created_at=datetime.datetime.utcnow()
        )
        db.add(db_q)
        db_questions.append(db_q)

    db.commit()
    for db_q in db_questions:
        db.refresh(db_q)
        
    return db_questions

async def grade_practice_attempt(
    db: Session,
    user_id: int,
    course_id: int,
    practice_question_id: int,
    student_answer: str,
    provider: str = "auto",
    model: str = None
) -> PracticeAttempt:
    question = db.query(PracticeQuestion).filter(
        PracticeQuestion.id == practice_question_id,
        PracticeQuestion.course_id == course_id
    ).first()
    if not question:
        raise ValueError("Practice question not found.")

    score = 0.0
    is_correct = False
    feedback = ""

    # Call AI router for grading
    system_prompt = (
        "You are the GradingAgent of NaySchool.\n"
        "Compare the student's answer with the correct reference answer and explanation.\n"
        "Assign a correctness score between 0.0 and 1.0 (where 1.0 is completely correct, 0.0 is completely incorrect).\n"
        "Provide constructive feedback to the student.\n\n"
        "You MUST respond ONLY with a valid JSON object matching this structure:\n"
        "{\n"
        '  "score": 0.85,\n'
        '  "feedback": "Your explanation of concept X is correct, but you missed detail Y.",\n'
        '  "is_correct": true\n'
        "}"
        "\nConsider the response correct (is_correct = true) if the score is 0.8 or higher."
    )
    user_content = (
        f"Question: {question.question_text}\n"
        f"Reference Answer: {question.answer_text}\n"
        f"Explanation: {question.explanation or 'None'}\n"
        f"Student's Answer: {student_answer}\n"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]

    try:
        llm_router = LLMRouter()
        res = await llm_router.chat(messages=messages, provider=provider, model=model, temperature=0.2)
        content = res.get("content", "").strip()
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        parsed = json.loads(content)
        score = float(parsed.get("score", 0.0))
        feedback = str(parsed.get("feedback", ""))
        is_correct = bool(parsed.get("is_correct", score >= 0.8))
    except Exception as e:
        # Fallback keyword scorer
        words_ref = set(re.findall(r'\b\w+\b', question.answer_text.lower()))
        words_stud = set(re.findall(r'\b\w+\b', student_answer.lower()))
        
        stopwords = {"the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "to", "of", "in", "on", "at", "for", "with", "that"}
        ref_keywords = words_ref - stopwords
        if not ref_keywords:
            ref_keywords = words_ref
            
        matches = ref_keywords.intersection(words_stud)
        if ref_keywords:
            score = len(matches) / len(ref_keywords)
        else:
            score = 0.5 if student_answer.strip() else 0.0

        if score > 0.0 and len(student_answer) > 20:
            score = min(1.0, score + 0.1)

        is_correct = score >= 0.75
        feedback = f"Graded via keyword fallback. Match score: {score:.2f}. We identified overlap in key concepts. Check the reference answer!"

    attempt = PracticeAttempt(
        user_id=user_id,
        course_id=course_id,
        topic_id=question.topic_id,
        practice_question_id=practice_question_id,
        student_answer=student_answer,
        is_correct=is_correct,
        score=score,
        feedback=feedback,
        created_at=datetime.datetime.utcnow()
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    # Update Mastery
    if question.topic_id:
        update_mastery_from_attempt(db, user_id, course_id, question.topic_id, score)

    return attempt
