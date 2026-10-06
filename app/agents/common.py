"""Shared building blocks for both arms: Groq chat wrapper, tool specs, tool dispatch.

Both arms use the same model, the same tools implementation, the same answer rules
and the same pricing, so only the orchestration pattern differs.
"""
import asyncio
import json
import time

from groq import Groq, RateLimitError

from app.config import Settings
from app.agent.tools import get_claim, get_adjuster_notes, search_policy, search_claims
from app.schema.agent_schema import ClaimStatus
from app.agents.telemetry import hop_label, record_usage

_client = Groq(api_key=Settings.GROQ_API_KEY)

ANSWER_RULES = (
    "Answer rules: be precise and complete. For policy questions, always state every critical condition: "
    "day thresholds, vacancy limits, clause/exclusion numbers (e.g. E-17), endorsement codes "
    "(e.g. HO-2306), form editions and dollar/percentage figures. Keep conditional answers "
    "conditional (e.g. 'covered subject to ...') - never simplify them into a flat yes/no. "
    "For claim searches, just provide the claim details. "
    "If the required information is not found in the policy documents or claim records, reply exactly: "
    "\"I'm sorry, but I don't have that information.\""
)

TOOL_SPECS = {
    "get_claim": {
        "type": "function",
        "function": {
            "name": "get_claim",
            "description": "Fetches base details of a claim (description, amount, excess, status).",
            "parameters": {
                "type": "object",
                "properties": {"claim_id": {"type": "string"}},
                "required": ["claim_id"],
            },
        },
    },
    "get_adjuster_notes": {
        "type": "function",
        "function": {
            "name": "get_adjuster_notes",
            "description": "Fetches the field adjuster's inspection notes. Needs the claim's current status (from get_claim).",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["OPEN", "UNDER_INVESTIGATION", "CLOSED"]},
                },
                "required": ["claim_id", "status"],
            },
        },
    },
    "search_policy": {
        "type": "function",
        "function": {
            "name": "search_policy",
            "description": "Searches the insurance policy documents for coverage, limits, conditions and exclusions.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    "search_claims": {
        "type": "function",
        "function": {
            "name": "search_claims",
            "description": "Searches claims by an attribute (e.g., 'customer_name', 'peril', 'status', 'date_of_loss').",
            "parameters": {
                "type": "object",
                "properties": {
                    "attribute": {"type": "string"},
                    "value": {"type": "string"}
                },
                "required": ["attribute", "value"],
            },
        },
    },
}


async def llm_chat(frm: str, to: str, messages: list, tools: list | None = None, max_tokens: int = 600):
    """One Groq call, recorded as a hand-off `frm -> to`. Retries only on 429s."""
    kwargs = dict(model=Settings.GROQ_MODEL, messages=messages, max_tokens=max_tokens, temperature=0.2)
    if tools:
        kwargs.update(tools=tools, tool_choice="auto")
    for attempt in range(4):
        try:
            resp = await asyncio.to_thread(lambda: _client.chat.completions.create(**kwargs))
            record_usage(resp.usage, frm, to)
            return resp.choices[0].message
        except RateLimitError:
            await asyncio.sleep(5 * (attempt + 1))
    raise RuntimeError("Groq rate limit not cleared after retries")


async def run_tool(name: str, args: dict, caller: str) -> str:
    # label nested LLM calls (RAG generation inside search_policy) as caller -> rag_tool
    with hop_label(caller, "rag_tool"):
        if name == "search_policy":
            return await search_policy(args.get("query", ""))
        if name == "get_claim":
            return get_claim(args.get("claim_id", ""))
        if name == "get_adjuster_notes":
            sv = args.get("status", "OPEN")
            status = ClaimStatus[sv] if sv in [e.name for e in ClaimStatus] else ClaimStatus.OPEN
            return get_adjuster_notes(args.get("claim_id", ""), status)
        if name == "search_claims":
            return search_claims(args.get("attribute", ""), args.get("value", ""))
    return f"Unknown tool {name}"


async def tool_loop(caller: str, callee_label: str, messages: list, tool_names: list[str], max_iters: int = 5) -> str:
    """Generic ReAct loop. Each iteration re-sends the full message history (that is the re-send cost)."""
    tools = [TOOL_SPECS[n] for n in tool_names]
    for _ in range(max_iters):
        msg = await llm_chat(caller, callee_label, messages, tools)
        if not msg.tool_calls:
            return msg.content or ""
        messages.append(msg)
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            if tc.function.name not in tool_names:
                result = f"Tool {tc.function.name} is not available to you."
            else:
                result = await run_tool(tc.function.name, args, callee_label)
            messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.function.name, "content": result})
    return "ERROR: max iterations reached without a final answer."
