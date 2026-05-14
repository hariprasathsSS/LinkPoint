from typing import List
from app.model.chunk_model import ChunkModel


class EmbeddingService:

    def __init__(self, embedding_model):
        self.embedding_model = embedding_model

    def generate_embeddings(self, chunks):
        texts = []
        valid_chunks = []

        for chunk in chunks:
            text = chunk.text  # ✅ correct for ChunkModel

            if text and text.strip():
                texts.append(text)
                valid_chunks.append(chunk)

        embeddings = self.embedding_model.encode(texts)

        return  embeddings
