import json
import os
from typing import Dict, Any

from app.schema.agent_schema import ClaimStatus
from app.dependencies import get_query_service

CLAIMS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "eval", "claims_data.json")

def _load_claims() -> Dict[str, Any]:
    if not os.path.exists(CLAIMS_FILE):
        raise FileNotFoundError(f"Claims file not found: {CLAIMS_FILE}")
    with open(CLAIMS_FILE, "r") as f:
        data = json.load(f)
    return {c["claim_id"]: c for c in data}


def get_claim(claim_id: str) -> str:
    """
    Fetches the base details of a claim, including the initial description of what happened,
    the claim amount, and the excess (deductible).
    Use this tool FIRST when triaging a claim to understand the basic facts.
    """
    try:
        claims = _load_claims()
        if claim_id not in claims:
            return f"Error: Claim {claim_id} not found."
        
        c = claims[claim_id]
        return (
            f"Claim ID: {c['claim_id']}\n"
            f"Status: {c['status']}\n"
            f"Claim Amount: ${c['claim_amount']}\n"
            f"Excess (Deductible): ${c['excess']}\n"
            f"Initial Description: {c['initial_description']}"
        )
    except Exception as e:
        return f"Error loading claim: {str(e)}"


def get_adjuster_notes(claim_id: str, status: ClaimStatus) -> str:
    """
    Fetches the field adjuster's inspection notes for a claim. 
    Use this tool to find out the ACTUAL cause of damage or any hidden details 
    (like vacancy or true duration of a leak) that the customer didn't mention.
    Requires the current ClaimStatus as an enum.
    """
    try:
        claims = _load_claims()
        if claim_id not in claims:
            return f"Error: Claim {claim_id} not found."
        
        c = claims[claim_id]
        if c['status'] != status.value:
            return f"Error: Provided status '{status.value}' does not match actual status '{c['status']}'."

        return f"Adjuster Notes for {claim_id}: {c['adjuster_notes']}"
    except Exception as e:
        return f"Error loading adjuster notes: {str(e)}"


async def search_policy(query: str) -> str:
    """
    Searches the insurance policy documents to determine if a specific peril or condition is covered.
    Use this tool to look up rules, limits, and exclusions (like E-17 or HO-2306).
    """
    try:
        from app.model.query_model import QueryRequest
        query_service = get_query_service()
        req = QueryRequest(query=query, top_k=3)
        res = await query_service.ask(req)
        return res["answer"]
    except Exception as e:
        return f"Error searching policy: {str(e)}"

def search_claims(attribute: str, value: str) -> str:
    """
    Search for claims by a specific attribute (e.g., 'status', 'customer_name', 'peril', 'date_of_loss').
    Returns a list of matching claim IDs and brief summaries.
    """
    try:
        claims = _load_claims()
        matches = []
        for cid, c in claims.items():
            if str(c.get(attribute, "")).lower() == value.lower():
                matches.append(
                    f"Claim ID: {cid} | Customer: {c.get('customer_name', 'N/A')} | "
                    f"Status: {c['status']} | Amount: ${c['claim_amount']} | Peril: {c.get('peril', 'N/A')}"
                )
        
        if not matches:
            return f"No claims found where {attribute} = {value}."
        return f"Found {len(matches)} matching claims:\n" + "\n".join(matches)
    except Exception as e:
        return f"Error searching claims: {str(e)}"
