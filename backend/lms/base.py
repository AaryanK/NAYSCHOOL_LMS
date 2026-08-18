from typing import List, Dict, Any

class BaseLMSConnector:
    provider_name: str

    async def build_authorization_url(self, base_url: str, state: str, code_challenge: str) -> str:
        raise NotImplementedError

    async def exchange_code_for_token(self, base_url: str, code: str, code_verifier: str) -> dict:
        raise NotImplementedError

    async def refresh_access_token(self, base_url: str, refresh_token: str) -> dict:
        raise NotImplementedError

    async def get_courses(self, connection) -> list:
        raise NotImplementedError

    async def get_assignments(self, connection, course_external_id: str) -> list:
        raise NotImplementedError

    async def get_course_content(self, connection, course_external_id: str) -> list:
        raise NotImplementedError

    async def get_announcements(self, connection, course_external_id: str) -> list:
        raise NotImplementedError

    async def get_grades(self, connection, course_external_id: str) -> list:
        raise NotImplementedError
