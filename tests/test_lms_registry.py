import pytest
from backend.lms.connector_registry import get_lms_connector
from backend.lms.providers.blackboard import BlackboardConnector
from backend.lms.providers.canvas import CanvasConnector

def test_connector_registry_success():
    bb = get_lms_connector("blackboard")
    assert isinstance(bb, BlackboardConnector)
    assert bb.provider_name == "blackboard"
    
    # Case insensitivity check
    bb_upper = get_lms_connector("BlackBoard  ")
    assert isinstance(bb_upper, BlackboardConnector)
    
    canvas = get_lms_connector("canvas")
    assert isinstance(canvas, CanvasConnector)
    assert canvas.provider_name == "canvas"

def test_connector_registry_unsupported():
    with pytest.raises(ValueError) as excinfo:
        get_lms_connector("moodle")
    assert "Unsupported LMS provider" in str(excinfo.value)
