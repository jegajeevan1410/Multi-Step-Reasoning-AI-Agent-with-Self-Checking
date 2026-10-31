import re

from agent.llm_handler import LLMHandler
from agent.solvers import safe_eval, to_minutes

llm = LLMHandler()


def _number_in(text: str):
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group(0)) if m else None


def _check(name, passed, details):
    return {"check_name": name, "passed": passed, "details": details}


def _python_checks(sol: dict):
    """Re-check the answer independently, using a different calculation from the executor."""
    t, d, answer = sol["type"], sol["data"], sol["final_answer"]
    checks = []

    if t == "arithmetic":
        expected = safe_eval(d["expr"])
        got = _number_in(answer)
        checks.append(_check("recalculate", got is not None and abs(got - expected) < 1e-9,
                             f"Recalculated {d['expr']} = {expected}, answer = {got}"))

    elif t == "time_difference":
        got = sol["raw_value"]
        ok = (d["start"] + got) % 1440 == d["end"] % 1440 and 0 <= got < 1440
        checks.append(_check("start_plus_duration_equals_end", ok,
                             f"{d['start']} + {got} min should land on {d['end']} min"))

    elif t == "scheduling":
        should_fit = [f"{s}–{e}" for s, e in d["slots"]
                      if to_minutes(e) - to_minutes(s) >= d["needed"]]
        checks.append(_check("every_listed_slot_is_long_enough",
                             all(f in should_fit for f in d["fits"]),
                             f"Listed: {d['fits']}"))
        checks.append(_check("no_fitting_slot_missed", set(should_fit) == set(d["fits"]),
                             f"Slots that fit: {should_fit}"))

    elif t == "sequence":
        nums, nxt = d["nums"] + [sol["raw_value"]], sol["raw_value"]
        diffs = [b - a for a, b in zip(nums, nums[1:])]
        second = [b - a for a, b in zip(diffs, diffs[1:])]
        ratio_ok = 0 not in nums[:-1] and len({round(b / a, 9) for a, b in zip(nums, nums[1:])}) == 1
        ok = len(set(diffs)) == 1 or ratio_ok or len(set(second)) == 1
        checks.append(_check("pattern_continues", ok, f"Full sequence with answer: {nums}"))

    elif t == "word_problem":
        base, mult, more = d["base"], d["mult"], d["more"]
        if mult is not None:
            other = base * mult
        else:
            other = base + int(more[0]) if more[1] == "more" else base - int(more[0])
        expected = base + other if d["total"] else other
        got = _number_in(answer)
        checks.append(_check("recalculate", got is not None and abs(got - expected) < 1e-9,
                             f"Expected {expected}, answer = {got}"))
        checks.append(_check("not_negative", expected >= 0, "Counts can't be negative"))

    return checks


def verifier(solution: dict, question: str = ""):
    """
    Check the executor's answer.
    - Python answers: re-checked with an independent calculation.
    - LLM answers: checked by the LLM using verifier_prompt.txt.
    Returns: {"passed": bool, "checks": [...], "issues": str}
    """
    answer = solution.get("final_answer", "")
    if not answer or answer.lower().startswith(("unable", "cannot")):
        return {"passed": False, "issues": "No answer produced",
                "checks": [_check("has_answer", False, solution.get("intermediate", ""))]}

    if solution["source"] == "python":
        checks = _python_checks(solution)
        passed = all(c["passed"] for c in checks)
        issues = "; ".join(c["details"] for c in checks if not c["passed"])
        return {"passed": passed, "checks": checks, "issues": issues}

    try:
        reply = llm.verify_solution(question, solution.get("intermediate", ""), answer)
        passed = bool(reply.get("passed"))
        issues = str(reply.get("issues", ""))
        correct = str(reply.get("correct_answer", ""))
        return {"passed": passed, "issues": issues, "correct_answer": correct,
                "checks": [_check("llm_verifier", passed, issues or "Answer confirmed")]}
    except Exception as e:
        return {"passed": False, "issues": f"Verifier LLM call failed: {e}",
                "checks": [_check("llm_verifier", False, str(e))]}
