import pytest
from unittest.mock import patch, AsyncMock
from backend.lms.providers.blackboard import BlackboardConnector
from backend.config import settings

@pytest.mark.anyio
async def test_blackboard_connector_unconfigured_error():
    connector = BlackboardConnector()
    
    # Temporarily disable Blackboard configuration
    with patch.object(settings, "BLACKBOARD_ENABLED", False):
        with pytest.raises(ValueError) as excinfo:
            await connector.build_authorization_url(user_id=1)
        assert "Blackboard integration is not configured" in str(excinfo.value)

@pytest.mark.anyio
async def test_blackboard_connector_get_courses_fallback():
    connector = BlackboardConnector()
    
    # When Blackboard is disabled/unconfigured
    with patch.object(settings, "BLACKBOARD_ENABLED", False):
        courses = await connector.get_courses(connection=None)
        assert len(courses) == 1
        assert courses[0].external_id == "bb-course-101"
        assert "CS101" in courses[0].code
        assert courses[0].instructor == "Dr. Alan Turing"

@pytest.mark.anyio
async def test_blackboard_connector_get_assignments_fallback():
    connector = BlackboardConnector()
    
    with patch.object(settings, "BLACKBOARD_ENABLED", False):
        assigns = await connector.get_assignments(connection=None, course_external_id="bb-course-101")
        assert len(assigns) == 1
        assert assigns[0].external_id == "bb-assign-1"
        assert assigns[0].course_external_id == "bb-course-101"
        assert "Big O notation" in assigns[0].title
