from typing import List, Dict, Any, Optional
from backend.ai.base import BaseLLMProvider
from backend.ai.providers.ollama_provider import OllamaProvider
from backend.ai.providers.openrouter_provider import OpenRouterProvider
from backend.ai.providers.deepseek_provider import DeepSeekProvider
from backend.config import settings

class LLMRouter:
    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {
            "ollama": OllamaProvider(),
            "openrouter": OpenRouterProvider(),
            "deepseek": DeepSeekProvider()
        }

    async def chat(
        self,
        messages: List[Dict[str, str]],
        provider: str = "auto",
        model: Optional[str] = None,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        provider = provider.lower() if provider else "auto"
        last_err = "No providers attempted."

        if provider != "auto":
            if provider not in self.providers:
                raise ValueError(f"Unknown AI provider requested: {provider}")
            return await self.providers[provider].chat(messages, model, temperature)

        # Auto Strategy
        # 1. Try DEFAULT_AI_PROVIDER if set and not "auto"
        default_p = settings.DEFAULT_AI_PROVIDER.lower() if settings.DEFAULT_AI_PROVIDER else "auto"
        if default_p != "auto" and default_p in self.providers:
            try:
                return await self.providers[default_p].chat(messages, model, temperature)
            except Exception as e:
                last_err = f"Default provider '{default_p}' failed: {str(e)}"

        # 2. Try Ollama (local)
        try:
            return await self.providers["ollama"].chat(messages, model, temperature)
        except Exception as ollama_err:
            last_err = f"Ollama failed: {str(ollama_err)}"

        # 3. Try OpenRouter (if ALLOW_CLOUD_AI is true and key configured)
        if settings.ALLOW_CLOUD_AI:
            or_key = settings.OPENROUTER_API_KEY
            if or_key and or_key != "in the .env file":
                try:
                    return await self.providers["openrouter"].chat(messages, model, temperature)
                except Exception as or_err:
                    last_err = f"OpenRouter failed: {str(or_err)}"

        # 4. Try DeepSeek (if ALLOW_CLOUD_AI is true and key configured)
        if settings.ALLOW_CLOUD_AI:
            ds_key = settings.get_deepseek_key
            if ds_key and ds_key != "in the .env file":
                try:
                    return await self.providers["deepseek"].chat(messages, model, temperature)
                except Exception as ds_err:
                    last_err = f"DeepSeek failed: {str(ds_err)}"

        raise RuntimeError(f"All AI providers failed. Detail: {last_err}")

    def get_providers_status(self) -> Dict[str, Dict[str, Any]]:
        or_key = settings.OPENROUTER_API_KEY
        ds_key = settings.get_deepseek_key
        ollama_key_present = bool(settings.OLLAMA_API_KEY and settings.OLLAMA_API_KEY.strip())
        ollama_mode = "cloud" if ollama_key_present else "local"
        return {
            "ollama": {
                "configured": True,
                "base_url": settings.OLLAMA_BASE_URL,
                "mode": ollama_mode,
                "api_key_present": ollama_key_present,
                "default_model": settings.OLLAMA_DEFAULT_MODEL
            },
            "openrouter": {
                "configured": bool(or_key and or_key.strip() and or_key != "in the .env file"),
                "default_model": settings.OPENROUTER_DEFAULT_MODEL
            },
            "deepseek": {
                "configured": bool(ds_key and ds_key.strip() and ds_key != "in the .env file"),
                "default_model": settings.DEEPSEEK_DEFAULT_MODEL
            }
        }

