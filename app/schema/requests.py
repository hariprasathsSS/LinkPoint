from pydantic import BaseModel

class IngestRequest(BaseModel):
    document_name: str
    metadata: dict | None = None
