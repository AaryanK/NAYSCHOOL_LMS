from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse
from unittest.mock import Mock, patch

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.config import settings
from backend.database import Base
from backend.lms.blackboard_client import BlackboardAPIError, BlackboardClient, normalize_blackboard_origin
from backend.lms.providers.blackboard import BlackboardConnector
from backend.models import LMSConnection, User
from backend.services.token_service import decrypt_token, encrypt_token


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeAsyncClient:
    response = FakeResponse()
    request_mock = Mock()
    post_mock = Mock()

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def request(self, *args, **kwargs):
        self.request_mock(*args, **kwargs)
        return self.response

    async def post(self, *args, **kwargs):
        self.post_mock(*args, **kwargs)
        return self.response


class TimeoutAsyncClient(FakeAsyncClient):
    async def request(self, *args, **kwargs):
        raise httpx.ReadTimeout("timeout")


@pytest.fixture(autouse=True)
def configured_blackboard(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "test")
    monkeypatch.setattr(settings, "BLACKBOARD_ENABLED", True)
    monkeypatch.setattr(settings, "BLACKBOARD_CLIENT_ID", "oauth-key")
    monkeypatch.setattr(settings, "BLACKBOARD_CLIENT_SECRET", "oauth-secret")
    monkeypatch.setattr(settings, "BLACKBOARD_SCOPES", "read offline")


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(User(id=1, email="student@example.test", hashed_password="x"))
    db.commit()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.mark.anyio
async def test_authorization_url_uses_public_route_pkce_and_offline_scope():
    url = await BlackboardConnector().build_authorization_url(
        "https://learn.example.edu", "opaque-state", "pkce-challenge"
    )
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert parsed.path == "/learn/api/public/v1/oauth2/authorizationcode"
    assert query["client_id"] == ["oauth-key"]
    assert query["scope"] == ["read offline"]
    assert query["state"] == ["opaque-state"]
    assert query["code_challenge"] == ["pkce-challenge"]
    assert query["code_challenge_method"] == ["S256"]


@pytest.mark.parametrize("origin", ["javascript:alert(1)", "https://user:pass@example.edu", "https://example.edu/path", "https://example.edu/?x=1"])
def test_malformed_origins_rejected(origin):
    with pytest.raises(ValueError):
        normalize_blackboard_origin(origin)


@pytest.mark.anyio
async def test_exchange_uses_public_token_route_and_pkce_verifier():
    FakeAsyncClient.response = FakeResponse(200, {"access_token": "secret", "expires_in": 900})
    FakeAsyncClient.post_mock.reset_mock()
    with patch("backend.lms.providers.blackboard.httpx.AsyncClient", FakeAsyncClient):
        payload = await BlackboardConnector().exchange_code_for_token("https://learn.example.edu", "code", "verifier")
    assert payload["access_token"] == "secret"
    args, kwargs = FakeAsyncClient.post_mock.call_args
    assert args[0].endswith("/learn/api/public/v1/oauth2/token")
    assert kwargs["data"]["code_verifier"] == "verifier"
    assert kwargs["auth"] == ("oauth-key", "oauth-secret")


def test_tokens_are_encrypted():
    encrypted = encrypt_token("student-token")
    assert encrypted != "student-token"
    assert decrypt_token(encrypted) == "student-token"


def test_production_requires_explicit_encryption_key(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", None)
    with pytest.raises(RuntimeError, match="TOKEN_ENCRYPTION_KEY"):
        encrypt_token("must-not-use-default")


@pytest.mark.anyio
async def test_refresh_persists_rotated_tokens(db_session):
    connection = LMSConnection(
        user_id=1, provider="blackboard", base_url="https://learn.example.edu", status="connected",
        access_token_encrypted=encrypt_token("expired"), refresh_token_encrypted=encrypt_token("refresh"),
        token_expires_at=datetime.utcnow() - timedelta(seconds=1),
    )
    db_session.add(connection)
    db_session.commit()
    FakeAsyncClient.response = FakeResponse(200, {
        "access_token": "new-access", "refresh_token": "new-refresh", "expires_in": 1200, "scope": "read offline"
    })
    with patch("backend.lms.blackboard_client.httpx.AsyncClient", FakeAsyncClient):
        token = await BlackboardClient(connection, db_session).access_token()
    assert token == "new-access"
    assert decrypt_token(connection.refresh_token_encrypted) == "new-refresh"
    assert connection.token_expires_at > datetime.utcnow()


@pytest.mark.anyio
@pytest.mark.parametrize("status_code,expected", [(401, 401), (403, 403), (429, 429)])
async def test_probe_sanitizes_blackboard_http_errors(db_session, status_code, expected):
    connection = LMSConnection(
        user_id=1, provider="blackboard", base_url="https://learn.example.edu", status="connected",
        external_user_id="user-1", access_token_encrypted=encrypt_token("access"),
        token_expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db_session.add(connection)
    db_session.commit()
    FakeAsyncClient.response = FakeResponse(status_code, {"developer_message": "secret upstream body"})
    with patch("backend.lms.blackboard_client.httpx.AsyncClient", FakeAsyncClient):
        with pytest.raises(BlackboardAPIError) as exc:
            await BlackboardClient(connection, db_session).probe()
    assert exc.value.status_code == expected
    assert "secret upstream body" not in str(exc.value)


@pytest.mark.anyio
async def test_probe_rejects_malformed_response(db_session):
    connection = LMSConnection(
        user_id=1, provider="blackboard", base_url="https://learn.example.edu", status="connected",
        external_user_id="user-1", access_token_encrypted=encrypt_token("access"),
        token_expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db_session.add(connection)
    db_session.commit()
    FakeAsyncClient.response = FakeResponse(200, ValueError("bad json"))
    with patch("backend.lms.blackboard_client.httpx.AsyncClient", FakeAsyncClient):
        with pytest.raises(BlackboardAPIError, match="malformed JSON"):
            await BlackboardClient(connection, db_session).probe()


@pytest.mark.anyio
async def test_network_timeout_is_sanitized(db_session):
    connection = LMSConnection(
        user_id=1, provider="blackboard", base_url="https://learn.example.edu", status="connected",
        external_user_id="user-1", access_token_encrypted=encrypt_token("access"),
        token_expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db_session.add(connection)
    db_session.commit()
    with patch("backend.lms.blackboard_client.httpx.AsyncClient", TimeoutAsyncClient):
        with pytest.raises(BlackboardAPIError):
            await BlackboardClient(connection, db_session).probe()


@pytest.mark.anyio
async def test_production_connector_never_returns_fake_courses():
    with pytest.raises(BlackboardAPIError) as exc:
        await BlackboardConnector().get_courses(None)
    assert exc.value.status_code == 501
