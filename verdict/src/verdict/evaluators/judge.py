"""Pointwise LLM-as-judge evaluator (rubric-based scoring)."""

from __future__ import annotations

import json
import re

from verdict.core.models import Case, Score
from verdict.evaluators.base import Evaluator
from verdict.providers.base import Provider

_JUDGE_SYSTEM = (
    "You are a careful evaluator. Score the candidate answer on the given rubric. "
    'Respond ONLY with compact JSON: {"score": <int>, "rationale": "<short reason>"}.'
)

_JUDGE_TEMPLATE = """Task: {task}

Rubric (score 1-{scale}, higher is better):
{rubric}

{reference_block}Candidate answer:
{output}

Return JSON only."""


class JudgeEvaluator(Evaluator):
    """Scores an output 1..scale with an LLM judge, normalised to 0..1.

    Note: with a real judge model, prefer auditing the judge first
    (see ``verdict.judge.audit``) -- judges have position and length biases.
    """

    def __init__(
        self,
        judge: Provider,
        rubric: str,
        scale: int = 5,
        threshold: int = 3,
        name: str = "judge",
    ) -> None:
        self.judge = judge
        self.rubric = rubric
        self.scale = scale
        self.threshold = threshold
        self.name = name

    def _parse_score(self, text: str) -> int | None:
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "score" in data:
                return int(data["score"])
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        m = re.search(r"\b([1-9][0-9]?)\b", text)
        return int(m.group(1)) if m else None

    def evaluate(self, case: Case, output: str) -> Score:
        reference_block = ""
        if case.reference:
            reference_block = f"Reference answer:\n{case.reference}\n\n"
        prompt = _JUDGE_TEMPLATE.format(
            task=case.input,
            scale=self.scale,
            rubric=self.rubric,
            reference_block=reference_block,
            output=output,
        )
        completion = self.judge.complete(prompt, system=_JUDGE_SYSTEM, temperature=0.0)
        raw = self._parse_score(completion.text)
        if raw is None:
            return Score(
                name=self.name, value=0.0, passed=False, rationale="could not parse judge score"
            )
        raw = max(1, min(self.scale, raw))
        value = (raw - 1) / (self.scale - 1) if self.scale > 1 else float(raw)
        return Score(
            name=self.name,
            value=round(value, 4),
            passed=raw >= self.threshold,
            rationale=f"judge score {raw}/{self.scale}",
            details={"raw_score": raw, "judge_output": completion.text},
        )
