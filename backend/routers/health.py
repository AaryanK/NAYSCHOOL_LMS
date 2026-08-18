from fastapi import APIRouter
from backend.ai.llm_router import LLMRouter

router = APIRouter(prefix="/health", tags=["health"])
ai_router = APIRouter(prefix="/ai", tags=["ai-health"])

llm_router = LLMRouter()

@router.get("")
def get_health():
    return {"status": "healthy", "app": "NaySchool 3.0"}

@ai_router.get("/health")
def get_ai_health():
    return {
        "status": "active",
        "providers": llm_router.get_providers_status()
    }
