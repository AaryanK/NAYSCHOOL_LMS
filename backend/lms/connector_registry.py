from backend.lms.base import BaseLMSConnector
from backend.lms.providers.blackboard import BlackboardConnector
from backend.lms.providers.canvas import CanvasConnector

_connectors = {
    "blackboard": BlackboardConnector(),
    "canvas": CanvasConnector()
}

def get_lms_connector(provider: str) -> BaseLMSConnector:
    """
    Returns the connector singleton instance for a given provider name.
    Raises ValueError for unsupported providers.
    """
    provider_clean = provider.strip().lower()
    if provider_clean not in _connectors:
        raise ValueError(f"Unsupported LMS provider: '{provider}'")
    return _connectors[provider_clean]
