"""
app/mcp/claims_server.py
========================
Server 2 — CLAIMS-SYSTEM MCP server.

Exposes two tools from the claims platform:
  - get_claim          → base claim facts (status, amount, excess, description)
  - get_adjuster_notes → field adjuster's inspection notes

This server is added to the agent purely via config (mcp_config.json).
Zero lines of agent code change when this server is bolted on.

Run standalone:
    python -m app.mcp.claims_server

Transport: stdio (spawned as a subprocess by the MCP host/agent)

IMPORTANT — MCP ARCHITECTURE NOTE:
    This server contains NO LLM calls. It is a data-access layer only.
    The model runs on the HOST side (mcp_agent.py). This server just
    exposes capabilities; it has no idea which AI is calling it.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fastmcp import FastMCP

mcp = FastMCP("claims-server")

# Path to the claims data file (same source the existing agent uses)
CLAIMS_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "eval", "claims_w8.json"
)

# Valid claim-ID pattern: CLM-W8-NNN  (or CLM-YYYY-NNN for future formats)
_CLAIM_ID_RE = re.compile(r"^CLM-[A-Z0-9]+-\d{3,}$")


def _load_claims() -> dict:
    """Load claims JSON and index by claim_id."""
    if not os.path.exists(CLAIMS_FILE):
        raise FileNotFoundError(f"Claims data file not found at: {CLAIMS_FILE}")
    with open(CLAIMS_FILE, "r") as f:
        data = json.load(f)
    return {c["claim_id"]: c for c in data}


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

    RETURNS:
        A structured text block with Claim ID, Status, Claim Amount, Excess,
        and Initial Description.

    ERROR PATHS:
        - Unknown ID   → message tells you the expected format so you can self-correct.
        - Bad format   → message tells you the expected pattern.
        - System error → message says the data layer is down; do not fabricate claim data.
    """
    # Guard: format check before hitting the data layer
    if not _CLAIM_ID_RE.match(claim_id):
        return (
            f"'{claim_id}' does not match the expected claim-ID format. "
            f"Claim IDs look like CLM-W8-001 (prefix CLM-W8-, then a 3-digit number). "
            f"Please confirm the exact claim ID with the user and call this tool again."
        )

    try:
        claims = _load_claims()
    except FileNotFoundError as e:
        return (
            f"Claims data store is unreachable ({e}). "
            f"Do not fabricate claim information — tell the user the system is temporarily unavailable."
        )
    except Exception as e:
        return (
            f"Unexpected error loading claims data: {str(e)}. "
            f"Do not proceed with claim triage until this is resolved."
        )

    if claim_id not in claims:
        all_ids = sorted(claims.keys())
        return (
            f"Claim '{claim_id}' was not found in the system. "
            f"Valid claim IDs currently on file: {', '.join(all_ids)}. "
            f"Please verify the claim number — a typo or wrong week prefix is the most common cause."
        )

    c = claims[claim_id]
    return (
        f"Claim ID: {c['claim_id']}\n"
        f"Status: {c['status']}\n"
        f"Claim Amount: ${c['claim_amount']}\n"
        f"Excess (Deductible): ${c['excess']}\n"
        f"Initial Description: {c['initial_description']}"
    )


@mcp.tool()
def get_adjuster_notes(claim_id: str, status: str) -> str:
    """
    Fetch the field adjuster's inspection notes for a claim.

    WHEN TO CALL:
        Call this AFTER get_claim, once you know the claim status.
        You must pass the status exactly as returned by get_claim
        (one of: OPEN, UNDER_INVESTIGATION, CLOSED).

    PARAMETERS:
        claim_id (str): The claim ID, same format as get_claim.
        status   (str): The current status — must match the actual claim status.
                        Allowed values: "OPEN", "UNDER_INVESTIGATION", "CLOSED".

    RETURNS:
        The adjuster's field notes describing the actual cause of damage,
        hidden conditions (e.g. slow leaks, vacancy), or coverage determinations.

    ERROR PATHS:
        - Status mismatch   → message tells you the actual status so you can self-correct.
        - Unknown claim ID  → message tells you valid IDs.
        - Bad status string → message lists the three valid values.
    """
    VALID_STATUSES = {"OPEN", "UNDER_INVESTIGATION", "CLOSED"}

    # Guard: validate status enum before data lookup
    status_upper = status.upper() if status else ""
    if status_upper not in VALID_STATUSES:
        return (
            f"'{status}' is not a valid status value. "
            f"Allowed values are: OPEN, UNDER_INVESTIGATION, CLOSED. "
            f"Use exactly the status string returned by get_claim."
        )

    try:
        claims = _load_claims()
    except Exception as e:
        return (
            f"Claims data store is unreachable: {str(e)}. "
            f"Do not fabricate adjuster notes — inform the user and wait."
        )

    if claim_id not in claims:
        return (
            f"Claim '{claim_id}' not found. "
            f"Call get_claim first to verify the claim exists before requesting adjuster notes."
        )

    c = claims[claim_id]
    actual_status = c["status"]

    if actual_status != status_upper:
        return (
            f"Status mismatch for claim {claim_id}: "
            f"you passed '{status_upper}' but the actual status is '{actual_status}'. "
            f"Call this tool again with status='{actual_status}'."
        )

    return f"Adjuster Notes for {claim_id}: {c['adjuster_notes']}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
