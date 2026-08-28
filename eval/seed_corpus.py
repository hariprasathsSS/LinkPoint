# eval/seed_corpus.py
#
# Ingests eval/corpus_pdfs/*.pdf through the REAL pipeline pieces (HybridParser
# for real table extraction -> ChunkingService -> EmbeddingService ->
# ClusteringService -> VectorStoreService), into a dedicated Qdrant collection
# so nothing touches the app's own `rag_collection` / `kmeans.pkl`.
#
# Prereqs: Qdrant running (cd app && docker-compose up -d).
# Run:     python eval/seed_corpus.py

from pathlib import Path

from app.config import settings
from app.embedding_factory import EmbeddingFactory
from app.parsers.hybrid_parser import HybridParser
from app.service.chunking_service import ChunkingService
from app.service.clustering_service import ClusteringService
from app.service.embedding_service import EmbeddingService
from app.service.vector_store_services import VectorStoreService

CORPUS_DIR = Path(__file__).parent / "corpus_pdfs"
COLLECTION_NAME = "insurance_claims_eval"
KMEANS_PATH = str(Path(__file__).parent / "kmeans_insurance_eval.pkl")
DOCUMENT_ID = "insurance-eval-corpus"


def main() -> None:
    parser = HybridParser()
    chunking_service = ChunkingService(
        chunk_size=settings.CHUNK_SIZE, overlap=settings.CHUNK_OVERLAP_SIZE
    )
    embedding_service = EmbeddingService(EmbeddingFactory.create())
    clustering_service = ClusteringService(model_path=KMEANS_PATH)
    vector_store = VectorStoreService(collection_name=COLLECTION_NAME)

    pdf_paths = sorted(CORPUS_DIR.glob("*.pdf"))
    if not pdf_paths:
        raise SystemExit(f"No PDFs found in {CORPUS_DIR} - run build_corpus_pdfs.py first")

    all_chunks = []
    for pdf_path in pdf_paths:
        documents = parser.parse(str(pdf_path))
        for doc in documents:
            text = doc["content"]
            if not text or not text.strip():
                continue
            chunks = chunking_service.chunk_text(text)
            for chunk in chunks:
                chunk.metadata.update(doc["metadata"])
            all_chunks.extend(chunks)
        print(f"  {pdf_path.name}: {len(documents)} pages parsed")

    print(f"Total chunks: {len(all_chunks)}")

    embeddings = embedding_service.generate_embeddings(all_chunks)
    if len(all_chunks) != len(embeddings):
        raise ValueError("Mismatch between chunks and embeddings")

    # One KMeans fit over the WHOLE corpus (all docs together) so cluster ids
    # are consistent across documents at query time - fitting separately per
    # document (as the live single-file /ingest path does) would make the
    # cluster-filtered search meaningless for a multi-document corpus.
    cluster_labels = clustering_service.train(embeddings)
    for i, chunk in enumerate(all_chunks):
        chunk.metadata["cluster_id"] = int(cluster_labels[i])

    vector_store.store(document_id=DOCUMENT_ID, chunks=all_chunks, embeddings=embeddings)

    count = vector_store.client.count(collection_name=COLLECTION_NAME).count
    print(f"Stored into Qdrant collection '{COLLECTION_NAME}' - point count: {count}")


if __name__ == "__main__":
    main()
