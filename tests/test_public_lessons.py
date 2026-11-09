from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.routers.public_lessons import router, STAGES

app = FastAPI()
app.include_router(router, prefix="/api")
client = TestClient(app)

def test_preview_has_five_beginner_steps_without_answer_keys():
    res = client.get("/api/public/lessons/electric-fields")
    assert res.status_code == 200
    payload = res.json()
    assert payload["ai_generated"] is False
    assert payload["persistence"] is False
    assert payload["status"] == "public-preview"
    assert len(payload["steps"]) == 5
    assert payload["steps"][0]["id"] == "charge"
    assert payload["steps"][-1]["scene"] == "dipole"
    assert all("correct" not in str(s["question"].keys()) for s in payload["steps"])
    assert all(len(s["question"]["options"]) == 3 for s in payload["steps"])

def test_each_correct_answer_is_evaluated_by_backend():
    data = client.get("/api/public/lessons/electric-fields").json()
    keys = {"field-direction": 0, "field-versus-force": 0, "double-charge": 0, "double-distance": 1, "dipole": 1}
    for stage in data["steps"]:
        id_ = stage["question"]["id"]
        response = client.post("/api/public/lessons/electric-fields/check",
            json={"question_id": id_, "selected_index": keys[id_]})
        assert response.status_code == 200
        assert response.json()["correct"] is True
        assert response.json()["persistence"] is False
        assert response.json()["assessed_by"] == "deterministic-answer-key"

def test_wrong_answer_returns_explanation_not_mastery_label():
    res = client.post("/api/public/lessons/electric-fields/check", json={"question_id": "double-distance", "selected_index": 0})
    assert res.status_code == 200
    assert res.json()["correct"] is False
    assert "remediation" not in res.json()
    assert "field" in res.json()["feedback"].lower() or "exponent" in res.json()["feedback"].lower()

def test_reject_unknown_and_unexpected_input():
    assert client.post("/api/public/lessons/electric-fields/check", json={"question_id":"unknown", "selected_index":0}).status_code == 404
    assert client.post("/api/public/lessons/electric-fields/check", json={"question_id":"double-charge", "selected_index":-1}).status_code == 422
    assert client.post("/api/public/lessons/electric-fields/check", json={"question_id":"double-charge", "selected_index":0, "learner_id":123}).status_code == 422

def test_content_references_only_known_questions():
    from backend.routers.public_lessons import _CHECKS
    assert len(STAGES) == len(_CHECKS)
    assert {s["question_id"] for s in STAGES} == set(_CHECKS)
