from typing import List, Dict, Any, Optional

class BaseLLMProvider:
    name: str = "BaseLLMProvider"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        Send chat message to provider and return normalized response format:
        {
            "provider": "...",
            "model": "...",
            "content": "...",
            "raw": {...}
        }
        """
        raise NotImplementedError
