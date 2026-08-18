import httpx
import asyncio
from typing import List, Optional
from backend.ai.embeddings.base import BaseEmbeddingProvider
from backend.config import settings

class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    name: str = "ollama"

    async def embed_texts(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> dict:
        target_model = model or settings.EMBEDDING_MODEL or "nomic-embed-text"
        base_url = settings.OLLAMA_BASE_URL or "http://localhost:11434"
        
        if not texts:
            return {
                "provider": self.name,
                "model": target_model,
                "dimension": settings.EMBEDDING_DIMENSION or 768,
                "embeddings": []
            }

        url = base_url.rstrip("/")
        if url.endswith("/api/chat"):
            base_api = url[:-9]
        elif url.endswith("/api"):
            base_api = url
        else:
            base_api = f"{url}/api"

        headers = {}
        if settings.OLLAMA_API_KEY and settings.OLLAMA_API_KEY.strip():
            headers["Authorization"] = f"Bearer {settings.OLLAMA_API_KEY.strip()}"

        # Try /api/embed first (Ollama newer API supporting list inputs)
        embed_url = f"{base_api}/embed"
        payload = {
            "model": target_model,
            "input": texts
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(embed_url, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    embeddings = data.get("embeddings", [])
                    if embeddings:
                        dimension = len(embeddings[0])
                        return {
                            "provider": self.name,
                            "model": target_model,
                            "dimension": dimension,
                            "embeddings": embeddings
                        }
        except Exception:
            # Fallback to the legacy/single endpoint
            pass

        # Fallback to /api/embeddings for each text
        embeddings_url = f"{base_api}/embeddings"
        
        async def embed_single(text: str) -> List[float]:
            single_payload = {
                "model": target_model,
                "prompt": text
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(embeddings_url, json=single_payload, headers=headers)
                resp.raise_for_status()
                return resp.json().get("embedding", [])

        try:
            tasks = [embed_single(text) for text in texts]
            embeddings = await asyncio.gather(*tasks)
            if embeddings and all(embeddings):
                dimension = len(embeddings[0])
                return {
                    "provider": self.name,
                    "model": target_model,
                    "dimension": dimension,
                    "embeddings": embeddings
                }
            else:
                raise ValueError("Received empty embeddings from Ollama")
        except Exception as e:
            raise RuntimeError(f"Ollama embedding provider failed: {str(e)}")
