# Multi-Step Reasoning AI Agent with Self-Checking

An agent that solves math, logic and scheduling problems in three stages: **Plan → Execute → Verify**. If the verifier rejects an answer, the agent retries with the verifier's feedback (up to `max_retries`).

For each question it returns:
- **answer**: the final result
- **reasoning_visible_to_user**: the working, in short
- **status** and **metadata**: problem type, plan, checks, retries and every attempt (for debugging)

**Supported problem types:** arithmetic (with correct order of operations), word problems ("twice", "three times as many", "4 more than"), number sequences, time differences (including past midnight), and meeting-slot scheduling. Other questions are passed to the LLM.

---

## 1. How to Run

**Requirements:** Python 3.10+. [Ollama](https://ollama.com/) with LLaMA 3 is optional. The supported problem types work without it.

```bash
# 1. Clone the repo
git clone https://github.com/jegajeevan1410/Multi-Step-Reasoning-AI-Agent-with-Self-Checking.git
cd Multi-Step-Reasoning-AI-Agent-with-Self-Checking/MultiStepReasoningAgent

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Start the local LLM in a separate terminal
ollama run llama3

# 4. Run the web app
python -m streamlit run app.py

# 5. Run the tests (21 questions with expected answers)
python tests/test_cases.py
```

The app opens at `http://localhost:8501`. Type a question and click **Solve**.

To use a different model or server, set `OLLAMA_MODEL` or `OLLAMA_URL`.

---

## 2. Where Prompts Live

All prompts are plain text files in **`MultiStepReasoningAgent/agent/prompts/`**:

| File | Used by | Purpose |
|------|---------|---------|
| `planner_prompt.txt` | `agent/planner.py` | Names the problem type and breaks it into small steps |
| `executor_prompt.txt` | `agent/executor.py` | Solves step by step and returns JSON (`intermediate`, `final_answer`) |
| `verifier_prompt.txt` | `agent/verifier.py` | Re-solves from scratch and returns JSON (`passed`, `issues`, `correct_answer`) |

Other files:
- `agent/solvers.py`: exact Python solvers for each supported problem type
- `agent/agent_loop.py`: the Plan → Execute → Verify loop with retries
- `agent/llm_handler.py`: calls Ollama and reads the JSON replies

---

## 3. Assumptions

- Questions are in English. Times use 24-hour `HH:MM` format.
- Slot ranges are written like `09:00–09:30` or `09:00-09:30`.
- A meeting fits a slot if the slot is **equal to or longer than** the meeting.
- If the arrival time is earlier than the departure time, the trip crosses midnight.
- Arithmetic results can be negative, but counts in word problems cannot.
- Ollama, if used, runs at `http://localhost:11434`. Without it, the planner uses a built-in plan, and questions outside the supported types return "failed" instead of a guess.

---

## 4. Prompt Documentation

### How the design works
- **Python does the exact maths, and the LLM handles everything else.** LLaMA 3 sometimes makes arithmetic slips, so supported problem types are solved with exact Python code. Anything else goes to the LLM through `executor_prompt.txt`.
- **The verifier checks the answer a different way.** It doesn't just re-read the executor's work:
  - Arithmetic is recalculated.
  - For durations, it checks that start + duration lands on the end time.
  - For scheduling, it checks that every listed slot is long enough and that no fitting slot was missed.
  - For LLM answers, the verifier prompt solves the question again from scratch and compares.
- **Retries use the verifier's feedback.** The verifier's `issues` are passed back into the executor prompt so the next attempt can fix the mistake.
- **Prompts are short and give an example for every type.** Each prompt has one job, a fixed JSON output format, and a worked example for each problem type, including one where the verifier catches a wrong answer.

### What didn't work well
- **Keyword rules in the executor.** The first version added up every number if it saw a `+`, so `45 - 18 + 6` gave 69. Similarly, `12 * 4 / 3` gave 144. A proper expression parser fixed this.
- **A verifier that only checked "is it a positive number?"** It passed wrong answers like 69, and it rejected correct negative results.
- **Matching on exact words.** Time questions only worked if they said "arrives" or "leaves". Now any question with two times is handled.
- **Prompt files that weren't used.** The executor and verifier prompts existed, but the code never sent them to the LLM.

### What I'd improve with more time
- Solve "reverse" word problems (e.g. "Tom has 4 more than Sam. Tom has 7. How many does Sam have?").
- Support percentages, units, letter sequences, odd-one-out and direction problems in Python.
- Run each LLM answer several times and keep the most common answer (self-consistency).
- Add proper unit tests with `pytest`.

---

## 5. Example Run Logs

Full logs with checks are in [`MultiStepReasoningAgent/example_run_logs.txt`](MultiStepReasoningAgent/example_run_logs.txt). All of them come from real runs.

| # | Question | Answer | Status | Retries |
|---|----------|--------|--------|---------|
| 1 | `45 - 18 + 6` | 33 | success | 0 |
| 2 | `12 * 4 / 3` | 16 | success | 0 |
| 3 | Ravi has 5 pencils and three times as many pens. How many items in total? | 20 items | success | 0 |
| 4 | Alice has 3 red apples and twice as many green apples. How many in total? | 9 apples | success | 0 |
| 5 | `2, 4, 8, 16, _` | 32 | success | 0 |
| 6 | Train leaves 14:30, arrives 18:05. How long? | 3 hours 35 minutes | success | 0 |
| 7 | Train leaves 23:50, arrives 00:20. How long? | 30 minutes | success | 0 |
| 8 | A call needs 45 minutes. Slots: 10:00–10:30, 13:15–14:00, 15:00–16:30. Which fit? | 13:15–14:00 and 15:00–16:30 | success | 0 |

---

## Author

**V. Jegajeevan**: [GitHub](https://github.com/jegajeevan1410) · [LinkedIn](https://www.linkedin.com/in/jegajeevan1410)
