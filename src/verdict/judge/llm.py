"""LLM-backed pairwise judge with built-in bias mitigations.

Strategies (per Soumik 2026, "Judging the Judges", which compared mitigations):
  * "naive"  : minimal prompt (baseline, most bias-prone).
  * "cot"    : force step-by-step reasoning before the verdict. The single safest,
               most universally helpful strategy; reduces style bias the most.
  * "rubric" : score explicit criteria first, then decide. Reduces length/verbosity bias.

Extra mitigations:
  * normalize=True strips Markdown from both answers before judging -> neutralizes the
    dominant *style* bias.
"""

from __future__ import annotations

import json
import re

from verdict.judge.base import PairwiseJudge, Verdict
from verdict.judge.normalize import strip_formatting
from verdict.providers.base import Provider

Strategy = str  # "naive" | "cot" | "rubric"

_SYSTEM = {
    "naive": (
        "You compare two answers and decide which is better. "
        'Respond ONLY with JSON: {"winner": "A" | "B" | "tie"}.'
    ),
    "cot": (
        "You compare two answers. First reason step by step about correctness, "
        "relevance, and completeness, ignoring formatting, length, tone, and order. "
        'Then respond on the LAST line with JSON only: {"winner": "A" | "B" | "tie"}.'
    ),
    "rubric": (
        "You compare two answers using these criteria: accuracy, relevance, "
        "completeness, clarity. Briefly score each answer per criterion, then decide. "
        "Ignore formatting, length, tone, and order. "
        'End with JSON only: {"winner": "A" | "B" | "tie"}.'
    ),
}

_TEMPLATE = """Question:
{question}

Answer A:
{answer_a}

Answer B:
{answer_b}

Which answer is better?"""


class LLMPairwiseJudge(PairwiseJudge):
    def __init__(
        self,
        provider: Provider,
        strategy: Strategy = "cot",
        normalize: bool = False,
        name: str | None = None,
    ) -> None:
        if strategy not in _SYSTEM:
            raise ValueError(f"Unknown strategy {strategy!r}. Use one of {sorted(_SYSTEM)}.")
        self.provider = provider
        self.strategy = strategy
        self.normalize = normalize
        self.name = name or f"llm:{provider.name}:{strategy}{'+norm' if normalize else ''}"

    @staticmethod
    def _parse(text: str) -> Verdict:
        # Prefer the LAST JSON object (CoT/rubric put reasoning first).
        for match in reversed(re.findall(r"\{[^{}]*\}", text, re.DOTALL)):
            try:
                winner = str(json.loads(match).get("winner", "")).strip().upper()
            except (json.JSONDecodeError, AttributeError, TypeError):
                continue
            if winner in {"A", "B"}:
                return winner  # type: ignore[return-value]
            if winner == "TIE":
                return "tie"
        m = re.search(r"\b(A|B|tie)\b", text, re.IGNORECASE)
        if m:
            token = m.group(1).upper()
            return "tie" if token == "TIE" else token  # type: ignore[return-value]
        return "tie"

    def compare(self, question: str, answer_a: str, answer_b: str) -> Verdict:
        if self.normalize:
            answer_a, answer_b = strip_formatting(answer_a), strip_formatting(answer_b)
        prompt = _TEMPLATE.format(question=question, answer_a=answer_a, answer_b=answer_b)
        completion = self.provider.complete(prompt, system=_SYSTEM[self.strategy], temperature=0.0)
        return self._parse(completion.text)
