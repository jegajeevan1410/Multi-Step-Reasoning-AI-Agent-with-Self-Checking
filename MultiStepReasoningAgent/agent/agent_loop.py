from agent.executor import executor
from agent.planner import planner
from agent.solvers import solve_with_python
from agent.verifier import verifier


class AgentLoop:
    def __init__(self, max_retries=2):
        self.max_retries = max_retries

    def solve(self, question: str):
        """
        Plan -> Execute -> Verify, retrying if the verifier rejects the answer.
        Returns a dict with answer, status, reasoning_visible_to_user and metadata.
        """
        quick = solve_with_python(question)
        plan = planner(question, quick["type"] if quick else None)

        attempts = []
        feedback = ""
        solution, verification = {}, {}

        for retry in range(self.max_retries + 1):
            # First try uses the Python solver if one fits; retries go to the LLM
            # with the verifier's feedback.
            solution = executor(question, plan, feedback=feedback, use_llm=retry > 0)
            verification = verifier(solution, question)

            attempts.append({
                "retry": retry,
                "source": solution["source"],
                "answer": solution["final_answer"],
                "passed": verification["passed"],
                "issues": verification.get("issues", ""),
            })
            print(f"[Retry {retry}] {solution['source']}: {solution['final_answer']} "
                  f"-> passed={verification['passed']}")

            if verification["passed"]:
                return {
                    "answer": solution["final_answer"],
                    "status": "success",
                    "reasoning_visible_to_user": solution["intermediate"],
                    "metadata": {
                        "problem_type": solution["type"],
                        "plan": plan,
                        "checks": verification["checks"],
                        "intermediate": solution["intermediate"],
                        "retries": retry,
                        "attempts": attempts,
                    },
                }

            feedback = verification.get("issues", "")
            # Nothing more to try if the LLM itself isn't reachable.
            if solution["source"] == "none":
                break

        return {
            "answer": "Failed to solve the problem",
            "status": "failed",
            "reasoning_visible_to_user": "The answer could not be verified. "
                                         + (verification.get("issues") or ""),
            "metadata": {
                "problem_type": solution.get("type"),
                "plan": plan,
                "checks": verification.get("checks", []),
                "intermediate": solution.get("intermediate", ""),
                "retries": len(attempts) - 1,
                "attempts": attempts,
            },
        }


def solve_question(question: str, max_retries: int = 2):
    """Shortcut used by the tests."""
    return AgentLoop(max_retries=max_retries).solve(question)


if __name__ == "__main__":
    agent = AgentLoop(max_retries=2)
    while True:
        q = input("Enter your question (or 'exit' to quit): ")
        if q.lower() == "exit":
            break
        print(agent.solve(q))
        print("=" * 60)
