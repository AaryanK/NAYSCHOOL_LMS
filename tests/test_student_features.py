import os
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db
from backend.models import User, UserProfile, Course, ChatSession, ChatMessage, Notification, StudyActivity, UsageCounter, Assignment, StudyPlanTask
from backend.deps import get_current_user
from backend.services.activity_service import log_study_activity, get_study_streak
from backend.services.usage_service import get_or_create_current_usage, increment_usage, check_usage_limit

@pytest.fixture(name="db_session")
def fixture_db_session():
    db_file = "./test_temp_student.db"
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

    mock_user = User(id=3, email="student@nayschool.com", hashed_password="pw", plan="free")
    db_session.add(mock_user)
    db_session.commit()

    def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    with TestClient(app) as c:
        yield c
        
    app.dependency_overrides.clear()

def test_profile_and_onboarding(client, db_session):
    # 1. Profile auto-created on GET
    resp = client.get("/api/me/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 3
    assert data["onboarding_completed"] is False
    
    # 2. PATCH profile
    patch_resp = client.patch("/api/me/profile", json={
        "education_level": "college",
        "major": "Computer Science"
    })
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    assert patch_data["education_level"] == "college"
    assert patch_data["major"] == "Computer Science"
    
    # 3. Complete onboarding
    complete_resp = client.post("/api/me/onboarding/complete", json={
        "education_level": "college",
        "major": "Computer Science",
        "school_name": "Stanford",
        "study_goal": "prepare for exams",
        "preferred_study_style": "step_by_step",
        "daily_study_minutes": 45
    })
    assert complete_resp.status_code == 200
    complete_data = complete_resp.json()
    assert complete_data["onboarding_completed"] is True
    assert complete_data["school_name"] == "Stanford"
    assert complete_data["daily_study_minutes"] == 45

def test_student_home(client, db_session):
    # Setup some test data: course, assignment, study task
    course = Course(id=1, user_id=3, name="Calculus")
    db_session.add(course)
    db_session.commit()
    
    assignment = Assignment(
        course_id=1,
        title="Homework 1",
        due_date=(datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d"),
        status="todo"
    )
    db_session.add(assignment)
    
    study_task = StudyPlanTask(
        user_id=3,
        course_id=1,
        title="Study limits",
        due_at=datetime.utcnow() + timedelta(hours=2),
        status="pending"
    )
    db_session.add(study_task)
    db_session.commit()

    resp = client.get("/api/student/home")
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["courses_count"] == 1
    assert len(data["assignments_due_soon"]) == 1
    assert len(data["study_tasks_today"]) == 1
    assert "streak" in data
    assert "recommended_actions" in data
    assert len(data["recommended_actions"]) > 0

def test_chat_sessions(client, db_session):
    course = Course(id=2, user_id=3, name="Physics")
    db_session.add(course)
    db_session.commit()
    
    # Create chat session via POST
    resp = client.post("/api/courses/2/chat-sessions", json={"title": "Mechanics Q&A"})
    assert resp.status_code == 200
    session_data = resp.json()
    assert session_data["title"] == "Mechanics Q&A"
    session_id = session_data["id"]
    
    # Get chat sessions list
    list_resp = client.get("/api/courses/2/chat-sessions")
    assert list_resp.status_code == 200
    sessions_list = list_resp.json()
    assert len(sessions_list) == 1
    assert sessions_list[0]["id"] == session_id
    
    # Get session details
    detail_resp = client.get(f"/api/courses/2/chat-sessions/{session_id}")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["id"] == session_id
    assert len(detail_data["messages"]) == 0
    
    # Delete session
    del_resp = client.delete(f"/api/courses/2/chat-sessions/{session_id}")
    assert del_resp.status_code == 200
    assert del_resp.json() == {"message": "Chat session deleted successfully."}

def test_notifications(client, db_session):
    course = Course(id=3, user_id=3, name="Chemistry")
    db_session.add(course)
    db_session.commit()
    
    assign = Assignment(
        course_id=3,
        title="Lab Report",
        due_date=(datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d"),
        status="todo"
    )
    db_session.add(assign)
    
    task = StudyPlanTask(
        user_id=3,
        course_id=3,
        title="Study Periodic Table",
        due_at=datetime.utcnow() + timedelta(days=1),
        status="pending"
    )
    db_session.add(task)
    db_session.commit()
    
    # Generate study reminders
    gen_resp = client.post("/api/courses/3/notifications/generate-study-reminders")
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()
    assert len(gen_data) == 2  # one for assignment, one for study task
    
    # Check notifications list
    list_resp = client.get("/api/notifications")
    assert list_resp.status_code == 200
    notifs = list_resp.json()
    assert len(notifs) == 2
    
    notif_id = notifs[0]["id"]
    
    # Mark as read
    read_resp = client.patch(f"/api/notifications/{notif_id}/read")
    assert read_resp.status_code == 200
    read_data = read_resp.json()
    assert read_data["read_at"] is not None

def test_activity_and_streaks(client, db_session):
    # Log some activities
    log_study_activity(db_session, user_id=3, activity_type="tutor_question", course_id=1)
    
    # Verify activity list endpoint
    resp = client.get("/api/me/activity")
    assert resp.status_code == 200
    activities = resp.json()
    assert len(activities) >= 1
    assert activities[0]["activity_type"] == "tutor_question"
    
    # Verify streak endpoint
    streak_resp = client.get("/api/me/streak")
    assert streak_resp.status_code == 200
    streak_data = streak_resp.json()
    assert streak_data["current_streak_days"] == 1
    assert streak_data["active_today"] is True

def test_plan_limits_and_overrides(client, db_session):
    # Setup test course with id=1
    course = Course(id=1, user_id=3, name="Calculus")
    db_session.add(course)
    db_session.commit()

    # Verify plan and usage endpoints
    p_resp = client.get("/api/me/plan")
    assert p_resp.status_code == 200
    assert p_resp.json() == {"plan": "free"}
    
    u_resp = client.get("/api/me/usage")
    assert u_resp.status_code == 200
    usage_data = u_resp.json()
    assert usage_data["tutor_questions_count"] == 0
    
    # Set dev plan override
    override_resp = client.patch("/api/me/plan-dev", json={"plan": "plus"})
    assert override_resp.status_code == 200
    assert override_resp.json()["plan"] == "plus"
    
    p_resp = client.get("/api/me/plan")
    assert p_resp.json() == {"plan": "plus"}
    
    # Reset back to free for limit testing
    client.patch("/api/me/plan-dev", json={"plan": "free"})
    
    # Mock usage count to exceeded (free limit is 50 tutor asks)
    usage = get_or_create_current_usage(db_session, user_id=3)
    usage.tutor_questions_count = 50
    db_session.commit()
    
    # Try tutor ask
    tutor_ask_resp = client.post("/api/courses/1/tutor/ask", json={
        "question": "What is 2+2?",
        "provider": "auto"
    })
    
    # Free plan limit exceeded should block with 403
    assert tutor_ask_resp.status_code == 403
    tutor_data = tutor_ask_resp.json()
    assert tutor_data["error"] == "usage_limit_exceeded"
    assert "upgrade_options" in tutor_data
