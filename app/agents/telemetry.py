"""Telemetry for the single-vs-multi agent race.

Every LLM call is recorded as one "hop" (caller -> callee) with its prompt and
completion tokens. Prompt tokens of a hop are what that hop re-sent as context.
A contextvar carries the active Trace so that nested calls (e.g. the RAG
LLMService.generate() inside the search_policy tool) are attributed correctly.
"""
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Optional

# Same price constants as app/agent/react_agent.py so both arms are costed identically.
PRICE_PER_1K_IN = 0.0005
PRICE_PER_1K_OUT = 0.0015

_trace: ContextVar[Optional["Trace"]] = ContextVar("trace", default=None)
_label: ContextVar[tuple] = ContextVar("label", default=("untracked", "llm"))


class Trace:
    def __init__(self, arm: str, case_id: str):
        self.arm = arm
        self.case_id = case_id
        self.hops: list[dict] = []
        self._start = time.time()

    def add(self, frm: str, to: str, prompt_tokens: int, completion_tokens: int):
        self.hops.append({
            "seq": len(self.hops) + 1,
            "arm": self.arm,
            "case_id": self.case_id,
            "from": frm,
            "to": to,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        })

    @property
    def total_tokens(self) -> int:
        return sum(h["total_tokens"] for h in self.hops)

    @property
    def cost(self) -> float:
        return sum(
            h["prompt_tokens"] / 1000 * PRICE_PER_1K_IN
            + h["completion_tokens"] / 1000 * PRICE_PER_1K_OUT
            for h in self.hops
        )

    @property
    def latency(self) -> float:
        return time.time() - self._start


@contextmanager
def start_trace(arm: str, case_id: str):
    t = Trace(arm, case_id)
    token = _trace.set(t)
    try:
        yield t
    finally:
        _trace.reset(token)


@contextmanager
def hop_label(frm: str, to: str):
    """Label LLM calls made inside this block (used for nested calls like RAG generate)."""
    token = _label.set((frm, to))
    try:
        yield
    finally:
        _label.reset(token)


def record_usage(usage, frm: Optional[str] = None, to: Optional[str] = None):
    """Record a Groq `usage` object on the active trace. No-op when no trace is active."""
    t = _trace.get()
    if t is None or usage is None:
        return
    lf, lt = _label.get()
    t.add(frm or lf, to or lt, usage.prompt_tokens, usage.completion_tokens)
