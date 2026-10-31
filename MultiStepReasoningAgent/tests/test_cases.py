import os
import sys

# Let "python tests/test_cases.py" find the agent package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.agent_loop import solve_question  # noqa: E402

# (question, expected answer)
EASY_QUESTIONS = [
    ("8+7", "15"),
    ("10+20-5", "25"),
    ("5 * 6", "30"),
    ("100 - 45", "55"),
    ("What is the sum of 3 and 4?", "7"),
    ("If a train leaves at 14:30 and arrives at 18:05, how long is the journey?", "3 hours 35 minutes"),
    ("2, 4, 8, 16, _", "32"),
]

TRICKY_QUESTIONS = [
    ("45 - 18 + 6", "33"),
    ("12 * 4 / 3", "16"),
    ("10 + 20 - 33 * 2", "-36"),
    ("(2 + 3) * 4", "20"),
    ("Alice has 3 red apples and twice as many green apples. How many apples total?", "9 apples"),
    ("Ravi has 5 pencils and three times as many pens. How many items does he have in total?", "20 items"),
    ("Sam has 6 stickers and Mia has 4 more stickers than Sam. How many stickers in total?", "16 stickers"),
    ("3, 7, 11, 15, _", "19"),
    ("1, 4, 9, 16, _", "25"),
    ("Train leaves at 23:50 and arrives at 00:20. How long is the journey?", "30 minutes"),
    ("A bus departs at 09:15 and lands at 13:50. How long is the trip?", "4 hours 35 minutes"),
    ("A meeting needs 60 minutes. Free slots: 09:00–09:30, 09:45–10:30, 11:00–12:00.", "11:00–12:00"),
    ("A call needs 45 minutes. Free slots are: 10:00–10:30, 13:15–14:00, 15:00–16:30. Which slots can fit the call?",
     "13:15–14:00 and 15:00–16:30"),
    ("A meeting needs 1 hour. Free slots: 09:00-09:30, 10:00-10:45.", "No slots fit"),
]


def run(group_name, questions):
    print(f"\n=== {group_name} ===")
    passed = 0
    counted = 0
    for q, expected in questions:
        result = solve_question(q)
        ok = expected is None or result["answer"] == expected
        if expected is not None:
            counted += 1
            passed += ok
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {q}")
        print(f"       answer={result['answer']!r}  expected={expected!r}  "
              f"status={result['status']}  retries={result['metadata']['retries']}")
    return passed, counted


if __name__ == "__main__":
    p1, c1 = run("EASY TESTS", EASY_QUESTIONS)
    p2, c2 = run("TRICKY TESTS", TRICKY_QUESTIONS)
    print(f"\nTotal: {p1 + p2}/{c1 + c2} correct")
