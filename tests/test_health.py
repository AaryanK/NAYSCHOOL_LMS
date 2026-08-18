from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_read_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "app": "NaySchool 3.0"}

def test_read_ai_health():
    response = client.get("/api/ai/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert "providers" in response.json()
