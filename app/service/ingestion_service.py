# app/services/ingestion_service.py

from typing import List
from app.service.chunking_service import ChunkingService
from app.service.embedding_service import EmbeddingService
from app.service.vector_store_services import VectorStoreService
from app.service.clustering_service import ClusteringService

from app.model.chunk_model import ChunkModel
import uuid


class IngestionService:

    def __init__(
        self,
        parser,
        chunking_service: ChunkingService,
        embedding_service: EmbeddingService,
        clustering_service:ClusteringService,
        vector_store_service: VectorStoreService,
    ):
        self.parser = parser
        self.chunking_service = chunking_service
        self.embedding_service = embedding_service
        self.clustering_service = clustering_service
        self.vector_store_service = vector_store_service

    def ingest(self, file_path: str) -> dict:

        print("---- DEBUG START ----")

        parser = self.parser.get_parser(file_path)
        documents = parser.parse(file_path)

        if not documents:
            raise ValueError("No content extracted from PDF")

        print(f"Documents: {len(documents)}")

        all_chunks = []

        for doc in documents:
            text = doc["content"]
            metadata = doc["metadata"]

            chunks = self.chunking_service.chunk_text(text)

            for chunk in chunks:
                chunk.metadata.update(metadata)

            all_chunks.extend(chunks)

        print(f"Chunks: {len(all_chunks)}")

        print("Chunk sample:")
        for c in all_chunks[:5]:
            print(vars(c))

        embeddings = self.embedding_service.generate_embeddings(all_chunks)

        print(f"Embeddings: {len(embeddings)}")

        if len(all_chunks) != len(embeddings):
            raise ValueError("Mismatch between chunks and embeddings")

        document_id = str(uuid.uuid4())
        cluster_labels = self.clustering_service.train(embeddings)
        for i, chunk in enumerate(all_chunks):
            chunk.metadata["cluster_id"] = int(cluster_labels[i])

        self.vector_store_service.store(
            document_id=document_id,
            chunks=all_chunks,
            embeddings=embeddings
        )

        print("---- DEBUG END ----")

        return {
            "document_id": document_id,
            "chunks_created": len(all_chunks),
            "status": "success"
        }
