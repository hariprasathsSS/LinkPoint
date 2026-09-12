# app/service/vector_store_service.py
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams,Filter,FieldCondition,MatchValue
from typing import List
from app.model.chunk_model import ChunkModel
from app.config import Settings

class VectorStoreService:

    def __init__(
        self,
        collection_name: str = "rag_collection",
        host: str = "localhost",
        port: int = 6333,
    ):
        self.collection_name = collection_name
        self.client = QdrantClient(host=host, port=port)

        self._ensure_collection(Settings.VECTOR_SIZE)

    def _ensure_collection(self, vector_size: int):
        collections = self.client.get_collections().collections
        existing = [c.name for c in collections]

        if self.collection_name not in existing:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )

    def store(
        self,
        document_id: str,
        chunks: List[ChunkModel],
        embeddings: List[List[float]]
    ):
        points = []
        print("vector db storage")
        for i, chunk in enumerate(chunks):
            if i >= len(embeddings):
                print("i >= len(embeddings)")
                break  # safety
            point_id = f"{document_id}_{i}"

            payload = {
                "text": chunk.text,
                "document_id": document_id,
                "chunk_id": point_id,
                **chunk.metadata
            }

            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embeddings[i],
                payload=payload
            )

            points.append(point)

        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
    def health_check(self):

        try:
            collections = self.client.get_collections()
            return {
                "status": "connected",
                "collections": [c.name for c in collections.collections]
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    def search(self, query_embedding: List[float], limit: int = 5):
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit
        )
        return results

    def search(self, query_embedding, limit=10, filter=None):

        qdrant_filter = None

        if filter:
            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key=f"metadata.{key}",
                        match=MatchValue(value=value)
                    )
                    for key, value in filter.items()
                ]
            )

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding.detach().cpu().tolist(),
            limit=limit,
            query_filter=qdrant_filter,
        ).points

        return results

    def fetch_by_chunk_id(self, chunk_id: str) -> dict | None:
        results, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="chunk_id", match=MatchValue(value=chunk_id))]
            ),
            with_payload=True,
            limit=1
        )
        if not results:
            return None
        return results[0].payload
