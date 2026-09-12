# app/routes/v1/chunk.py

from fastapi import APIRouter, Depends, HTTPException
from app.schema.response import ChunkResponse
from app.dependencies import get_vector_store_service

chunk_router = APIRouter()

_PAYLOAD_RESERVED = {"text", "document_id", "chunk_id", "page"}


@chunk_router.get("/chunk/{chunk_id}", response_model=ChunkResponse)
def get_chunk(chunk_id: str, vs=Depends(get_vector_store_service)):
    payload = vs.fetch_by_chunk_id(chunk_id)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"Chunk '{chunk_id}' not found")
    return ChunkResponse(
        chunk_id=chunk_id,
        text=payload.get("text", ""),
        document_id=payload.get("document_id"),
        page=payload.get("page"),
        metadata={k: v for k, v in payload.items() if k not in _PAYLOAD_RESERVED} or None,
    )
