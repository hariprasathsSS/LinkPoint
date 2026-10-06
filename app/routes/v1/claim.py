from fastapi import APIRouter

from app.schema.agent_schema import AgentResponse
from app.agent.react_agent import run_agent
from app.agent.fixed_workflow import run_workflow
from app.mcp.mcp_agent import run_mcp_agent  # Week 9: MCP-aware agent

claim_router = APIRouter(prefix="/claim", tags=["Claims"])

@claim_router.post("/agent/{claim_id}", response_model=AgentResponse)
async def process_claim_agent(claim_id: str):
    """Run a claim through the original hard-coded ReAct Agent."""
    return await run_agent(claim_id)


@claim_router.post("/workflow/{claim_id}", response_model=AgentResponse)
async def process_claim_workflow(claim_id: str):
    """Run a claim through the Fixed Workflow."""
    return await run_workflow(claim_id)


@claim_router.post("/mcp-agent/{claim_id}", response_model=AgentResponse)
async def process_claim_mcp_agent(claim_id: str):
    """
    Week 9 — MCP-aware agent.
    Discovers tools dynamically from all servers listed in app/mcp/mcp_config.json.
    Adding a new MCP server requires only a config edit — this route never changes.
    """
    return await run_mcp_agent(claim_id)
