import asyncio
import json
import httpx
import os
import csv
import statistics

API_BASE = "http://localhost:8000/claim"
CLAIMS_FILE = os.path.join(os.path.dirname(__file__), "claims_10.json")

async def run_race():
    print("Starting the Race: Agent vs Fixed Workflow")
    print("Make sure your FastAPI server is running on localhost:8000!")
    
    with open(CLAIMS_FILE, "r") as f:
        claims = json.load(f)
        
    results = []
    agent_latencies = []
    workflow_latencies = []
    
    agent_totals = {"tokens": 0, "cost": 0.0, "passes": 0}
    workflow_totals = {"tokens": 0, "cost": 0.0, "passes": 0}
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for c in claims:
            cid = c["claim_id"]
            print(f"\nProcessing {cid}...")
            
            # Call Agent
            print("  Running Agent...")
            res_a = await client.post(f"{API_BASE}/agent/{cid}")
            a_data = res_a.json() if res_a.status_code == 200 else {}
            
            # Call Workflow
            print("  Running Workflow...")
            res_w = await client.post(f"{API_BASE}/workflow/{cid}")
            w_data = res_w.json() if res_w.status_code == 200 else {}
            
            # Simple pass check (Did it return a string with APPROVED/DENIED?)
            # In a real eval we'd match ground truth, but here we just check if it completed successfully
            a_pass = 1 if "APPROVED" in a_data.get("decision", "") or "DENIED" in a_data.get("decision", "") else 0
            w_pass = 1 if "APPROVED" in w_data.get("decision", "") or "DENIED" in w_data.get("decision", "") else 0
            
            agent_totals["passes"] += a_pass
            workflow_totals["passes"] += w_pass
            agent_totals["tokens"] += a_data.get("total_tokens", 0)
            workflow_totals["tokens"] += w_data.get("total_tokens", 0)
            agent_totals["cost"] += a_data.get("total_cost", 0.0)
            workflow_totals["cost"] += w_data.get("total_cost", 0.0)
            
            if a_data.get("latency_seconds"):
                agent_latencies.append(a_data["latency_seconds"])
            if w_data.get("latency_seconds"):
                workflow_latencies.append(w_data["latency_seconds"])
                
            results.append({
                "claim_id": cid,
                "agent_decision": a_data.get("decision", "FAILED"),
                "agent_time": a_data.get("latency_seconds", 0),
                "agent_tokens": a_data.get("total_tokens", 0),
                "agent_cost": a_data.get("total_cost", 0),
                "agent_budget_term": a_data.get("budget_termination"),
                "workflow_decision": w_data.get("decision", "FAILED"),
                "workflow_time": w_data.get("latency_seconds", 0),
                "workflow_tokens": w_data.get("total_tokens", 0),
                "workflow_cost": w_data.get("total_cost", 0)
            })

    # Calculate metrics
    num_claims = len(claims)
    agent_p50 = statistics.median(agent_latencies) if agent_latencies else 0
    workflow_p50 = statistics.median(workflow_latencies) if workflow_latencies else 0
    
    # Save to CSV
    csv_file = os.path.join(os.path.dirname(__file__), "race.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
        
    # Print Table
    print("\n================ RACE RESULTS ================")
    print(f"{'Metric':<20} | {'Agent':<15} | {'Workflow':<15}")
    print("-" * 55)
    print(f"{'Pass Rate':<20} | {agent_totals['passes']}/{num_claims} ({agent_totals['passes']/num_claims*100:.0f}%) | {workflow_totals['passes']}/{num_claims} ({workflow_totals['passes']/num_claims*100:.0f}%)")
    print(f"{'p50 Latency (sec)':<20} | {agent_p50:.2f}s          | {workflow_p50:.2f}s")
    print(f"{'Total Tokens':<20} | {agent_totals['tokens']:<15} | {workflow_totals['tokens']:<15}")
    print(f"{'Cost per Claim':<20} | ${agent_totals['cost']/num_claims:.4f}        | ${workflow_totals['cost']/num_claims:.4f}")
    print("==============================================")
    print(f"\nDetailed results saved to {csv_file}")
    
    # Look for a budget termination log
    for r in results:
        if r["agent_budget_term"]:
            print(f"\n[!] Agent budget terminated on {r['claim_id']} due to {r['agent_budget_term']}")

if __name__ == "__main__":
    asyncio.run(run_race())
