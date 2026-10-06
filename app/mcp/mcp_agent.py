"""
app/mcp/mcp_agent.py
====================
MCP-aware ReAct agent — the Week 9 replacement for the hard-coded react_agent.py.

KEY DESIGN:
    - Reads server list from mcp_config.json at startup.
    - Connects to EVERY server listed and runs tools/list on each.
    - Merges all discovered tools into one flat list for the LLM.
    - Routes every tool call back to the correct server automatically.
    - Adding a new server = edit mcp_config.json only. THIS FILE NEVER CHANGES.

That last point is the entire point of Week 9 / MCP.

Architecture roles (as per MCP spec):
    HOST   = this process (manages the loop, owns the model call)
    CLIENT = the MCP client sessions inside this process
    SERVER = policy_server.py / claims_server.py (subprocess, stdio)

The LLM call happens HERE (line marked # <-- LLM CALL).
It never happens inside the MCP servers.
"""

import asyncio
import json
import os
import re
import time
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from groq import Groq
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.config import Settings
from app.schema.agent_schema import AgentResponse

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CONFIG_PATH = Path(__file__).parent / "mcp_config.json"

# Agent budgets (identical to the original react_agent.py)
MAX_ITERS           = 7
MAX_TOKENS          = 4000
MAX_COST            = 0.50
WALL_CLOCK_TIMEOUT  = 45

GROQ_COST_PER_1K_IN  = 0.0005
GROQ_COST_PER_1K_OUT = 0.0015

client = Groq(api_key=Settings.GROQ_API_KEY)


# ---------------------------------------------------------------------------
# MCP connection helpers
# ---------------------------------------------------------------------------

def _load_config() -> list[dict]:
    """Load server list from mcp_config.json."""
    with open(CONFIG_PATH, "r") as f:
        cfg = json.load(f)
    return cfg["servers"]


async def _connect_server(
    stack: AsyncExitStack,
    server_cfg: dict,
) -> tuple[ClientSession, list[dict]]:
    """
    Spawn one MCP server subprocess, run initialize + tools/list,
    and return (session, tools_schema_list).

    The session stays alive for the lifetime of `stack`.
    """
    params = StdioServerParameters(
        command=server_cfg["command"],
        args=server_cfg["args"],
        env=server_cfg.get("env") or None,
    )

    read, write = await stack.enter_async_context(stdio_client(params))
    session: ClientSession = await stack.enter_async_context(
        ClientSession(read, write)
    )

    # MCP handshake: initialize
    await session.initialize()

    # MCP discovery: tools/list
    tools_result = await session.list_tools()

    # Convert MCP tool schema → Groq-compatible function schema
    groq_tools = []
    for t in tools_result.tools:
        groq_tools.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.inputSchema,
            },
        })

    return session, groq_tools


# ---------------------------------------------------------------------------
# Main agent entry point
# ---------------------------------------------------------------------------

