"""Evaluator interface: score a single output for a single case."""

from __future__ import annotations

from abc import ABC, abstractmethod

from verdict.core.models import Case, Score


class Evaluator(ABC):
    name: str = "evaluator"

    @abstractmethod
    def evaluate(self, case: Case, output: str) -> Score:
        raise NotImplementedError
