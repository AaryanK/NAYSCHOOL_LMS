import os
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db
from backend.models import Course, User, LMSConnection, LMSSyncLog, ExternalCourseMap, Assignment
from backend.deps import get_current_user
from backend.config import settings

@pytest.fixture(name="db_session")
def fixture_db_session():
    db_file = "./test_temp_lms.db"
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

    mock_user = User(id=2, email="lms@nayschool.com", hashed_password="pw")
    db_session.add(mock_user)
    db_session.commit()

    def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    with TestClient(app) as c:
        yield c
        
    app.dependency_overrides.clear()

def test_get_lms_providers_endpoint(client):
    resp = client.get("/api/lms/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data
    # Standard providers: blackboard, canvas
    providers = {p["name"]: p for p in data["providers"]}
    assert "blackboard" in providers
    assert "canvas" in providers

def test_get_lms_connections_empty(client):
    resp = client.get("/api/lms/connections")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_connect_provider_not_configured(client):
    # If BLACKBOARD_ENABLED is False or URL is missing
    settings.BLACKBOARD_ENABLED = False
    resp = client.post("/api/lms/blackboard/connect", json={"school_domain": "blackboard.school.edu"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "not_configured"
    assert "not fully configured" in data["message"]

def test_connect_provider_success(client):
    # Set config values temporarily
    settings.BLACKBOARD_ENABLED = True
    settings.BLACKBOARD_BASE_URL = "https://blackboard.school.edu"
    settings.BLACKBOARD_CLIENT_ID = "my-client-id"
    settings.BLACKBOARD_CLIENT_SECRET = "my-client-secret"
    
    resp = client.post("/api/lms/blackboard/connect", json={"school_domain": "blackboard.school.edu"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "configured"
    assert "authorization_url" in data
    assert "state=2:blackboard_auth" in data["authorization_url"]

def test_sync_lms_not_configured(client, db_session):
    # Pre-create connection record
    conn = LMSConnection(
        id=5,
        user_id=2,
        provider="blackboard",
        school_domain="blackboard.school.edu",
        status="disconnected"
    )
    db_session.add(conn)
    db_session.commit()

    settings.BLACKBOARD_ENABLED = False
    resp = client.post("/api/lms/5/sync", json={"sync_courses": True, "sync_assignments": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "not_configured"
    
    # Verify sync log was created
    log = db_session.query(LMSSyncLog).filter(LMSSyncLog.connection_id == 5).first()
    assert log is not None
    assert log.status == "not_configured"

def test_sync_lms_success_mock(client, db_session):
    # Pre-create connection record
    conn = LMSConnection(
        id=6,
        user_id=2,
        provider="blackboard",
        school_domain="blackboard.school.edu",
        status="disconnected"
    )
    db_session.add(conn)
    db_session.commit()

    # Enabled but without actual API endpoint calls, Blackboard Connector will fall back to mock data!
    settings.BLACKBOARD_ENABLED = True
    settings.BLACKBOARD_BASE_URL = "https://blackboard.school.edu"
    
    resp = client.post("/api/lms/6/sync", json={"sync_courses": True, "sync_assignments": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["synced_courses_count"] == 1
    assert data["synced_assignments_count"] == 1

    # Check course was created
    c = db_session.query(Course).filter(Course.user_id == 2).first()
    assert c is not None
    assert "Introduction to Computer Science" in c.name
    
    # Check ExternalCourseMap
    mapping = db_session.query(ExternalCourseMap).filter(ExternalCourseMap.lms_connection_id == 6).first()
    assert mapping is not None
    assert mapping.external_course_id == "bb-course-101"
    
    # Check Assignment
    assign = db_session.query(Assignment).filter(Assignment.course_id == c.id).first()
    assert assign is not None
    assert assign.external_provider == "blackboard"
    assert assign.external_id == "bb-assign-1"
    assert "Big O notation" in assign.title

    # Check logs
    logs_resp = client.get("/api/lms/6/sync-logs")
    assert logs_resp.status_code == 200
    logs_data = logs_resp.json()
    assert len(logs_data) == 1
    assert logs_data[0]["status"] == "success"
