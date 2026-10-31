"""
Exact Python solvers for the problem types the agent supports.

Each solver returns None if the question isn't its type, otherwise a dict:
    {"type", "final_answer", "raw_value", "intermediate", "data"}
`data` holds the extracted values so the verifier can re-check the answer.
"""
import ast
import operator
import re

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}

TIME_RE = r"(\d{1,2}):(\d{2})"
SLOT_RE = r"(\d{1,2}:\d{2})\s*(?:–|—|-|to)\s*(\d{1,2}:\d{2})"


def fmt(value):
    """Show 16.0 as 16, and round long decimals."""
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(round(value, 4))
    return str(value)


def to_minutes(hhmm: str) -> int:
    h, m = map(int, hhmm.split(":"))
    return h * 60 + m


def minutes_to_text(total: int) -> str:
    h, m = divmod(total, 60)
    parts = []
    if h:
        parts.append(f"{h} hour{'s' if h != 1 else ''}")
    if m or not h:
        parts.append(f"{m} minute{'s' if m != 1 else ''}")
    return " ".join(parts)


# ---------- Safe arithmetic (no eval) ----------
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def safe_eval(expr: str):
    """Evaluate + - * / and brackets with the correct order of operations."""
    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval(node.operand))
        raise ValueError("Unsupported expression")
    return _eval(ast.parse(expr, mode="eval"))


def solve_scheduling(question: str):
    q = question.lower()
    slots = re.findall(SLOT_RE, question)
    dur = re.search(r"(\d+(?:\.\d+)?)\s*(minutes?|mins?|hours?|hrs?)\b", q)
    if not slots or not dur:
        return None
    needed = float(dur.group(1)) * (60 if dur.group(2).startswith(("hour", "hr")) else 1)
    needed = int(needed)

    steps, fits = [], []
    for start, end in slots:
        length = to_minutes(end) - to_minutes(start)
        ok = length >= needed
        steps.append(f"{start}–{end} = {length} min ({'fits' if ok else 'too short'})")
        if ok:
            fits.append(f"{start}–{end}")
    answer = " and ".join(fits) if len(fits) <= 2 else ", ".join(fits[:-1]) + " and " + fits[-1]
    return {
        "type": "scheduling",
        "final_answer": answer or "No slots fit",
        "raw_value": len(fits),
        "intermediate": f"Needed = {needed} min; " + "; ".join(steps),
        "data": {"needed": needed, "slots": slots, "fits": fits},
    }


def solve_time_difference(question: str):
    if re.search(SLOT_RE, question):
        return None
    times = re.findall(TIME_RE, question)
    if len(times) != 2:
        return None
    start = int(times[0][0]) * 60 + int(times[0][1])
    end = int(times[1][0]) * 60 + int(times[1][1])
    diff = end - start
    note = ""
    if diff < 0:
        diff += 24 * 60
        note = " (+24 h, crosses midnight)"
    return {
        "type": "time_difference",
        "final_answer": minutes_to_text(diff),
        "raw_value": diff,
        "intermediate": f"Start = {start} min; End = {end} min; Duration = {end} - {start} = {diff} min{note}",
        "data": {"start": start, "end": end},
    }


def solve_sequence(question: str):
    m = re.search(r"(-?\d+(?:\s*,\s*-?\d+){2,})\s*,\s*(?:_+|\?)", question)
    if not m:
        return None
    nums = [int(x) for x in re.findall(r"-?\d+", m.group(1))]
    diffs = [b - a for a, b in zip(nums, nums[1:])]

    if len(set(diffs)) == 1:
        nxt = nums[-1] + diffs[0]
        how = f"Differences = {diffs} (constant); Next = {nums[-1]} + {diffs[0]} = {nxt}"
    elif 0 not in nums[:-1] and len({b / a for a, b in zip(nums, nums[1:])}) == 1:
        ratio = nums[1] / nums[0]
        nxt = nums[-1] * ratio
        how = f"Differences = {diffs} (not constant); Ratio = {fmt(ratio)} (constant); Next = {nums[-1]} x {fmt(ratio)} = {fmt(nxt)}"
    else:
        second = [b - a for a, b in zip(diffs, diffs[1:])]
        if len(second) >= 1 and len(set(second)) == 1:
            nxt = nums[-1] + diffs[-1] + second[0]
            how = f"Differences = {diffs}; they grow by {second[0]}; Next = {nums[-1]} + {diffs[-1] + second[0]} = {nxt}"
        else:
            return None
    return {
        "type": "sequence",
        "final_answer": fmt(nxt),
        "raw_value": nxt,
        "intermediate": how,
        "data": {"nums": nums},
    }


