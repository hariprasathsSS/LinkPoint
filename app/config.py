# app/config.py

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    RERANKER_MODEL = os.getenv("RERANKER_MODEL")
    VECTOR_SIZE = int(os.getenv("VECTOR_SIZE", 384))

    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 500))
    CHUNK_OVERLAP_SIZE = int(os.getenv("CHUNK_OVERLAP_SIZE", 50))

    GROQ_API_KEY=os.getenv("GROQ_API_KEY")
    GROQ_MODEL=os.getenv("GROQ_MODEL")
    OLLAMA_PORT=os.getenv("OLLAMA_PORT")
    OLLAMA_HOST=os.getenv("OLLAMA_HOST")
    OLLAMA_MODEL=os.getenv("OLLAMA_MODEL")

settings = Settings()
