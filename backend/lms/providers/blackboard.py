import logging
import httpx
from typing import List
from backend.config import settings
from backend.lms.base import BaseLMSConnector
from backend.lms.schemas import LMSCourse, LMSAssignment, LMSContentItem, LMSAnnouncement, LMSGradeItem

logger = logging.getLogger(__name__)

class BlackboardConnector(BaseLMSConnector):
    provider_name = "blackboard"

    async def build_authorization_url(self, user_id: int) -> str:
        if not settings.BLACKBOARD_ENABLED or not settings.BLACKBOARD_BASE_URL or not settings.BLACKBOARD_CLIENT_ID:
            raise ValueError("Blackboard integration is not configured or enabled.")
            
        base_url = settings.BLACKBOARD_BASE_URL.rstrip("/")
        # State encodes user_id to verify on callback
        state = f"{user_id}:blackboard_auth"
        redirect_uri = settings.BLACKBOARD_REDIRECT_URI
        scopes = settings.BLACKBOARD_SCOPES or "read"
        
        # Standard Blackboard OAuth2 Authorization URL
        auth_url = (
            f"{base_url}/learn/api/v1/oauth2/authorizationcode"
            f"?response_type=code"
            f"&client_id={settings.BLACKBOARD_CLIENT_ID}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scopes}"
            f"&state={state}"
        )
        return auth_url

    async def exchange_code_for_token(self, code: str, state: str) -> dict:
        if not settings.BLACKBOARD_BASE_URL or not settings.BLACKBOARD_CLIENT_ID or not settings.BLACKBOARD_CLIENT_SECRET:
            raise ValueError("Blackboard environment configuration (base URL, client ID, or client secret) is missing.")
            
        base_url = settings.BLACKBOARD_BASE_URL.rstrip("/")
        token_url = f"{base_url}/learn/api/v1/oauth2/token"
        
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.BLACKBOARD_REDIRECT_URI
        }
        
        # Blackboard Learn OAuth2 uses basic authentication with client_id:client_secret
        auth = (settings.BLACKBOARD_CLIENT_ID, settings.BLACKBOARD_CLIENT_SECRET)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data, auth=auth)
            if response.status_code != 200:
                logger.error(f"Failed to exchange code for token: {response.text}")
                raise RuntimeError(f"Blackboard OAuth exchange failed: {response.text}")
            
            return response.json()

    async def refresh_access_token(self, refresh_token: str) -> dict:
        if not settings.BLACKBOARD_BASE_URL or not settings.BLACKBOARD_CLIENT_ID or not settings.BLACKBOARD_CLIENT_SECRET:
            raise ValueError("Blackboard environment configuration is missing.")
            
        base_url = settings.BLACKBOARD_BASE_URL.rstrip("/")
        token_url = f"{base_url}/learn/api/v1/oauth2/token"
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        auth = (settings.BLACKBOARD_CLIENT_ID, settings.BLACKBOARD_CLIENT_SECRET)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data, auth=auth)
            if response.status_code != 200:
                raise RuntimeError(f"Blackboard OAuth refresh failed: {response.text}")
            return response.json()

    async def get_courses(self, connection) -> list:
        # Check configuration
        if not settings.BLACKBOARD_ENABLED or not settings.BLACKBOARD_BASE_URL:
            logger.warning("Blackboard is disabled or not configured. Returning scaffolded courses.")
            return [
                LMSCourse(
                    external_id="bb-course-101",
                    name="Introduction to Computer Science (Blackboard Sync)",
                    code="CS101",
                    description="Scaffolded Blackboard course for local verification.",
                    instructor="Dr. Alan Turing",
                    raw={"scaffolded": True}
                )
            ]

        # Real API call placeholder
        # Standard route is GET /learn/api/v1/courses or user specific courses
        # Return scaffolded details for now unless actively integrated
        return [
            LMSCourse(
                external_id="bb-course-101",
                name="Introduction to Computer Science (Blackboard Sync)",
                code="CS101",
                description="Scaffolded Blackboard course for local verification.",
                instructor="Dr. Alan Turing",
                raw={"scaffolded": True}
            )
        ]

    async def get_assignments(self, connection, course_external_id: str) -> list:
        if not settings.BLACKBOARD_ENABLED or not settings.BLACKBOARD_BASE_URL:
            return [
                LMSAssignment(
                    external_id="bb-assign-1",
                    course_external_id=course_external_id,
                    title="Blackboard HW 1 - Big O notation",
                    description="Analyze the time complexity of sorting algorithms.",
                    due_date=None,
                    points_possible=100.0,
                    raw={"scaffolded": True}
                )
            ]
        return [
            LMSAssignment(
                external_id="bb-assign-1",
                course_external_id=course_external_id,
                title="Blackboard HW 1 - Big O notation",
                description="Analyze the time complexity of sorting algorithms.",
                due_date=None,
                points_possible=100.0,
                raw={"scaffolded": True}
            )
        ]

    async def get_course_content(self, connection, course_external_id: str) -> list:
        return []

    async def get_announcements(self, connection, course_external_id: str) -> list:
        return []

    async def get_grades(self, connection, course_external_id: str) -> list:
        return []
