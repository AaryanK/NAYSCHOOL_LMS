from typing import List, Optional, Dict
from backend.ai.embeddings.base import BaseEmbeddingProvider
from backend.ai.embeddings.providers.ollama_embedding_provider import OllamaEmbeddingProvider
from backend.config import settings

class EmbeddingRouter:
    def __init__(self):
        self.providers: Dict[str, BaseEmbeddingProvider] = {
            "ollama": OllamaEmbeddingProvider(),
            # TODO: OpenAI-compatible embeddings
            # TODO: OpenRouter embeddings if supported
            # TODO: DeepSeek embeddings if supported
            # TODO: local sentence-transformers
        }

    async def embed_texts(
        self,
        texts: List[str],
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> dict:
        """
        Routes the embedding request to the configured or requested provider.
        """
        target_provider = provider or settings.EMBEDDING_PROVIDER or "ollama"
        target_provider = target_provider.lower()

        if target_provider not in self.providers:
            raise ValueError(f"Unknown Embedding provider requested: {target_provider}")

        return await self.providers[target_provider].embed_texts(texts, model=model)
