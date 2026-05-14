from pydantic import BaseModel

class IngestResponse(BaseModel):
    document_id: str
    chunks_created: int
    status: str
