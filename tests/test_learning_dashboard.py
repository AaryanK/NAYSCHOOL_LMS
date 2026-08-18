import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db
from backend.models import Course, User, CourseTopic, DocumentChunk, PracticeQuestion, StudyPlanTask
from backend.deps import get_current_user
from unittest.mock import patch

@pytest.fixture(name="db_session")
def fixture_db_session():
    db_file = "./test_temp_learning.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass
            
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    original_close = db.close
    db.close = lambda: None
    
    try:
        yield db
    finally:
        original_close()
        engine.dispose()
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except Exception:
                pass

@pytest.fixture(name="client")
def fixture_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    # Create dummy user and course
    user = User(id=1, email="student@test.com", hashed_password="hashed_password_mock")
    course = Course(id=1, user_id=1, name="Data Science", code="DS101")
    db_session.add(user)
    db_session.add(course)
    db_session.commit()

    def override_get_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()

def test_get_learning_dashboard(client, db_session):
    # Add a topic to make it return values
    topic = CourseTopic(id=1, course_id=1, name="Machine Learning", source="manual")
    chunk = DocumentChunk(id=1, course_id=1, course_file_id=1, chunk_index=0, content="ML intro")
    db_session.add(topic)
    db_session.add(chunk)
    db_session.commit()

    response = client.get("/api/courses/1/learning-dashboard")
    assert response.status_code == 200
    data = response.json()
    
    # Assert all expected fields are present
    assert "course" in data
    assert data["course"]["name"] == "Data Science"
    assert data["topics_count"] == 1
    assert data["chunks_count"] == 1
    assert "average_mastery" in data
    assert "weak_topics" in data
    assert "strong_topics" in data
    assert "upcoming_study_tasks" in data
    assert "recent_attempts" in data

def test_topics_endpoints(client, db_session):
    # Create topic
    response = client.post("/api/courses/1/topics", json={
        "name": "Deep Learning",
        "description": "Neural Networks",
        "source": "manual"
    })
    assert response.status_code == 200
    assert response.json()["name"] == "Deep Learning"

    # Get topics
    response = client.get("/api/courses/1/topics")
    assert response.status_code == 200
    assert len(response.json()) == 1
    
    # Get topic by id
    response = client.get("/api/courses/1/topics/1")
    assert response.status_code == 200

@pytest.mark.anyio
@patch("backend.services.practice_service.PracticeQuestionAgent.run")
async def test_practice_endpoints(mock_practice_agent, client, db_session):
    # Mock LLM generation
    mock_practice_agent.return_value = {
        "questions": [
            {
                "question_text": "Describe overfitting?",
                "answer_text": "Model fits training data too well.",
                "explanation": "High variance.",
                "difficulty": "medium"
            }
        ]
    }

    # Add topic first
    topic = CourseTopic(id=1, course_id=1, name="Supervised Learning", source="manual")
    db_session.add(topic)
    db_session.commit()

    response = client.post("/api/courses/1/practice/generate", json={
        "topic_id": 1,
        "count": 1,
        "difficulty": "medium",
        "provider": "auto",
        "model": None
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["question_text"] == "Describe overfitting?"

    # Verify retrieval
    response = client.get("/api/courses/1/practice")
    assert response.status_code == 200
    assert len(response.json()) == 1

@pytest.mark.anyio
@patch("backend.ai.llm_router.LLMRouter.chat")
async def test_study_plan_tasks_endpoints(mock_chat, client, db_session):
    # Mock AI Grading response
    mock_chat.return_value = {
        "content": '{"score": 0.5, "feedback": "Needs work", "is_correct": false}'
    }

    # Setup topic
    topic = CourseTopic(id=1, course_id=1, name="Unsupervised Learning", source="manual")
    db_session.add(topic)
    db_session.commit()

    # Generate study plan tasks
    response = client.post("/api/courses/1/study-tasks/generate", json={"days": 7})
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0 # Generates 4 tasks per topic
    
    task_id = data[0]["id"]

    # Retrieve study tasks
    response = client.get("/api/courses/1/study-tasks")
    assert response.status_code == 200
    assert len(response.json()) > 0

    # Update study task status
    response = client.patch(f"/api/study-tasks/{task_id}", json={"status": "completed"})
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
