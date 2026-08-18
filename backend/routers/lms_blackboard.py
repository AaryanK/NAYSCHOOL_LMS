from fastapi import APIRouter, Depends
from backend.deps import get_current_user
from backend.models import User

router = APIRouter(prefix="/lms/blackboard", tags=["lms-blackboard"])

@router.get("/status")
def get_blackboard_status(current_user: User = Depends(get_current_user)):
    return {
        "provider": "blackboard",
        "status": "scaffolded",
        "implemented": False,
        "message": "Legacy endpoint. Please use the new unified LMS routes: GET /api/lms/providers.",
        "next_steps": [
            "Anthology/Blackboard Developer Portal app registration",
            "Obtain Application ID, OAuth key, and OAuth secret",
            "Request University Blackboard Administrator authorization/installation",
            "Implement OAuth2 Authorization Code flow to securely exchange tokens",
            "Map courses, materials, announcements, and grades to database schema"
        ]
    }

@router.post("/connect-placeholder")
def connect_blackboard_placeholder(current_user: User = Depends(get_current_user)):
    return {
        "status": "placeholder_connection",
        "message": (
            "Legacy endpoint. Please use POST /api/lms/blackboard/connect. "
            "Blackboard integration requires setup in the Anthology Developer Portal. "
            "To connect in production, you will need: 1. An Application ID, 2. An OAuth Key, "
            "and 3. An OAuth Secret. A University Blackboard Admin must approve and install "
            "the Application ID. For security, we recommend requesting read-only access scopes first."
        ),
        "next_actions": [
            "Register at developer.anthology.com",
            "Add registered App ID under REST API Integrations in Blackboard System Admin panel"
        ]
    }

@router.post("/sync-placeholder")
def sync_blackboard_placeholder(current_user: User = Depends(get_current_user)):
    return {
        "status": "success",
        "message": "Mock Blackboard synchronization completed successfully. Note: Please use POST /api/lms/{connection_id}/sync for new sync flow.",
        "synced_courses_count": 1,
        "synced_assignments_count": 1,
        "detail": {
            "courses": [
                {
                    "name": "Introduction to Computer Science (Blackboard Sync)",
                    "code": "CS101",
                    "instructor": "Dr. Alan Turing"
                }
            ],
            "assignments": [
                {
                    "title": "Blackboard HW 1 - Big O notation",
                    "due_date": "2026-06-30T23:59:59Z"
                }
            ]
        }
    }
