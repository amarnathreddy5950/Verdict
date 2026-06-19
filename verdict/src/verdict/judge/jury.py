"""Multi-judge jury + a self-preference guardrail.

Why:
- A *single* judge's systematic bias cannot be averaged away by more samples, but a
  panel of **diverse** judges dilutes any one judge's bias (Verga et al. 2024).
- **Self-preference bias**: judges favor their own outputs. The simplest mitigation is
  to never let a model grade its own generations; ``self_preference_warning`` flags it.
"""

from __future__ import annotations

from collections import Counter

from verdict.judge.base import PairwiseJudge, Verdict


class JuryJudge(PairwiseJudge):
    """Aggregate several judges by majority vote (ties broken to 'tie')."""

    def __init__(self, judges: list[PairwiseJudge], name: str = "jury") -> None:
        if not judges:
            raise ValueError("JuryJudge needs at least one judge.")
        self.judges = judges
        self.name = name

    def compare(self, question: str, answer_a: str, answer_b: str) -> Verdict:
        votes = Counter(j.compare(question, answer_a, answer_b) for j in self.judges)
        top = votes.most_common()
        # If the top two are tied in count, the panel is undecided -> 'tie'.
        if len(top) > 1 and top[0][1] == top[1][1]:
            return "tie"
        return top[0][0]


def self_preference_warning(judge_model: str, target_model: str) -> str | None:
    """Return a warning string if the judge is grading its own model's outputs, else None."""
    j = (judge_model or "").lower()
    t = (target_model or "").lower()
    if j and t and (j == t or j in t or t in j):
        return (
            f"Self-preference risk: judge ({judge_model}) and target ({target_model}) look like "
            "the same model family. Judges favor their own outputs -- use a different judge."
        )
    return None
