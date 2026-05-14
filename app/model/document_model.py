from dataclasses import dataclass
from typing import List
from .chunk_model import ChunkModel

@dataclass
class DocumentModel:
    id: str
    raw_text: str
    chunks: List[ChunkModel]
