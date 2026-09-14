# Project Master Notes: Weeks 5 to 7

This document is your complete study guide and reference manual for everything we have built from Week 5 through Week 7. It breaks down the story of your project step-by-step.

---

## 📅 Week 5: Traces & Error Taxonomy
**Theme: "Stop guessing, start measuring."**

### Core Concept
Before Week 5, if someone asked "How good is your AI?", the only answer was a gut feeling. Week 5 was about capturing hard data from the real world (Production Traces) and manually analyzing where the AI failed. You cannot fix an AI until you can scientifically name its failures.

### What We Built
1. **Trace Logging:** We updated `RetrievalService` so every single question asked, the chunks retrieved, and the AI's final answer were saved (logged).
2. **The 20 Trace Review:** You manually read 20 real logs to see exactly what the AI was doing wrong.
3. **The Taxonomy (`taxonomy.md`):** We grouped those failures into 3 specific "Failure Modes":
   - **Mode 1:** The AI deflected (said "I don't know") even when the answer was in the document.
   - **Mode 2:** The AI gave a correct answer, but omitted critical threshold details (e.g., missed the 30-day/60-day rule).
   - **Mode 3:** The AI retrieved the wrong chunks and hallucinated.

### 💡 Points to Remember for Demo
- **Why do a taxonomy?** You can't write an automated test to catch a bug if you haven't defined the bug first. The taxonomy defined the bugs.

---

## 📅 Week 6: Automated Evaluation (LLM-as-a-Judge)
**Theme: "Automate the grading."**

### Core Concept
Manually reading 20 traces (Week 5) took hours. If you update your prompt, you can't afford to manually read 1,000 traces to see if it got better. We needed an automated grading system to test our AI in seconds.

### What We Built
1. **The Blind Protocol (`labels_25.json`):** You hand-labeled 25 test cases as PASS/FAIL *before* writing the automated judge, to ensure we had a "Ground Truth" baseline.
2. **Tier 1 (Regex Assertions):** Fast, free Python code that checks structure. (e.g., "If the claim is denied, the answer MUST contain an E-XX exclusion code").
3. **Tier 2 (LLM Judge):** For nuanced grading. We gave a second LLM (`judge_v2.txt`) the Question, the AI's Answer, and the Ground Truth, and asked it: "Is this factually accurate and complete?"
4. **The Agreement Benchmark:** We tested how often our LLM Judge agreed with your human labels. We iterated the prompt from V1 to V2 to improve agreement to 92%.

### 💡 Points to Remember for Demo
- **Why a Two-Tier system?** LLMs are expensive and slow. If you can catch a failure with a free Regex assertion (Tier 1), you save money by skipping the LLM judge (Tier 2).
- **The Prediction Outcome:** We honestly documented in `prediction.txt` that our initial hypothesis was wrong. The judge wasn't too lenient; it was actually too strict until we gave it scope-awareness instructions in V2.

---

## 📅 Week 7: Agents vs. Workflows
**Theme: "Just because you *can* use an Agent, doesn't mean you *should*."**

### Core Concept
Now that we can evaluate the AI, we wanted to build a complex automation: an Insurance Claims Triage system. 
An **Agent** decides its own path dynamically using a loop. A **Fixed Workflow** blindly follows hard-coded steps. We raced them to see which was better.

### What We Built
1. **The Tools (`tools.py`):** The "hands" of the AI. `get_claim`, `get_adjuster_notes`, `search_policy`.
2. **The Dataset (`claims_10.json`):** 10 fake claims, including "plot twists" (e.g., initial claim says "water damage," notes reveal "house was vacant for 90 days").
3. **The Agent (`react_agent.py`):** An AI trapped in a `while` loop that chooses tools until it finds the answer. We enforced 4 strict budgets (Time, Loops, Tokens, Cost) so it wouldn't spin infinitely.
4. **The Fixed Workflow (`fixed_workflow.py`):** A rigid script: Get Claim -> Get Notes -> Check Policy -> Decide. No loops.
5. **The Race (`run_race.py`):** The script that ran 10 claims through both systems simultaneously.

### 💡 Points to Remember for Demo
- **The Core Decision Rule:** "Does the path vary by input?" 
- **The Verdict:** The Fixed Workflow crushed the Agent. It was 2x faster, 4x cheaper, used fewer tokens, and had a higher pass rate. Because the steps for checking a claim never actually change (even for trick questions), an Agent is a complete waste of money and time. **We should ship the Fixed Workflow.**
