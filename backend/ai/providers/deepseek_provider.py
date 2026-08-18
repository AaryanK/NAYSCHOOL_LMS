import httpx
from typing import List, Dict, Any, Optional
from backend.ai.base import BaseLLMProvider
from backend.config import settings

class DeepSeekProvider(BaseLLMProvider):
    name: str = "deepseek"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        target_model = model or settings.DEEPSEEK_DEFAULT_MODEL
        api_key = settings.get_deepseek_key
        
        if not api_key or api_key == "in the .env file":
            raise ValueError("DeepSeek API key is not configured in .env.")

        base_url = settings.DEEPSEEK_BASE_URL or "https://api.deepseek.com"
        url = f"{base_url.rstrip('/')}/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
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
            raise RuntimeError(f"DeepSeek provider failed: {str(e)}")
