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

class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[SourceChunk]