def _multiplier(text: str):
    text = text.lower()
    if "twice" in text or "double" in text:
        return 2
    if "half as many" in text:
        return 0.5
    if "thrice" in text:
        return 3
    m = re.search(r"(\d+|" + "|".join(NUMBER_WORDS) + r")\s+times\s+as\s+many", text)
    if m:
        word = m.group(1)
        return int(word) if word.isdigit() else NUMBER_WORDS[word]
    return None


def solve_word_problem(question: str):
    q = question.lower()
    mult = _multiplier(q)
    more = re.search(r"(\d+)\s+(more|fewer|less)\s+\w+\s+than", q)
    if mult is None and not more:
        return None

    base_match = re.search(r"\b(\d+|" + "|".join(NUMBER_WORDS) + r")\s+([a-z]+(?:\s[a-z]+)?)", q)
    if not base_match:
        return None
    word = base_match.group(1)
    base = int(word) if word.isdigit() else NUMBER_WORDS[word]

    if mult is not None:
        other = base * mult
        rule = f"{base} x {fmt(mult)} = {fmt(other)}"
    else:
        n = int(more.group(1))
        other = base + n if more.group(2) == "more" else base - n
        rule = f"{base} {'+' if more.group(2) == 'more' else '-'} {n} = {other}"

    wants_total = any(w in q for w in ["total", "altogether", "in all", "combined", "together"])
    unit_match = re.search(r"how many (\w+)", q)
    unit = unit_match.group(1) if unit_match else ""

    if wants_total:
        result = base + other
        steps = f"First amount = {base}; Second amount = {rule}; Total = {base} + {fmt(other)} = {fmt(result)}"
    else:
        result = other
        steps = f"First amount = {base}; Second amount = {rule}"

    answer = fmt(result) + (f" {unit}" if unit and unit not in ("do", "does", "is", "are") else "")
    return {
        "type": "word_problem",
        "final_answer": answer,
        "raw_value": result,
        "intermediate": steps,
        "data": {"base": base, "mult": mult, "more": more.groups() if more else None,
                 "total": wants_total},
    }


def solve_arithmetic(question: str):
    q = question.lower()

    # "sum of 3 and 4", "product of 6 and 7", "difference between 10 and 4"
    m = re.search(r"(sum|product|difference)\s+(?:of|between)\s+(-?\d+(?:\.\d+)?)\s+and\s+(-?\d+(?:\.\d+)?)", q)
    if m:
        op = {"sum": "+", "product": "*", "difference": "-"}[m.group(1)]
        expr = f"{m.group(2)} {op} {m.group(3)}"
    else:
        cleaned = q.replace("×", "*").replace("÷", "/")
        cleaned = re.sub(r"(?<=\d)\s*x\s*(?=\d)", " * ", cleaned)
        candidates = re.findall(r"[\d\.\s\+\-\*/\(\)]+", cleaned)
        candidates = [c.strip() for c in candidates if re.search(r"\d\s*[\+\-\*/]\s*[\(\d]", c)]
        if not candidates:
            return None
        expr = max(candidates, key=len)

    try:
        value = safe_eval(expr)
    except (ValueError, SyntaxError, ZeroDivisionError):
        return None
    return {
        "type": "arithmetic",
        "final_answer": fmt(value),
        "raw_value": value,
        "intermediate": f"{expr} = {fmt(value)} (order of operations: brackets, then * and /, then + and -)",
        "data": {"expr": expr},
    }


# Order matters: more specific types first.
SOLVERS = [solve_scheduling, solve_time_difference, solve_sequence,
           solve_word_problem, solve_arithmetic]


def solve_with_python(question: str):
    for solver in SOLVERS:
        result = solver(question)
        if result is not None:
            return result
    return None
