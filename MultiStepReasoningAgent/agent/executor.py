from agent.llm_handler import LLMHandler
from agent.solvers import solve_with_python

llm = LLMHandler()


def executor(question: str, plan: list = None, feedback: str = "", use_llm: bool = False):
    """
    Solve the question.

    1. Try the exact Python solvers first (arithmetic, word problems,
       sequences, time differences, scheduling).
    2. If none of them fit, or a retry asks for it, ask the LLM using
       executor_prompt.txt.

    Returns: {"type", "final_answer", "raw_value", "intermediate", "data", "source"}
    """
    if not use_llm:
        result = solve_with_python(question)
        if result is not None:
            result["source"] = "python"
            return result

    try:
        reply = llm.execute_plan(question, plan or [], feedback)
        return {
            "type": "llm",
            "final_answer": str(reply.get("final_answer", "")).strip(),
            "raw_value": None,
            "intermediate": str(reply.get("intermediate", "")).strip(),
            "data": {},
            "source": "llm",
        }
    except Exception as e:
        return {
            "type": "unsupported",
            "final_answer": "Unable to solve this question",
            "raw_value": None,
            "intermediate": f"No built-in solver matched and the LLM call failed: {e}",
            "data": {},
            "source": "none",
        }
