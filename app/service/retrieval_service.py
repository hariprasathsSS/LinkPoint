# app/service/retrieval_service.py

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

    def ask(self, request):

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

        print(combined_results[0])
        print("=============================\n")
        normalized_results = self._normalize_results(combined_results)
        print(normalized_results[0])
        print("=============================\n")
        reranked_results = self.reranker_service.rerank(
            query=request.query,
            results=normalized_results,
            top_k=request.top_k
        )
        print(reranked_results[0])
        print("=============================\n")
        # Step 3: Build Prompt
        prompt = self.prompt_service.build(
            query=request.query,
            results=reranked_results
        )

        # Step 4: LLM Call
        answer = self.llm_service.generate(prompt)

        return {
            "query": request.query,
            "answer": answer,
            "sources": [
                {
                    "text": r["result"]["payload"]["text"],
                    "score": r["score"],
                    "page": r["result"]["payload"].get("page")
                }
                for r in reranked_results
            ]
        }
