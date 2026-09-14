# Project Master Notes: Weeks 5 to 7 (Enhanced Study Guide)

This document is your complete, detailed study guide and reference manual for everything we have built from Week 5 through Week 7. It breaks down the story of your project step-by-step, the context behind every decision, the exact flow of execution, and the knowledge you gained.

---

## 📅 Week 5: Traces & Error Taxonomy
**Theme: "Stop guessing, start measuring."**

### The Context & Problem
Before Week 5, if someone asked "How good is your AI?", the only answer was a gut feeling or anecdotal evidence. As engineers, we cannot fix a system until we can mathematically measure it and scientifically name its failures. We needed to pull real data from how the system behaves in production.

### The Flow & What We Built
1. **Trace Logging Integration:** We updated the core `RetrievalService`. Every time a user asked a question, we logged exactly what the user asked, the exact text chunks the Vector DB retrieved, and the AI's final answer. This creates a "Trace" (a receipt of the AI's thought process).
2. **The 20 Trace Review:** You manually read 20 of these real production logs. This forced you to see exactly where the AI was getting confused in the real world.
3. **The Taxonomy (`taxonomy.md`):** We grouped those observed failures into 3 specific "Failure Modes":
   - **Mode 1 (Deflection):** The AI got scared and said "I don't know," even when the correct information was sitting right there in the retrieved documents. (Cause: Overly strict system prompt).
   - **Mode 2 (Omission):** The AI gave an answer that was technically correct, but omitted critical threshold details (e.g., missed the rule that water damage isn't covered if the house is vacant for 60 days).
   - **Mode 3 (Hallucination):** The Vector DB retrieved the completely wrong chunks, but the AI confidently made up an answer anyway instead of refusing to answer.

### 💡 Knowledge Gained
- **Taxonomy is a prerequisite for Testing:** You can't write an automated test to catch a bug if you haven't defined the bug first. The taxonomy defined the exact bugs we needed to hunt.

---

## 📅 Week 6: Automated Evaluation (LLM-as-a-Judge)
**Theme: "Automate the grading to iterate faster."**

### The Context & Problem
Manually reading 20 traces (Week 5) took hours. If you update your system prompt to fix a bug, you cannot afford to manually read 1,000 new traces to see if it got better. We needed an automated grading system (an Evaluator) to test our AI in seconds.

### The Flow & What We Built
1. **The Blind Protocol (Ground Truth):** Before writing the judge, you hand-labeled 25 test cases as PASS/FAIL in `labels_25.json`. This established our "Ground Truth" baseline.
2. **The 5 Evaluation Modes:** We tracked 5 different outcomes in our evaluation script to precisely measure performance:
   - *Mode 1, 2, 3:* The Failure Modes defined in Week 5.
   - *Mode 4 (Out-of-Corpus Correct):* The AI correctly realized the answer was not in the documents and safely deflected.
   - *Mode 5 (In-Corpus Correct):* The AI successfully found the answer and answered perfectly.
3. **Tier 1 (Regex Assertions):** We built fast, free Python code to check structure before calling the AI. (e.g., "If the claim is denied, the answer MUST contain an E-XX exclusion code").
4. **Tier 2 (LLM Judge):** For nuanced grading. We gave a second, smarter LLM (`judge_v2.txt`) the original Question, the AI's Answer, and your Ground Truth, and asked it: "Is this factually accurate and complete?"
5. **The Agreement Benchmark:** We tested how often our LLM Judge agreed with your human labels. By tweaking the prompt from V1 to V2, we improved the LLM Judge's agreement rate to 92%.

### 💡 Knowledge Gained
- **The Two-Tier System:** LLMs are expensive and slow. If you can catch a failure with a free Regex assertion (Tier 1), you save money and latency by skipping the LLM judge (Tier 2).
- **Prompt Iteration:** Our initial hypothesis was wrong. The judge wasn't too lenient; it was actually too strict until we gave it "scope-awareness" instructions in V2.

---

## 📅 Week 7: Agents vs. Workflows
**Theme: "Just because you *can* use an Agent, doesn't mean you *should*."**

### The Context & Problem
Now that we have a solid evaluation system, we moved on to building complex automations: an Insurance Claims Triage system. 
We wanted to compare two architectures:
- An **Agent** (dynamic, loops, makes its own decisions).
- A **Fixed Workflow** (rigid, blind, follows hard-coded steps).
Which one is actually better for our business?

### The Flow & What We Built
1. **The Tools (`tools.py`):** We built the "hands" of the system. 3 Python functions: `get_claim()`, `get_adjuster_notes()`, and `search_policy()`.
2. **The Dataset (`claims_10.json`):** We generated 10 fake claims, deliberately including "plot twists" (e.g., the initial claim says "water damage," but the notes reveal "house was vacant for 90 days").
3. **The ReAct Agent (`react_agent.py`):** We built an AI trapped in a `while True:` loop. It uses the ReAct pattern (Reasoning + Acting). It thinks about the problem, chooses a tool, reads the result, and loops until it has enough info to decide.
   - *Budgets:* We enforced 4 strict budgets (Wall-Clock Time, Max Loops, Max Tokens, Max Cost) so the Agent wouldn't spin infinitely and burn our money.
4. **The Fixed Workflow (`fixed_workflow.py`):** A rigid Python script that executes the tools sequentially: Get Claim -> Get Notes -> Check Policy -> Decide. No loops, no AI decision-making on *how* to route.
5. **The Race (`run_race.py`):** The script that ran all 10 claims through both systems simultaneously and printed a benchmark table.

### 💡 Knowledge Gained
- **The Core Decision Rule for Agents:** *"Does the path vary by input?"* If every input requires the exact same sequence of steps, do not use an Agent.
- **The Verdict:** The Fixed Workflow crushed the Agent. It was 2x faster, 4x cheaper, used far fewer tokens, and had a higher pass rate (100% vs 90%). Because the steps for checking an insurance claim never actually change (you always need the claim, the notes, and the policy), an Agent is a complete waste of money and time for this specific task. **We should ship the Fixed Workflow.**
