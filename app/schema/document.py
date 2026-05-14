from pydantic import BaseModel
from typing import List

class Chunk(BaseModel):
    content: str
    metadata: dict

class Document(BaseModel):
    id: str
    text: str
    chunks: List[Chunk]
