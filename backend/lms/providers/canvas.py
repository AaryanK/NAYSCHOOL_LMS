from backend.lms.base import BaseLMSConnector

class CanvasConnector(BaseLMSConnector):
    provider_name = "canvas"

    async def build_authorization_url(self, user_id: int) -> str:
        # TODO: Implement Canvas OAuth2 authorization URL builder
        raise NotImplementedError("Canvas connector is scaffolded but not implemented.")

    async def exchange_code_for_token(self, code: str, state: str) -> dict:
        # TODO: Implement Canvas OAuth2 authorization code token exchange
        raise NotImplementedError("Canvas connector is scaffolded but not implemented.")

    async def refresh_access_token(self, refresh_token: str) -> dict:
        # TODO: Implement Canvas OAuth2 token refresh
        raise NotImplementedError("Canvas connector is scaffolded but not implemented.")

    async def get_courses(self, connection) -> list:
        # TODO: Implement Canvas course synchronization
        raise NotImplementedError("Canvas connector is scaffolded but not implemented.")

    async def get_assignments(self, connection, course_external_id: str) -> list:
        # TODO: Implement Canvas assignment synchronization
        raise NotImplementedError("Canvas connector is scaffolded but not implemented.")

    async def get_course_content(self, connection, course_external_id: str) -> list:
        raise NotImplementedError("Canvas connector is scaffolded but not implemented.")

    async def get_announcements(self, connection, course_external_id: str) -> list:
        raise NotImplementedError("Canvas connector is scaffolded but not implemented.")

    async def get_grades(self, connection, course_external_id: str) -> list:
        raise NotImplementedError("Canvas connector is scaffolded but not implemented.")
