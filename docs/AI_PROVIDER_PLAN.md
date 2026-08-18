# AI Provider Integration & Routing Plan

This document outlines the strategy for model provider routing, local/cloud fallback procedures, and the newly added Embedding Provider Layer.

---

## 1. LLM Provider Architecture

NaySchool 3.0 supports a hybrid local/cloud strategy for LLM routing, governed by `LLMRouter`:

- **Ollama**: Serves as the primary local provider (default model: `llama3.2`).
- **OpenRouter**: Serves as a cloud provider fallback (default model: `deepseek/deepseek-chat`).
- **DeepSeek API**: Serves as a direct cloud provider fallback (default model: `deepseek-chat`).

### Routing Strategy
When a client requests `auto` provider:
1. Target the local Ollama instance.
2. If local Ollama is offline or unresponsive, and `ALLOW_CLOUD_AI=true` is set, fall back to OpenRouter.
3. If OpenRouter fails, attempt direct DeepSeek API.
4. Raise a `RuntimeError` if all routes are exhausted.

---

## 2. Embedding Provider Layer (Phase 2 Upgrade)

To power semantic search and grounding in the AI tutor, Phase 2 implements a specialized embedding routing layer.

### Base Interface (`BaseEmbeddingProvider`)
All embedding providers implement `backend/ai/embeddings/base.py`:
```python
class BaseEmbeddingProvider:
    name: str

    async def embed_texts(
        self,
        texts: list[str],
        model: str | None = None
    ) -> dict:
        raise NotImplementedError
```

### Standardized Output Schema
Regardless of the model, provider outputs are mapped to a uniform shape:
```json
{
  "provider": "ollama",
  "model": "nomic-embed-text",
  "dimension": 768,
  "embeddings": [
    [0.012, -0.043, 0.982, ...],
    [-0.054, 0.122, -0.009, ...]
  ]
}
```

### Supported Embedding Providers

#### 1. Ollama Embedding Provider (`backend/ai/embeddings/providers/ollama_embedding_provider.py`)
- **API Target**: Utilizes `OLLAMA_BASE_URL` (local or private cloud).
- **Authentication**: Sends `Authorization: Bearer <key>` headers if `OLLAMA_API_KEY` is provided; executes unauthenticated local HTTP queries otherwise.
- **Endpoint Version Support**: 
  - Attempts the batch `/api/embed` endpoint first.
  - If the batch endpoint fails (e.g., returning 404 on legacy Ollama instances), it falls back to concurrent requests against the legacy `/api/embeddings` single-prompt endpoint.

### Embedding Configuration Settings
The embedding pipeline is configured via `.env` variables loaded in `backend/config.py`:
```env
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSION=768
ENABLE_SEMANTIC_SEARCH=true
AUTO_EMBED_ON_UPLOAD=true
```

### Future Providers (TODOs)
- **OpenAI Embeddings**: Support `text-embedding-3-small` / `text-embedding-3-large`.
- **OpenRouter Embeddings**: Access cloud-hosted open embeddings models.
- **DeepSeek Embeddings**: Leverage direct cloud APIs if supported.
- **Sentence-Transformers**: Load lightweight embeddings models directly in-process via Python.
