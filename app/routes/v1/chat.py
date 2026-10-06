from typing import Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.single_agent import run_single
from app.agents.manager import run_multi

chat_router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str
    mode: Literal["single", "multi"] = "multi"
    case_id: str = "adhoc"
    inject_coverage_failure: bool = False  # test hook: coverage worker returns a 500


@chat_router.post("")
async def chat(req: ChatRequest):
    """Chat entry point. `mode` switches between the single agent and the manager+workers squad."""
    if req.mode == "single":
        return await run_single(req.message, req.case_id)
    return await run_multi(req.message, req.case_id, req.inject_coverage_failure)
