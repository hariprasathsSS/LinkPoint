"""Adjuster-note specialist: narrow prompt, claim/notes tools only (no policy search)."""
from app.agents.common import tool_loop

SYSTEM = (
    "You are the CLAIMS & ADJUSTER-NOTES specialist. Given a claim ID, use get_claim and "
    "get_adjuster_notes to summarise the facts. If asked to find claims by attribute (like customer name), "
    "use search_claims. Do not decide coverage."
)


async def run_notes_worker(claim_id: str, focus: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Context/Focus: {focus}. Claim ID: {claim_id or 'None'}"},
    ]
    return await tool_loop("manager", "notes_worker", messages, ["get_claim", "get_adjuster_notes", "search_claims"], max_iters=4)
