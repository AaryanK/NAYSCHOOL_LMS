import pytest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import Course, CourseTopic, StudentMastery, StudyPlanTask
from backend.services.study_plan_service import (
    create_study_task,
    update_study_task,
    get_study_tasks,
    generate_study_tasks_from_weaknesses
)
from backend.services.mastery_service import update_mastery_from_attempt

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    
    # Setup Course and User
    course = Course(id=1, user_id=1, name="Algorithms")
    session.add(course)
    
    topic = CourseTopic(id=1, course_id=1, name="Dynamic Programming", source="manual")
    session.add(topic)
    session.commit()
    
    try:
        yield session
    finally:
        session.close()

def test_create_and_update_study_task(db):
    task = create_study_task(
        db, user_id=1, course_id=1, title="Review DP Chunks",
        topic_id=1, description="Read notes", due_at=None, priority="high"
    )
    assert task.id is not None
    assert task.status == "pending"
    assert task.priority == "high"
    
    # Test update to completed
    updated = update_study_task(db, user_id=1, task_id=task.id, updates={"status": "completed"})
    assert updated.status == "completed"
    assert updated.completed_at is not None
    
    # Test update back to pending clears completed_at
    updated = update_study_task(db, user_id=1, task_id=task.id, updates={"status": "pending"})
    assert updated.status == "pending"
    assert updated.completed_at is None

def test_generate_study_tasks_from_weaknesses(db):
    # Give DP a very low mastery (0.1)
    update_mastery_from_attempt(db, user_id=1, course_id=1, topic_id=1, score=0.1)
    
    tasks = generate_study_tasks_from_weaknesses(db, user_id=1, course_id=1, days=7)
    # The template generates 4 tasks per weak topic
    assert len(tasks) == 4
    assert any("Dynamic Programming" in t.title for t in tasks)
    
    # Verify priority is high or urgent for low mastery (0.1 < 0.25 -> urgent)
    assert tasks[0].priority == "urgent"
    
    db_tasks = get_study_tasks(db, user_id=1, course_id=1)
    assert len(db_tasks) == 4
