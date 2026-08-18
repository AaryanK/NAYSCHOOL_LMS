class BaseEmbeddingProvider:
    name: str

    async def embed_texts(
        self,
        texts: list[str],
        model: str | None = None
    ) -> dict:
        """
        Generates embeddings for a list of texts.
        Returns a dict in the format:
        {
            "provider": str,
            "model": str,
            "dimension": int,
            "embeddings": list[list[float]]
        }
        """
        raise NotImplementedError
