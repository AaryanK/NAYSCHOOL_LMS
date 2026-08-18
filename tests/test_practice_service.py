import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import Course, CourseTopic, PracticeQuestion, PracticeAttempt
from backend.services.practice_service import (
    generate_practice_questions,
    grade_practice_attempt
)
from unittest.mock import patch

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    
    # Setup Course and Topic
    course = Course(id=1, user_id=1, name="Database Systems")
    session.add(course)
    
    topic = CourseTopic(id=1, course_id=1, name="Normalization", source="manual")
    session.add(topic)
    session.commit()
    
    try:
        yield session
    finally:
        session.close()

@pytest.mark.anyio
@patch("backend.services.practice_service.PracticeQuestionAgent.run")
async def test_generate_practice_questions(mock_run, db):
    mock_run.return_value = {
        "questions": [
            {
                "question_text": "What is 3NF?",
                "answer_text": "A table is in 3NF if it is in 2NF and has no transitive dependencies.",
                "explanation": "Eliminates transitive dependencies.",
                "difficulty": "medium"
            }
        ]
    }
    
    questions = await generate_practice_questions(db, course_id=1, topic_id=1, count=1)
    assert len(questions) == 1
    assert questions[0].question_text == "What is 3NF?"
    assert questions[0].topic_id == 1
    
    db_questions = db.query(PracticeQuestion).filter(PracticeQuestion.course_id == 1).all()
    assert len(db_questions) == 1

@pytest.mark.anyio
@patch("backend.ai.llm_router.LLMRouter.chat")
async def test_grade_practice_attempt_ai(mock_chat, db):
    # Mock AI Grading returns success JSON
    mock_chat.return_value = {
        "content": '{"score": 0.9, "feedback": "Excellent answer", "is_correct": true}'
    }
    
    question = PracticeQuestion(
        id=1, course_id=1, topic_id=1,
        question_text="What is 3NF?",
        answer_text="A relation in 2NF with no transitive dependencies.",
        explanation="Explain relations",
        difficulty="medium",
        source="generated"
    )
    db.add(question)
    db.commit()
    
    attempt = await grade_practice_attempt(
        db, user_id=1, course_id=1,
        practice_question_id=1,
        student_answer="It is in 2nd normal form and doesn't have transitive dependencies."
    )
    
    assert attempt.id is not None
    assert attempt.score == 0.9
    assert attempt.is_correct is True
    assert attempt.feedback == "Excellent answer"
    
    attempts = db.query(PracticeAttempt).all()
    assert len(attempts) == 1

@pytest.mark.anyio
@patch("backend.ai.llm_router.LLMRouter.chat")
async def test_grade_practice_attempt_fallback(mock_chat, db):
    # Mock AI Grading fails to trigger fallback
    mock_chat.side_effect = Exception("LLM router offline")
    
    question = PracticeQuestion(
        id=1, course_id=1, topic_id=1,
        question_text="What is 3NF?",
        answer_text="A relation in 2NF with no transitive dependencies.",
        explanation="Explain relations",
        difficulty="medium",
        source="generated"
    )
    db.add(question)
    db.commit()
    
    attempt = await grade_practice_attempt(
        db, user_id=1, course_id=1,
        practice_question_id=1,
        # student answer shares many keywords: relation, transitive, dependencies
        student_answer="A relation with no transitive dependencies."
    )
    
    assert attempt.id is not None
    assert attempt.score > 0.4
    assert "fallback" in attempt.feedback.lower()
