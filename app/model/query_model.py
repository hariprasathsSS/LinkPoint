from dataclasses import dataclass
from pydantic import BaseModel
from typing import List

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5

class SourceChunk(BaseModel):
    text: str
    score: float
    page: int | None = None
    chunk_id: str | None = None

class QueryResponse(BaseModel):
    trace_id: str
    query: str
    answer: str
    sources: List[SourceChunk]
