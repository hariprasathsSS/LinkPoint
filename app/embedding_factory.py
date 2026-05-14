# app/embedding_factory.py

from app.config import settings
from app.utils.huggingface_embedder import HuggingFaceEmbedder


class EmbeddingFactory:

    @staticmethod
    def create():
        if settings.EMBEDDING_PROVIDER == "sentence_transformers":
            return HuggingFaceEmbedder()

        raise ValueError(f"Unsupported provider: {settings.EMBEDDING_PROVIDER}")
