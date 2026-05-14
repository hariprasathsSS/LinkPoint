from sentence_transformers import SentenceTransformer
from app.config import Settings

class HuggingFaceEmbedder:

    def __init__(self):
        self.model = SentenceTransformer(Settings.EMBEDDING_MODEL)

    def encode(self, texts):
        return self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=False
        )
