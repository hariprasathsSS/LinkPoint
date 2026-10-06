"""Baseline arm: ONE agent, ALL tools, one growing context."""
from app.agents.common import ANSWER_RULES, tool_loop
from app.agents.telemetry import start_trace

SYSTEM = (
    "You are AKIRA, a senior insurance claims assistant. "
    "Use your tools to answer the user's question; never guess. " + ANSWER_RULES
)


async def run_single(question: str, case_id: str = "adhoc") -> dict:
    with start_trace("single", case_id) as t:
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
        try:
            answer = await tool_loop("user", "single_agent", messages,
                                     ["search_policy", "get_claim", "get_adjuster_notes"])
        except Exception as e:  # noqa: BLE001
            answer = f"ERROR: {e}"
        return {"mode": "single", "answer": answer, "latency": t.latency,
                "total_tokens": t.total_tokens, "cost": t.cost, "hops": t.hops}
