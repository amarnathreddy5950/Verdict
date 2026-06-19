"""Pairwise judging primitives used by the bias auditor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

Verdict = Literal["A", "B", "tie"]


class PairwiseJudge(ABC):
    """Decides which of two answers is better for a question."""

    name: str = "judge"

    @abstractmethod
    def compare(self, question: str, answer_a: str, answer_b: str) -> Verdict:
        """Return 'A' if answer_a is better, 'B' if answer_b is better, else 'tie'."""
        raise NotImplementedError
