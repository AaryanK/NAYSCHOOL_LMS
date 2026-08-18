import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import Course, CourseTopic, StudentMastery
from backend.services.mastery_service import (
    get_or_create_mastery,
    update_mastery_from_attempt,
    get_course_mastery_dashboard
)

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    
    # Setup Course and User and Topics
    course = Course(id=1, user_id=1, name="Calculus")
    session.add(course)
    
    topic1 = CourseTopic(id=1, course_id=1, name="Derivatives", source="manual")
    topic2 = CourseTopic(id=2, course_id=1, name="Integrals", source="manual")
    session.add(topic1)
    session.add(topic2)
    session.commit()
    
    try:
        yield session
    finally:
        session.close()

def test_get_or_create_mastery(db):
    m = get_or_create_mastery(db, user_id=1, course_id=1, topic_id=1)
    assert m.id is not None
    assert m.mastery_score == 0.0
    assert m.confidence == 0.0
    
    # Fetch same should not create duplicates
    m2 = get_or_create_mastery(db, user_id=1, course_id=1, topic_id=1)
    assert m2.id == m.id

def test_update_mastery_from_attempt(db):
    # Initial state
    m = get_or_create_mastery(db, user_id=1, course_id=1, topic_id=1)
    assert m.attempts_count == 0
    assert m.correct_count == 0
    
    # 1. Update with a correct score (e.g. 1.0)
    # formula: new_mastery = 0.0 * 0.75 + 1.0 * 0.25 = 0.25
    m = update_mastery_from_attempt(db, user_id=1, course_id=1, topic_id=1, score=1.0)
    assert m.attempts_count == 1
    assert m.correct_count == 1
    assert m.mastery_score == 0.25
    assert m.confidence == 0.1
    
    # 2. Update with incorrect score (e.g. 0.0)
    # formula: new_mastery = 0.25 * 0.75 + 0.0 * 0.25 = 0.1875
    m = update_mastery_from_attempt(db, user_id=1, course_id=1, topic_id=1, score=0.0)
    assert m.attempts_count == 2
    assert m.correct_count == 1
    assert m.mastery_score == 0.1875
    assert m.confidence == 0.2

def test_get_course_mastery_dashboard(db):
    # Give Derivatives some practices to make mastery high
    update_mastery_from_attempt(db, user_id=1, course_id=1, topic_id=1, score=1.0) # score high -> mastery high
    
    # Give Integrals some poor practices to keep mastery low
    update_mastery_from_attempt(db, user_id=1, course_id=1, topic_id=2, score=0.1) # score low -> mastery low
    
    dashboard = get_course_mastery_dashboard(db, user_id=1, course_id=1)
    assert len(dashboard) == 2
    
    # Derivatives should be stronger than Integrals, so sorted ascending brings Integrals first (weakest)
    assert dashboard[0]["topic_id"] == 2  # Integrals
    assert dashboard[1]["topic_id"] == 1  # Derivatives
    assert dashboard[0]["mastery_score"] < dashboard[1]["mastery_score"]
