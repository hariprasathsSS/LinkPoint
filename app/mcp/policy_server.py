"""
app/mcp/policy_server.py
========================
Server 1 — YOUR OWN MCP server.

Wraps the existing retrieval pipeline (search_policy) as a discoverable
MCP tool. Any external agent that connects to this server can call
search_policy without knowing how the RAG pipeline works internally.

Run standalone:
    python -m app.mcp.policy_server

Transport: stdio (spawned as a subprocess by the MCP host/agent)
"""

import asyncio
import sys
import os

# Ensure project root is on the path when run as __main__
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fastmcp import FastMCP

mcp = FastMCP("policy-server")


@mcp.tool()
async def search_policy(query: str) -> str:
    """
    Search the insurance policy documents for coverage rules, exclusions, limits,
    and endorsement conditions.

    WHEN TO CALL:
        Call this tool whenever you need to determine whether a specific peril,
        condition, or event is covered under the homeowner's policy. Use it to
        look up exclusion codes (e.g. E-17), HO endorsements (e.g. HO-2306),
        or coverage limits before making an approval or denial decision.

    DO NOT call this tool to look up claim details — use get_claim for that.

    PARAMETER:
        query (str): A plain-English question about what is or is not covered.
                     Example: "Is flood damage from surface water covered?"
                     Example: "What does exclusion E-17 say?"

    RETURNS:
        A plain-English answer drawn from the policy documents, with relevant
        clauses quoted where available. If the topic is not in the policy corpus,
        the response will say so explicitly — do not infer coverage from silence.
    """
    try:
        from app.dependencies import get_query_service
        from app.model.query_model import QueryRequest

        query_service = get_query_service()
        req = QueryRequest(query=query, top_k=3)
        res = await query_service.ask(req)
        return res["answer"]
    except Exception as e:
        return (
            f"Policy search encountered an error: {str(e)}. "
            f"The RAG pipeline may be unavailable. "
            f"Do not assume coverage — state that you could not verify policy status and ask the user to retry."
        )


if __name__ == "__main__":
    mcp.run(transport="stdio")