async def run_mcp_agent(claim_id: str) -> AgentResponse:
    """
    MCP-aware ReAct agent.

    Discovers tools dynamically from all servers in mcp_config.json,
    then runs the standard Groq tool-use loop.
    """
    start_time = time.time()
    servers = _load_config()

    async with AsyncExitStack() as stack:
        # ----------------------------------------------------------------
        # Connect to every server and collect tools
        # ----------------------------------------------------------------
        all_groq_tools: list[dict]      = []
        tool_to_session: dict[str, ClientSession] = {}

        for srv in servers:
            session, groq_tools = await _connect_server(stack, srv)
            for gt in groq_tools:
                tool_name = gt["function"]["name"]
                all_groq_tools.append(gt)
                tool_to_session[tool_name] = session  # routing table

        # ----------------------------------------------------------------
        # ReAct loop
        # ----------------------------------------------------------------
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior insurance claims triage agent. "
                    "Determine if a claim should be approved or denied and calculate "
                    "the final payout (Claim Amount - Excess). "
                    "MUST use tools to gather information. Never guess. "
                    "Once you have all info, return your final decision starting with "
                    "'APPROVED' or 'DENIED', followed by the math."
                ),
            },
            {"role": "user", "content": f"Please triage claim {claim_id}"},
        ]

        iters            = 0
        total_tokens     = 0
        total_cost       = 0.0
        termination_reason: str | None = None
        trajectory: list[str] = []
        decision = "No decision reached."

        while True:
            # Budget checks
            if iters >= MAX_ITERS:
                termination_reason = "MAX_ITERS_REACHED"
                break
            if time.time() - start_time > WALL_CLOCK_TIMEOUT:
                termination_reason = "WALL_CLOCK_TIMEOUT"
                break
            if total_tokens > MAX_TOKENS:
                termination_reason = "MAX_TOKENS_REACHED"
                break
            if total_cost > MAX_COST:
                termination_reason = "MAX_COST_REACHED"
                break

            iters += 1

            # <-- LLM CALL  (model runs HERE, never in the MCP server)
            response = client.chat.completions.create(
                model=Settings.GROQ_MODEL,
                messages=messages,
                tools=all_groq_tools,   # dynamically discovered — not hard-coded
                tool_choice="auto",
                max_tokens=500,
            )

            msg   = response.choices[0].message
            usage = response.usage

            if usage:
                total_tokens += usage.total_tokens
                total_cost   += (
                    (usage.prompt_tokens   / 1000) * GROQ_COST_PER_1K_IN
                    + (usage.completion_tokens / 1000) * GROQ_COST_PER_1K_OUT
                )

            if msg.tool_calls:
                messages.append(msg)

                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    args    = json.loads(tc.function.arguments)

                    # Route the call to the correct MCP server
                    session = tool_to_session.get(fn_name)
                    if session is None:
                        result = (
                            f"Unknown tool '{fn_name}'. "
                            f"Available tools: {list(tool_to_session.keys())}. "
                            f"Please retry with a valid tool name."
                        )
                    else:
                        # MCP tools/call
                        mcp_result = await session.call_tool(fn_name, arguments=args)
                        # Extract text content from the MCP result
                        result = "\n".join(
                            c.text for c in mcp_result.content if hasattr(c, "text")
                        )

                    trajectory.append(fn_name)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": fn_name,
                        "content": result,
                    })
            else:
                # Final answer from the model
                decision = msg.content or "No decision."

                # Output validator: block prompt-injected payouts
                if "APPROVED" in decision.upper():
                    payouts = [
                        float(n.replace(",", ""))
                        for n in re.findall(
                            r"\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)", decision
                        )
                    ]
                    if payouts:
                        try:
                            # Re-fetch claim facts directly, bypassing the AI
                            facts_session = tool_to_session.get("get_claim")
                            if facts_session:
                                raw = await facts_session.call_tool(
                                    "get_claim", arguments={"claim_id": claim_id}
                                )
                                facts_text = "\n".join(
                                    c.text for c in raw.content if hasattr(c, "text")
                                )
                                m = re.search(
                                    r"Claim Amount: \$([0-9,.]+)", facts_text
                                )
                                if m:
                                    max_limit = float(m.group(1).replace(",", ""))
                                    if any(p > max_limit for p in payouts):
                                        decision = (
                                            f"BLOCKED BY SECURITY VALIDATOR: "
                                            f"Agent attempted to approve ${max(payouts):.2f} "
                                            f"which exceeds the original claim limit "
                                            f"(${max_limit:.2f}). Prompt injection detected."
                                        )
                        except Exception:
                            pass
                break

    if termination_reason:
        decision = f"ERROR: Agent terminated early — {termination_reason}."

    return AgentResponse(
        system="MCP-Agent",
        claim_id=claim_id,
        decision=decision,
        latency_seconds=time.time() - start_time,
        total_tokens=total_tokens,
        total_cost=total_cost,
        budget_termination=termination_reason,
        trajectory=trajectory,
    )
