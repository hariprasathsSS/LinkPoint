# error_before_after.md
# Docstring rewrite + recoverable error — same failing call, before and after

---

## What changed

**Tool:** `get_claim` on the claims-system MCP server (`app/mcp/claims_server.py`)

Two changes were made:
1. **Docstring rewritten as a prompt** — tells the model *when* to call, *what format* the ID must be, and *what the error paths mean*
2. **Error response made recoverable** — instead of a bare "Error: not found", the model gets the valid ID list + a diagnosis

---

## BEFORE — Original `tools.py` docstring and error

```python
def get_claim(claim_id: str) -> str:
    """
    Fetches the base details of a claim, including the initial description of what happened,
    the claim amount, and the excess (deductible).
    Use this tool FIRST when triaging a claim to understand the basic facts.
    """
    try:
        claims = _load_claims()
        if claim_id not in claims:
            return f"Error: Claim {claim_id} not found."   # ← opaque error
        ...
    except Exception as e:
        return f"Error loading claim: {str(e)}"             # ← opaque error
```

### Transcript — BEFORE (agent given claim_id = "CLM-W8-999")

```
USER:   Please triage claim CLM-W8-999

[iter 1] LLM → tool_calls: get_claim(claim_id="CLM-W8-999")
HOST    → MCP server: tools/call get_claim {"claim_id": "CLM-W8-999"}
SERVER  → HOST: "Error: Claim CLM-W8-999 not found."

[iter 2] LLM sees: "Error: Claim CLM-W8-999 not found."
         LLM has no hint about valid IDs or format.
         LLM responds:
         "DENIED — I was unable to locate claim CLM-W8-999 in the system.
          The claim may have been closed or the ID is invalid. No payout calculated."

         ← WRONG: agent gave a coverage decision on a claim it never loaded.
            It cannot distinguish "typo" from "dead system" from "wrong week prefix".
```

**Problem:** The model cannot self-correct. It sees `"Error: Claim X not found"` and has no information about whether the system is down, the ID format is wrong, or the claim genuinely doesn't exist.

---

## AFTER — Rewritten docstring + recoverable error (app/mcp/claims_server.py)

```python
@mcp.tool()
def get_claim(claim_id: str) -> str:
    """
    Fetch the base facts of a claim: status, claim amount, excess (deductible),
    and the customer's initial description of the loss.

    WHEN TO CALL:
        Call this tool FIRST when triaging any claim. You need the claim amount
        and excess before you can calculate any payout.

    CLAIM ID FORMAT:
        IDs follow the pattern  CLM-W8-NNN  (e.g. CLM-W8-001, CLM-W8-012).
        If the user gave you a different format, ask them to confirm before calling.
        Do NOT guess or mutate the ID.

    ERROR PATHS:
        - Unknown ID   → message tells you the expected format so you can self-correct.
        - Bad format   → message tells you the expected pattern.
        - System error → message says the data layer is down; do not fabricate claim data.
    """
    if not _CLAIM_ID_RE.match(claim_id):
        return (
            f"'{claim_id}' does not match the expected claim-ID format. "
            f"Claim IDs look like CLM-W8-001 (prefix CLM-W8-, then a 3-digit number). "
            f"Please confirm the exact claim ID with the user and call this tool again."
        )
    ...
    if claim_id not in claims:
        all_ids = sorted(claims.keys())
        return (
            f"Claim '{claim_id}' was not found in the system. "
            f"Valid claim IDs currently on file: {', '.join(all_ids)}. "
            f"Please verify the claim number — a typo or wrong week prefix is the most common cause."
        )
```

### Transcript — AFTER (same call: claim_id = "CLM-W8-999")

```
USER:   Please triage claim CLM-W8-999

[iter 1] LLM → tool_calls: get_claim(claim_id="CLM-W8-999")
HOST    → MCP server: tools/call get_claim {"claim_id": "CLM-W8-999"}
SERVER  → HOST:
    "Claim 'CLM-W8-999' was not found in the system.
     Valid claim IDs currently on file: CLM-W8-001, CLM-W8-002, CLM-W8-003,
     CLM-W8-004, CLM-W8-005, CLM-W8-006, CLM-W8-007, CLM-W8-008,
     CLM-W8-009, CLM-W8-010, CLM-W8-011, CLM-W8-012.
     Please verify the claim number — a typo or wrong week prefix is the most common cause."

[iter 2] LLM sees the recoverable message with the valid ID list.
         LLM responds:
         "I could not find claim CLM-W8-999. The valid claims on file go up to
          CLM-W8-012. Could you confirm the correct claim ID? For example, did
          you mean CLM-W8-009?"

         ← CORRECT: agent surfaces the diagnosis, does not fabricate a decision,
            and gives the user enough information to self-correct.
```

**What moved:**
- Before: model gave a coverage decision with no claim data loaded.
- After: model correctly defers, names the available IDs, and asks for confirmation.
- The error is now **recoverable** — the model has everything it needs to retry or escalate.
