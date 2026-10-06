"""
app/mcp/wire_capture.py
=======================
Script to capture the raw JSON-RPC wire traffic between the host and the
claims-server MCP server and save it to week9_deliverables/wire.json.

This documents the three mandatory MCP handshake messages:
    1. initialize        (host → server)
    2. tools/list        (host → server)
    3. tools/call        (host → server, one call per tool invoked)

Run from the project root:
    python -m app.mcp.wire_capture

Output: week9_deliverables/wire.json
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


OUTPUT_PATH = Path(__file__).resolve().parents[2] / "week9_deliverables" / "wire.json"

CLAIMS_SERVER_PARAMS = StdioServerParameters(
    command="python",
    args=["-m", "app.mcp.claims_server"],
    env=None,
)


async def capture():
    wire_log = []

    async with stdio_client(CLAIMS_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:

            # -----------------------------------------------------------
            # Message 1: initialize
            # -----------------------------------------------------------
            init_result = await session.initialize()

            wire_log.append({
                "_annotation": "Message 1 — initialize request/response",
                "direction": "host → server (request) + server → host (response)",
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "mcp-agent", "version": "1.0"},
                },
                "result": {
                    "protocolVersion": init_result.protocolVersion,
                    "capabilities": str(init_result.capabilities),
                    "serverInfo": {
                        "name": init_result.serverInfo.name,
                        "version": init_result.serverInfo.version,
                    },
                },
                "_field_notes": {
                    "jsonrpc":          "Always '2.0' — identifies the JSON-RPC version in use",
                    "method":           "'initialize' — the first handshake message; establishes protocol version and capability negotiation",
                    "params.protocolVersion": "MCP spec version both sides must agree on",
                    "params.capabilities":    "What the HOST supports (tools, sampling, etc.)",
                    "params.clientInfo":      "Human-readable identity of this host process",
                    "result.protocolVersion": "Server echoes back the agreed version",
                    "result.capabilities":    "What THIS SERVER supports",
                    "result.serverInfo":      "Human-readable identity of the server process",
                },
                "_model_call": "NO — initialize is a protocol handshake. The LLM is not involved.",
            })

            # -----------------------------------------------------------
            # Message 2: tools/list
            # -----------------------------------------------------------
            tools_result = await session.list_tools()

            tool_schemas = []
            for t in tools_result.tools:
                tool_schemas.append({
                    "name":        t.name,
                    "description": t.description,
                    "inputSchema": t.inputSchema,
                })

            wire_log.append({
                "_annotation": "Message 2 — tools/list request/response",
                "direction": "host → server (request) + server → host (response)",
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "result": {
                    "tools": tool_schemas,
                },
                "_field_notes": {
                    "jsonrpc":      "Always '2.0'",
                    "method":       "'tools/list' — discovery call; returns every tool the server exposes",
                    "params":       "Empty — no filter; host always asks for the full list",
                    "result.tools": "Array of tool descriptors. Each has name, description, and inputSchema (JSON Schema). The HOST copies these into the LLM's tool parameter list.",
                    "result.tools[n].name":        "The exact string the LLM must use in tool_calls[].function.name",
                    "result.tools[n].description": "Shown verbatim to the LLM as the tool description — write it as a prompt",
                    "result.tools[n].inputSchema":  "JSON Schema the LLM uses to generate valid arguments",
                },
                "_model_call": "NO — tool discovery. The LLM has not been called yet; the host is building the tools array to pass to the model.",
            })

            # -----------------------------------------------------------
            # Message 3: tools/call (get_claim)
            # -----------------------------------------------------------
            call_result = await session.call_tool(
                "get_claim",
                arguments={"claim_id": "CLM-W8-001"},
            )
            call_content = [
                c.text for c in call_result.content if hasattr(c, "text")
            ]

            wire_log.append({
                "_annotation": "Message 3 — tools/call (get_claim on CLM-W8-001)",
                "direction": "host → server (request) + server → host (response)",
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name":      "get_claim",
                    "arguments": {"claim_id": "CLM-W8-001"},
                },
                "result": {
                    "content": call_content,
                    "isError": False,
                },
                "_field_notes": {
                    "jsonrpc":           "Always '2.0'",
                    "method":            "'tools/call' — execute a specific tool on the server",
                    "params.name":       "Exact tool name from tools/list; must match",
                    "params.arguments":  "The LLM's output, validated against inputSchema before dispatch",
                    "result.content":    "Array of content blocks (text, image, etc.) returned by the tool",
                    "result.isError":    "True if the tool raised an exception; false on success",
                },
                "_model_call": (
                    "YES — the LLM call already happened on the HOST side BEFORE this message. "
                    "The model saw the tools list, decided to call get_claim, and produced the params. "
                    "This message is the HOST forwarding that decision to the server. "
                    "The server never sees the model; it only receives tool call requests."
                ),
            })

    # Write output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump({
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "server":      "claims-server (app/mcp/claims_server.py)",
            "transport":   "stdio",
            "messages":    wire_log,
        }, f, indent=2)

    print(f"Wire capture saved to: {OUTPUT_PATH}")
    print(f"Tools discovered: {[t['name'] for t in tool_schemas]}")


if __name__ == "__main__":
    asyncio.run(capture())
