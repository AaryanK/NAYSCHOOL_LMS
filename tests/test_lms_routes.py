from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.config import settings
from backend.database import Base, get_db
from backend.deps import get_current_user
from backend.main import app
from backend.models import LMSConnection, LMSOAuthState, User
from backend.services.token_service import decrypt_token


@pytest.fixture(name="db_session")
def fixture_db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    user = User(id=2, email="lms@nayschool.test", hashed_password="pw")
    db.add(user)
    db.commit()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture(name="client")
def fixture_client(db_session, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "test")
    monkeypatch.setattr(settings, "BLACKBOARD_ENABLED", True)
    monkeypatch.setattr(settings, "BLACKBOARD_CLIENT_ID", "oauth-key")
    monkeypatch.setattr(settings, "BLACKBOARD_CLIENT_SECRET", "oauth-secret")
    monkeypatch.setattr(settings, "BLACKBOARD_SCOPES", "read offline")

    def override_get_db():
        yield db_session

    def override_get_current_user():
        return db_session.query(User).filter(User.id == 2).one()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def start_oauth(client):
    response = client.post("/api/lms/blackboard/connect", json={"school_domain": "learn.example.edu"})
    assert response.status_code == 200
    data = response.json()
    state = parse_qs(urlparse(data["authorization_url"]).query)["state"][0]
    return data, state


def test_connect_stores_unpredictable_hashed_state_and_pkce(client, db_session):
    first, first_state = start_oauth(client)
    second, second_state = start_oauth(client)
    assert first_state != second_state
    assert "2:blackboard_auth" not in first_state
    assert first["connection_id"] == second["connection_id"]
    rows = db_session.query(LMSOAuthState).all()
    assert len(rows) == 2
    assert all(row.state_hash not in {first_state, second_state} for row in rows)
    assert len(decrypt_token(rows[0].code_verifier_encrypted)) >= 43
    query = parse_qs(urlparse(first["authorization_url"]).query)
    assert query["code_challenge_method"] == ["S256"]


def test_connect_rejects_origin_with_path(client):
    response = client.post("/api/lms/blackboard/connect", json={"school_domain": "https://learn.example.edu/evil"})
    assert response.status_code == 422


def test_callback_success_encrypts_token_and_calculates_expiry(client, db_session):
    data, state = start_oauth(client)
    before = datetime.utcnow()
    token_payload = {
        "access_token": "raw-access", "refresh_token": "raw-refresh", "expires_in": 1800,
        "scope": "read offline", "user_id": "bb-user-7",
    }
    with patch(
        "backend.lms.providers.blackboard.BlackboardConnector.exchange_code_for_token",
        new=AsyncMock(return_value=token_payload),
    ):
        response = client.get(
            f"/api/lms/blackboard/oauth/callback?code=abc&state={state}", follow_redirects=False
        )
    assert response.status_code == 303
    assert response.headers["location"] == f"/lms?oauth=success&connection_id={data['connection_id']}"
    connection = db_session.query(LMSConnection).filter(LMSConnection.id == data["connection_id"]).one()
    transaction = db_session.query(LMSOAuthState).one()
    assert connection.status == "connected"
    assert connection.access_token_encrypted != "raw-access"
    assert decrypt_token(connection.access_token_encrypted) == "raw-access"
    assert connection.token_expires_at >= before + timedelta(seconds=1799)
    assert transaction.consumed_at is not None


def test_callback_invalid_state(client):
    response = client.get(
        "/api/lms/blackboard/oauth/callback?code=abc&state=invalid", follow_redirects=False
    )
    assert response.headers["location"].endswith("oauth=error&reason=invalid_state")


def test_callback_expired_state(client, db_session):
    _, state = start_oauth(client)
    row = db_session.query(LMSOAuthState).one()
    row.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    response = client.get(
        f"/api/lms/blackboard/oauth/callback?code=abc&state={state}", follow_redirects=False
    )
    assert response.headers["location"].endswith("oauth=error&reason=state_expired")


def test_callback_provider_mismatch(client, db_session):
    _, state = start_oauth(client)
    row = db_session.query(LMSOAuthState).one()
    row.provider = "canvas"
    db_session.commit()
    response = client.get(
        f"/api/lms/blackboard/oauth/callback?code=abc&state={state}", follow_redirects=False
    )
    assert response.headers["location"].endswith("oauth=error&reason=provider_mismatch")


def test_callback_state_is_one_time_use(client, db_session):
    _, state = start_oauth(client)
    token_payload = {"access_token": "a", "expires_in": 60, "user_id": "u"}
    exchange = AsyncMock(return_value=token_payload)
    with patch("backend.lms.providers.blackboard.BlackboardConnector.exchange_code_for_token", new=exchange):
        first = client.get(f"/api/lms/blackboard/oauth/callback?code=one&state={state}", follow_redirects=False)
        second = client.get(f"/api/lms/blackboard/oauth/callback?code=two&state={state}", follow_redirects=False)
    assert "oauth=success" in first.headers["location"]
    assert second.headers["location"].endswith("oauth=error&reason=state_already_used")
    assert exchange.await_count == 1


def test_callback_handles_blackboard_oauth_error_without_echoing_description(client):
    response = client.get(
        "/api/lms/blackboard/oauth/callback?error=access_denied&error_description=contains-secret",
        follow_redirects=False,
    )
    assert response.headers["location"].endswith("oauth=error&reason=authorization_denied")
    assert "contains-secret" not in response.headers["location"]


def test_authenticated_probe_is_sanitized(client, db_session):
    connection = LMSConnection(
        user_id=2, provider="blackboard", base_url="https://learn.example.edu", status="connected"
    )
    db_session.add(connection)
    db_session.commit()
    result = {
        "provider": "blackboard", "connection_status": "connected",
        "blackboard_site": "https://learn.example.edu", "authenticated_user_id": "bb-user",
        "token_expires_at": None, "api_reachable": True,
    }
    with patch("backend.routers.lms.BlackboardClient.probe", new=AsyncMock(return_value=result)):
        response = client.get(f"/api/lms/{connection.id}/probe")
    assert response.status_code == 200
    assert response.json() == result
    assert "access_token" not in response.text.lower()
    assert "refresh_token" not in response.text.lower()


def test_sync_has_no_fake_success(client, db_session):
    connection = LMSConnection(
        user_id=2, provider="blackboard", base_url="https://learn.example.edu", status="connected"
    )
    db_session.add(connection)
    db_session.commit()
    response = client.post(f"/api/lms/{connection.id}/sync", json={})
    assert response.status_code == 501
    assert "not implemented" in response.json()["detail"]
