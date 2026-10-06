"""
app/mcp/tool_counter.py
=======================
Utility that connects to each server in mcp_config.json and reports
tool counts + names from tools/list. Used to generate the
"N before → M after" deliverable.

Run:
    python -m app.mcp.tool_counter --config mcp_config_v1.json   # before
    python -m app.mcp.tool_counter --config mcp_config.json      # after
"""

import argparse
import asyncio
import json
import sys
from contextlib import AsyncExitStack
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def count_tools(config_path: str):
    config_file = Path(__file__).parent / config_path
    with open(config_file) as f:
        cfg = json.load(f)

    servers = cfg["servers"]
    all_tools = []

    async with AsyncExitStack() as stack:
        for srv in servers:
            params = StdioServerParameters(
                command=srv["command"],
                args=srv["args"],
                env=srv.get("env") or None,
            )
            read, write = await stack.enter_async_context(stdio_client(params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()

            tools_result = await session.list_tools()
            for t in tools_result.tools:
                all_tools.append({
                    "server": srv["name"],
                    "tool":   t.name,
                    "description_preview": (t.description or "")[:80],
                })

    print(f"\nConfig: {config_path}")
    print(f"Total tools discovered: {len(all_tools)}")
    print("-" * 50)
    for i, t in enumerate(all_tools, 1):
        print(f"  {i}. [{t['server']}] {t['tool']}")
        print(f"     → {t['description_preview']}...")
    print()
    return all_tools


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="mcp_config.json",
        help="Config filename inside app/mcp/",
    )
    args = parser.parse_args()
    asyncio.run(count_tools(args.config))


if __name__ == "__main__":
    main()
