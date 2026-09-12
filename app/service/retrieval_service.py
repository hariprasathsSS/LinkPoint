# app/service/retrieval_service.py

from app.config import Settings
from app.utils.trace_logger import log_trace


class RetrievalService:

    def __init__(
        self,
        embedding_service,
        vector_store_service,
        reranker_service,
        clustering_service,
        prompt_service,
        llm_service
    ):
        self.embedding_service = embedding_service
        self.vector_store_service = vector_store_service
        self.reranker_service = reranker_service
        self.clustering_service = clustering_service
        self.prompt_service = prompt_service
        self.llm_service = llm_service

    def _normalize_results(self, results):
        return [
            {
                "id": r.id,
                "text": r.payload["text"],
                "score": r.score,
                "payload": r.payload
            }
            for r in results
            if r.payload.get("text")  # ponytail: skip points from partial/failed ingests; delete stale ones if this fires often
        ]
    def _merge_results(self, global_results, cluster_results):

        seen_ids = set()
        merged = []

        for res in global_results + cluster_results:
            point_id = res.id   # ✅ FIX

            if point_id not in seen_ids:
                seen_ids.add(point_id)
                merged.append(res)

        return merged

    async def ask(self, request):

        # Step 1: Query Embedding
        query_embedding = self.embedding_service.embedding_model.encode(
            [request.query]
        )[0]

        cluster_id = self.clustering_service.predict(query_embedding)

        global_results = self.vector_store_service.search(
            query_embedding=query_embedding,
            limit=20
        )

        cluster_results = self.vector_store_service.search(
            query_embedding=query_embedding,
            limit=20,
            filter={"cluster_id": cluster_id}
        )
        combined_results = self._merge_results(global_results, cluster_results)
        normalized_results = self._normalize_results(combined_results)
        reranked_results = self.reranker_service.rerank(
            query=request.query,
            results=normalized_results,
            top_k=request.top_k
        )

        # Step 3: Build Prompt
        prompt = self.prompt_service.build(
            query=request.query,
            results=reranked_results
        )

        # Step 4: LLM Call
        answer = self.llm_service.generate(prompt)

        sources = [
            {
                "text": r["result"]["payload"]["text"],
                "score": r["score"],
                "page": r["result"]["payload"].get("page"),
                "chunk_id": r["result"]["payload"].get("chunk_id"),
            }
            for r in reranked_results
        ]

        trace_id = log_trace(
            question=request.query,
            retrieved=[
                {"chunk_id": s["chunk_id"], "score": s["score"], "rank": i + 1, "text": s["text"]}
                for i, s in enumerate(sources)
            ],
            model=Settings.GROQ_MODEL,
            generation_params=self.llm_service.GENERATION_PARAMS,
            prompt_version=self.prompt_service.PROMPT_VERSION,
            answer=answer,
        )

        return {
            "trace_id": trace_id,
            "query": request.query,
            "answer": answer,
            "sources": sources,
        }
