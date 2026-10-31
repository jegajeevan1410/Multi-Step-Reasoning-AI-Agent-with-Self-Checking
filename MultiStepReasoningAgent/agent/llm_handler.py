import json
import os
import re

import requests


class LLMHandler:
    """Talks to a local Ollama server and loads the prompt files."""

    def __init__(self, model=None, url=None):
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3")
        self.url = url or os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.prompt_dir = os.path.join(os.path.dirname(__file__), "prompts")
        self.prompts = {
            "planner": self._load_prompt("planner_prompt.txt"),
            "executor": self._load_prompt("executor_prompt.txt"),
            "verifier": self._load_prompt("verifier_prompt.txt"),
        }

    def _load_prompt(self, filename):
        path = os.path.join(self.prompt_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _call_llm(self, prompt: str) -> str:
        response = requests.post(
            self.url,
            json={"model": self.model, "prompt": prompt, "stream": False,
                  "options": {"temperature": 0}},
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["response"]

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Pull the first {...} block out of the model's reply."""
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON found in LLM reply: {text[:200]}")
        return json.loads(match.group(0))

    # ---------- Planner ----------
    def generate_plan(self, question: str) -> list:
        prompt = f"{self.prompts['planner']}\nQuestion: {question}\n"
        text = self._call_llm(prompt)
        steps = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("-"):
                steps.append(line.lstrip("- ").strip())
        return steps

    # ---------- Executor ----------
    def execute_plan(self, question: str, plan: list, feedback: str = "") -> dict:
        plan_text = "\n".join(f"- {step}" for step in plan) or "- Solve step by step"
        prompt = f"{self.prompts['executor']}\nQuestion: {question}\nPlan:\n{plan_text}\n"
        if feedback:
            prompt += (f"\nA previous attempt was wrong. Verifier feedback: {feedback}\n"
                       "Fix the mistake and solve again.\n")
        prompt += "Output:\n"
        return self._extract_json(self._call_llm(prompt))

    # ---------- Verifier ----------
    def verify_solution(self, question: str, intermediate: str, final_answer: str) -> dict:
        prompt = (f"{self.prompts['verifier']}\nQuestion: {question}\n"
                  f"Intermediate: {intermediate}\nFinal answer: {final_answer}\nOutput:\n")
        return self._extract_json(self._call_llm(prompt))
