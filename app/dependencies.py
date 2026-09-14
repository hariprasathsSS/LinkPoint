# app/dependencies.py
from functools import lru_cache

from app.service.ingestion_service import IngestionService
from app.service.chunking_service import ChunkingService
from app.service.embedding_service import EmbeddingService
from app.service.vector_store_services import VectorStoreService
from app.utils.huggingface_embedder import HuggingFaceEmbedder
from app.parsers.parser_selector import ParserSelector
from app.embedding_factory import EmbeddingFactory
from app.service.prompt_service import PromptService
from app.service.llm_service import LLMService
from app.service.retrieval_service import RetrievalService
from app.service.reranker_service import RerankerService
from app.service.clustering_service import ClusteringService


@lru_cache(maxsize=1)
def get_ingestion_service():

    parser = ParserSelector()
    chunking_service = ChunkingService()
    embedder = EmbeddingFactory.create()
    embedding_service = EmbeddingService(embedder)
    clustering_service = ClusteringService()
    vector_store_service = VectorStoreService()


    return IngestionService(
        parser,
        chunking_service,
        embedding_service,
        clustering_service,
        vector_store_service
    )

@lru_cache(maxsize=1)
def get_query_service():

    embedder = EmbeddingFactory.create()
    embedding_service = EmbeddingService(embedder)
    vector_store_service = VectorStoreService()
    reranker_service = RerankerService()
    clustering_service = ClusteringService()
    prompt_service = PromptService()
    llm_service = LLMService()


    return RetrievalService(
        embedding_service,
        vector_store_service,
        reranker_service,
        clustering_service,
        prompt_service,
        llm_service
    )

@lru_cache(maxsize=1)
def get_vector_store_service():
    return VectorStoreService()

# # app/dependencies.py

# from app.service.ingestion_service import IngestionService
# from app.service.chunking_service import ChunkingService
# from app.service.embedding_service import EmbeddingService
# from app.service.vector_store_service import VectorStoreService

# from app.embeddings.huggingface_embedder import HuggingFaceEmbedder
# from app.parsers.parser_router import ParserRouter


# def get_ingestion_service():

#     # 🔹 Parser (dynamic selection)
#     parser_router = ParserRouter()

#     # 🔹 Chunking (single strategy)
#     chunking_service = ChunkingService(
#         chunk_size=500,
#         overlap=50
#     )

#     # 🔹 Embedding (HF model)
#     embedder = HuggingFaceEmbedder(
#         model_name="all-MiniLM-L6-v2"
#     )
#     embedding_service = EmbeddingService(embedder)

#     # 🔹 Vector DB (Qdrant)
#     vector_store_service = VectorStoreService(
#         collection_name="rag_collection",
#         host="localhost",
#         port=6333,
#         vector_size=384  # IMPORTANT for MiniLM
#     )

#     # 🔹 Final Orchestrator
#     return IngestionService(
#         parser_router=parser_router,
#         chunking_service=chunking_service,
#         embedding_service=embedding_service,
#         vector_store_service=vector_store_service
#     )
