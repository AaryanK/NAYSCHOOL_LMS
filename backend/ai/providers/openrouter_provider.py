import httpx
from typing import List, Dict, Any, Optional
from backend.ai.base import BaseLLMProvider
from backend.config import settings

class OpenRouterProvider(BaseLLMProvider):
    name: str = "openrouter"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        target_model = model or settings.OPENROUTER_DEFAULT_MODEL
        api_key = settings.OPENROUTER_API_KEY
        
        # Guard key existence
        if not api_key or api_key == "in the .env file":
            raise ValueError("OpenRouter API key is not configured in .env.")

        base_url = settings.OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1"
        url = f"{base_url.rstrip('/')}/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://nayschool3.edu",
            "X-Title": "NaySchool 3.0",
            "Content-Type": "application/json"
        }

        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return {
                    "provider": self.name,
                    "model": target_model,
                    "content": content,
                    "raw": data
                }
        except Exception as e:
            raise RuntimeError(f"OpenRouter provider failed: {str(e)}")
