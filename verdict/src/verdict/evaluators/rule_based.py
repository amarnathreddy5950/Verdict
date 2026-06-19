"""Deterministic, offline rule-based evaluators."""

from __future__ import annotations

import json
import re

from verdict.core.models import Case, Score
from verdict.evaluators.base import Evaluator


def _binary(name: str, ok: bool, rationale: str) -> Score:
    return Score(name=name, value=1.0 if ok else 0.0, passed=ok, rationale=rationale)


class ExactMatch(Evaluator):
    name = "exact_match"

    def __init__(self, expected: str | None = None, ignore_case: bool = True) -> None:
        self.expected = expected
        self.ignore_case = ignore_case

    def evaluate(self, case: Case, output: str) -> Score:
        target = self.expected if self.expected is not None else case.reference
        if target is None:
            return _binary(self.name, False, "no expected/reference value provided")
        a, b = output.strip(), target.strip()
        if self.ignore_case:
            a, b = a.lower(), b.lower()
        ok = a == b
        return _binary(self.name, ok, "exact match" if ok else "did not match expected")


class Contains(Evaluator):
    name = "contains"

    def __init__(self, value: str, ignore_case: bool = True) -> None:
        self.value = value
        self.ignore_case = ignore_case

    def evaluate(self, case: Case, output: str) -> Score:
        hay, needle = output, self.value
        if self.ignore_case:
            hay, needle = hay.lower(), needle.lower()
        ok = needle in hay
        return _binary(self.name, ok, f"{'found' if ok else 'missing'} substring {self.value!r}")


class Regex(Evaluator):
    name = "regex"

    def __init__(self, pattern: str) -> None:
        self.pattern = re.compile(pattern, re.DOTALL)

    def evaluate(self, case: Case, output: str) -> Score:
        ok = self.pattern.search(output) is not None
        return _binary(self.name, ok, f"pattern {'matched' if ok else 'did not match'}")


class JSONSchemaValid(Evaluator):
    name = "json_schema"

    def __init__(self, schema: dict) -> None:
        self.schema = schema

    def evaluate(self, case: Case, output: str) -> Score:
        try:
            import jsonschema

            jsonschema.validate(json.loads(output), self.schema)
            return _binary(self.name, True, "valid JSON matching schema")
        except json.JSONDecodeError:
            return _binary(self.name, False, "output is not valid JSON")
        except Exception as exc:  # noqa: BLE001 - report any schema failure as a fail
            return _binary(self.name, False, f"schema validation failed: {exc}")


class NumericTolerance(Evaluator):
    name = "numeric"

    _NUM = re.compile(r"-?\d+(?:\.\d+)?")

    def __init__(self, expected: float | None = None, tolerance: float = 0.0) -> None:
        self.expected = expected
        self.tolerance = tolerance

    def _first_number(self, text: str) -> float | None:
        m = self._NUM.search(text)
        return float(m.group()) if m else None

    def evaluate(self, case: Case, output: str) -> Score:
        target = self.expected
        if target is None and case.reference is not None:
            target = self._first_number(case.reference)
        got = self._first_number(output)
        if target is None or got is None:
            return _binary(self.name, False, "could not parse a number")
        ok = abs(got - target) <= self.tolerance
        return Score(
            name=self.name,
            value=1.0 if ok else 0.0,
            passed=ok,
            rationale=f"got {got}, expected {target} (+/-{self.tolerance})",
            details={"got": got, "expected": target},
        )


class LengthWithin(Evaluator):
    name = "length"

    def __init__(self, min_words: int = 0, max_words: int = 10_000) -> None:
        self.min_words = min_words
        self.max_words = max_words

    def evaluate(self, case: Case, output: str) -> Score:
        n = len(output.split())
        ok = self.min_words <= n <= self.max_words
        return Score(
            name=self.name,
            value=1.0 if ok else 0.0,
            passed=ok,
            rationale=f"{n} words (allowed {self.min_words}-{self.max_words})",
            details={"words": n},
        )
