from agent.llm_handler import LLMHandler

llm = LLMHandler()

FALLBACK_PLANS = {
    "scheduling": ["Problem type: scheduling", "Extract the required duration",
                   "Compute the length of each slot", "Keep slots that are long enough"],
    "time_difference": ["Problem type: time difference", "Convert both times to minutes",
                        "Subtract start from end (add 24 h if negative)", "Convert to hours and minutes"],
    "sequence": ["Problem type: number sequence", "Check differences between numbers",
                 "Check ratios between numbers", "Apply the constant pattern"],
    "word_problem": ["Problem type: word problem", "Extract the starting amount",
                     "Apply 'times as many' / 'more than'", "Add up if a total is asked"],
    "arithmetic": ["Problem type: arithmetic", "Extract the expression",
                   "Apply order of operations", "Return the result"],
}


def planner(question: str, problem_type: str = None):
    """
    Ask the LLM for a step-by-step plan.
    If the LLM is not reachable, use a simple built-in plan for the problem type.
    """
    try:
        steps = llm.generate_plan(question)
        if steps:
            return steps
    except Exception as e:
        print(f"[Planner] LLM unavailable, using built-in plan: {e}")
    return FALLBACK_PLANS.get(problem_type, ["Read the question", "Solve step by step", "Check the answer"])
