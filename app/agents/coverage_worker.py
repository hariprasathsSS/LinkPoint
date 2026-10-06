"""Exclusions/coverage specialist: narrow prompt, ONE tool (search_policy)."""
from app.agents.common import ANSWER_RULES, tool_loop


class WorkerError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(f"{status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


SYSTEM = (
    "You are the COVERAGE & EXCLUSIONS specialist. Use search_policy to determine whether the "
    "described loss is covered and which exclusions/endorsement conditions apply. "
    "Do not discuss anything else. " + ANSWER_RULES
)


async def run_coverage_worker(task: str, inject_failure: bool = False) -> str:
    if inject_failure:
        raise WorkerError(500, "Internal Server Error (injected)")
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}]
    return await tool_loop("manager", "coverage_worker", messages, ["search_policy"], max_iters=4)
