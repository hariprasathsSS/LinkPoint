from pydantic import BaseModel
from typing import Any

class IngestResponse(BaseModel):
    document_id: str
    chunks_created: int
    status: str


class ChunkResponse(BaseModel):
    chunk_id: str
    text: str
    document_id: str | None = None
    page: int | None = None
    metadata: dict[str, Any] | None = None
