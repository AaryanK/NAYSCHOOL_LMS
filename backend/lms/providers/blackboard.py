from urllib.parse import urlencode

import httpx

from backend.config import settings
from backend.lms.base import BaseLMSConnector
from backend.lms.blackboard_client import BlackboardAPIError, normalize_blackboard_origin


class BlackboardConnector(BaseLMSConnector):
    provider_name = "blackboard"
    authorization_path = "/learn/api/public/v1/oauth2/authorizationcode"
    token_path = "/learn/api/public/v1/oauth2/token"

    def _require_oauth_config(self) -> None:
        if not settings.BLACKBOARD_ENABLED:
            raise ValueError("Blackboard integration is disabled.")
        if not settings.BLACKBOARD_CLIENT_ID or not settings.BLACKBOARD_CLIENT_SECRET:
            raise ValueError("Blackboard OAuth key/client ID and OAuth secret are required.")

    async def build_authorization_url(self, base_url: str, state: str, code_challenge: str) -> str:
        self._require_oauth_config()
        origin = normalize_blackboard_origin(base_url)
        params = {
            "response_type": "code",
            "client_id": settings.BLACKBOARD_CLIENT_ID,
            "redirect_uri": settings.BLACKBOARD_REDIRECT_URI,
            "scope": settings.BLACKBOARD_SCOPES or "read offline",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{origin}{self.authorization_path}?{urlencode(params)}"

    async def exchange_code_for_token(self, base_url: str, code: str, code_verifier: str) -> dict:
        self._require_oauth_config()
        origin = normalize_blackboard_origin(base_url)
        try:
            async with httpx.AsyncClient(timeout=settings.BLACKBOARD_HTTP_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{origin}{self.token_path}",
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": settings.BLACKBOARD_REDIRECT_URI,
                        "code_verifier": code_verifier,
                    },
                    auth=(settings.BLACKBOARD_CLIENT_ID, settings.BLACKBOARD_CLIENT_SECRET),
                )
        except httpx.TimeoutException as exc:
            raise BlackboardAPIError("Blackboard authorization timed out.", 504) from exc
        except httpx.HTTPError as exc:
            raise BlackboardAPIError("Blackboard authorization service could not be reached.", 502) from exc
        if response.status_code != 200:
            raise BlackboardAPIError("Blackboard rejected the authorization code.", 400)
        try:
            payload = response.json()
        except ValueError as exc:
            raise BlackboardAPIError("Blackboard returned a malformed token response.", 502) from exc
        if not isinstance(payload, dict) or not payload.get("access_token"):
            raise BlackboardAPIError("Blackboard token response did not contain an access token.", 502)
        return payload

    async def refresh_access_token(self, base_url: str, refresh_token: str) -> dict:
        self._require_oauth_config()
        origin = normalize_blackboard_origin(base_url)
        try:
            async with httpx.AsyncClient(timeout=settings.BLACKBOARD_HTTP_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{origin}{self.token_path}",
                    data={"grant_type": "refresh_token", "refresh_token": refresh_token},
                    auth=(settings.BLACKBOARD_CLIENT_ID, settings.BLACKBOARD_CLIENT_SECRET),
                )
        except httpx.HTTPError as exc:
            raise BlackboardAPIError("Blackboard token refresh failed to reach the institution.", 502) from exc
        if response.status_code != 200:
            raise BlackboardAPIError("Blackboard rejected the refresh token.", 401)
        try:
            payload = response.json()
        except ValueError as exc:
            raise BlackboardAPIError("Blackboard returned a malformed refresh response.", 502) from exc
        if not isinstance(payload, dict) or not payload.get("access_token"):
            raise BlackboardAPIError("Blackboard refresh response did not contain an access token.", 502)
        return payload

    async def get_courses(self, connection) -> list:
        raise BlackboardAPIError("Real Blackboard course sync is not implemented yet.", 501)

    async def get_assignments(self, connection, course_external_id: str) -> list:
        raise BlackboardAPIError("Real Blackboard assignment sync is not implemented yet.", 501)

    async def get_course_content(self, connection, course_external_id: str) -> list:
        raise BlackboardAPIError("Blackboard content sync is not implemented yet.", 501)

    async def get_announcements(self, connection, course_external_id: str) -> list:
        raise BlackboardAPIError("Blackboard announcement sync is not implemented yet.", 501)

    async def get_grades(self, connection, course_external_id: str) -> list:
        raise BlackboardAPIError("Blackboard grade sync is not implemented yet.", 501)
