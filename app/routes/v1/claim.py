from fastapi import APIRouter

from app.schema.agent_schema import AgentResponse
from app.agent.react_agent import run_agent
from app.agent.fixed_workflow import run_workflow

claim_router = APIRouter(prefix="/claim", tags=["Claims"])

@claim_router.post("/agent/{claim_id}", response_model=AgentResponse)
async def process_claim_agent(claim_id: str):
    """Run a claim through the ReAct Agent."""
    return await run_agent(claim_id)


@claim_router.post("/workflow/{claim_id}", response_model=AgentResponse)
async def process_claim_workflow(claim_id: str):
    """Run a claim through the Fixed Workflow."""
    return await run_workflow(claim_id)
