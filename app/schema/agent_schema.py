from enum import Enum
from pydantic import BaseModel

class ClaimStatus(str, Enum):
    OPEN = "OPEN"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    CLOSED = "CLOSED"

class AgentRequest(BaseModel):
    claim_id: str

class AgentResponse(BaseModel):
    system: str
    claim_id: str
    decision: str
    latency_seconds: float
    total_tokens: int
    total_cost: float
    budget_termination: str | None = None
    trajectory: list[str] = []
