import httpx
from typing import List, Dict, Any, Optional
from backend.ai.base import BaseLLMProvider
from backend.config import settings

class OllamaProvider(BaseLLMProvider):
    name: str = "ollama"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        target_model = model or settings.OLLAMA_DEFAULT_MODEL
        base_url = settings.OLLAMA_BASE_URL or "http://localhost:11434"
        
        # Format correct endpoint
        url = base_url.rstrip("/")
        if not url.endswith("/api/chat"):
            if url.endswith("/api"):
                url = f"{url}/chat"
            else:
                url = f"{url}/api/chat"

        headers = {}
        if settings.OLLAMA_API_KEY and settings.OLLAMA_API_KEY.strip():
            headers["Authorization"] = f"Bearer {settings.OLLAMA_API_KEY.strip()}"


        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                content = data.get("message", {}).get("content", "")
                return {
                    "provider": self.name,
                    "model": target_model,
                    "content": content,
                    "raw": data
                }
        except Exception as e:
            raise RuntimeError(f"Ollama provider failed: {str(e)}")
