from sentence_transformers import CrossEncoder
from app.config import Settings

class RerankerService:

    def __init__(self):
        self.model = CrossEncoder(Settings.RERANKER_MODEL)

    def rerank(self, query: str,results,top_k:int):

        pairs = []

        for r in results:
            pairs.append([query,r["payload"]["text"]])
        scores = self.model.predict(pairs)
        reranked = []
        for score,result in zip(scores,results):
            reranked.append({
                "score":score,
                "result":result
            })
        reranked.sort(key=lambda x:x['score'],reverse=True)

        return reranked[:top_k]

    # def rerank(self, query, results, top_k=3):

    #     pairs = [
    #         [query, r.payload["text"]]
    #         for r in results
    #     ]

    #     scores = self.model.predict(pairs)

    #     scored_results = list(zip(scores, results))

    #     scored_results.sort(
    #         key=lambda x: x[0],
    #         reverse=True
    #     )

    #     reranked_results = [
    #         result
    #         for score, result in scored_results[:top_k]
    #     ]

    #     return reranked_results
