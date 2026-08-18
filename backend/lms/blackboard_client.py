import ipaddress
from datetime import datetime, timedelta
from urllib.parse import quote, urlsplit, urlunsplit

import httpx
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import LMSConnection
from backend.services.token_service import decrypt_token, encrypt_token


class BlackboardAPIError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def normalize_blackboard_origin(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        raise ValueError("A Blackboard site hostname or HTTPS origin is required.")
    if "://" not in raw:
        raw = f"https://{raw}"
    parsed = urlsplit(raw)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ValueError("Blackboard site must be a valid HTTP(S) origin.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Blackboard site must not contain credentials, query parameters, or fragments.")
    if parsed.path not in {"", "/"}:
        raise ValueError("Blackboard site must be an origin without a path.")

    env = settings.APP_ENV.lower()
    is_dev = env in {"development", "dev", "test", "testing", "local"}
    hostname = parsed.hostname.rstrip(".").lower()
    if not is_dev:
        if parsed.scheme != "https":
            raise ValueError("Blackboard sites must use HTTPS outside development.")
        if hostname == "localhost" or hostname.endswith(".localhost"):
            raise ValueError("Localhost is not a valid production Blackboard site.")
        try:
            address = ipaddress.ip_address(hostname)
            if not address.is_global:
                raise ValueError("Private or non-public IP addresses are not valid production Blackboard sites.")
        except ValueError as exc:
            if "not valid production" in str(exc):
                raise

    host = f"[{hostname}]" if ":" in hostname else hostname
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme.lower(), host, "", "", ""))


class BlackboardClient:
    def __init__(self, connection: LMSConnection, db: Session):
        if not connection.base_url:
            raise BlackboardAPIError("Blackboard connection has no institution URL configured.", 409)
        self.connection = connection
        self.db = db
        self.base_url = normalize_blackboard_origin(connection.base_url)

    async def _refresh(self) -> str:
        refresh_token = decrypt_token(self.connection.refresh_token_encrypted or "")
        if not refresh_token:
            self.connection.status = "reauthorization_required"
            self.db.commit()
            raise BlackboardAPIError("Blackboard authorization has expired; reconnect your account.", 401)
        if not settings.BLACKBOARD_CLIENT_ID or not settings.BLACKBOARD_CLIENT_SECRET:
            raise BlackboardAPIError("Blackboard OAuth credentials are not configured.", 503)

        try:
            async with httpx.AsyncClient(timeout=settings.BLACKBOARD_HTTP_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{self.base_url}/learn/api/public/v1/oauth2/token",
                    data={"grant_type": "refresh_token", "refresh_token": refresh_token},
                    auth=(settings.BLACKBOARD_CLIENT_ID, settings.BLACKBOARD_CLIENT_SECRET),
                )
        except httpx.TimeoutException as exc:
            raise BlackboardAPIError("Blackboard token refresh timed out.", 504) from exc
        except httpx.HTTPError as exc:
            raise BlackboardAPIError("Blackboard token refresh could not reach the institution.", 502) from exc
        if response.status_code != 200:
            self.connection.status = "reauthorization_required"
            self.db.commit()
            raise BlackboardAPIError("Blackboard rejected the saved authorization; reconnect your account.", 401)
        try:
            payload = response.json()
            access_token = payload["access_token"]
            expires_in = max(0, int(payload.get("expires_in", 3600)))
        except (ValueError, KeyError, TypeError) as exc:
            raise BlackboardAPIError("Blackboard returned a malformed token response.", 502) from exc

        self.connection.access_token_encrypted = encrypt_token(access_token)
        if payload.get("refresh_token"):
            self.connection.refresh_token_encrypted = encrypt_token(payload["refresh_token"])
        self.connection.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        self.connection.scopes = payload.get("scope") or self.connection.scopes
        self.connection.updated_at = datetime.utcnow()
        self.connection.status = "connected"
        self.db.commit()
        return access_token

    async def access_token(self) -> str:
        token = decrypt_token(self.connection.access_token_encrypted or "")
        expires = self.connection.token_expires_at
        if token and (expires is None or expires > datetime.utcnow() + timedelta(seconds=60)):
            return token
        return await self._refresh()

    async def request(self, method: str, path: str, **kwargs) -> dict:
        token = await self.access_token()
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {token}"
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=settings.BLACKBOARD_HTTP_TIMEOUT_SECONDS) as client:
                response = await client.request(method, url, headers=headers, **kwargs)
        except httpx.TimeoutException as exc:
            raise BlackboardAPIError("Blackboard did not respond before the request timed out.", 504) from exc
        except httpx.HTTPError as exc:
            raise BlackboardAPIError("Blackboard could not be reached.", 502) from exc

        if response.status_code == 401:
            token = await self._refresh()
            headers["Authorization"] = f"Bearer {token}"
            try:
                async with httpx.AsyncClient(timeout=settings.BLACKBOARD_HTTP_TIMEOUT_SECONDS) as client:
                    response = await client.request(method, url, headers=headers, **kwargs)
            except httpx.HTTPError as exc:
                raise BlackboardAPIError("Blackboard could not be reached after token refresh.", 502) from exc
        if response.status_code == 401:
            raise BlackboardAPIError("Blackboard authorization is no longer valid; reconnect your account.", 401)
        if response.status_code == 403:
            raise BlackboardAPIError("Blackboard denied access to this resource.", 403)
        if response.status_code == 429:
            raise BlackboardAPIError("Blackboard rate limit reached; try again later.", 429)
        if response.status_code >= 400:
            raise BlackboardAPIError("Blackboard returned an unexpected API error.", 502)
        try:
            payload = response.json()
        except ValueError as exc:
            raise BlackboardAPIError("Blackboard returned malformed JSON.", 502) from exc
        if not isinstance(payload, dict):
            raise BlackboardAPIError("Blackboard returned an unexpected response shape.", 502)
        return payload

    async def probe(self) -> dict:
        if not self.connection.external_user_id:
            raise BlackboardAPIError("Blackboard did not provide an authenticated user identifier.", 409)
        user_id = quote(self.connection.external_user_id, safe="")
        payload = await self.request("GET", f"/learn/api/public/v1/users/{user_id}")
        return {
            "provider": "blackboard",
            "connection_status": self.connection.status,
            "blackboard_site": self.base_url,
            "authenticated_user_id": str(payload.get("id") or self.connection.external_user_id),
            "token_expires_at": self.connection.token_expires_at,
            "api_reachable": True,
        }
