"""Evaluator registry + factory for rule-based evaluators."""

from __future__ import annotations

from typing import Any

from verdict.evaluators.base import Evaluator
from verdict.evaluators.judge import JudgeEvaluator
from verdict.evaluators.rule_based import (
    Contains,
    ExactMatch,
    JSONSchemaValid,
    LengthWithin,
    NumericTolerance,
    Regex,
)

_RULE_TYPES = {
    "exact_match": ExactMatch,
    "contains": Contains,
    "regex": Regex,
    "json_schema": JSONSchemaValid,
    "numeric": NumericTolerance,
    "length": LengthWithin,
}


def build_rule_evaluator(spec: dict[str, Any]) -> Evaluator:
    """Build a rule-based evaluator from a config mapping like {"type": "contains", ...}."""
    spec = dict(spec)
    etype = spec.pop("type", None)
    name = spec.pop("name", None)
    if etype not in _RULE_TYPES:
        raise ValueError(
            f"Unknown rule evaluator type {etype!r}. Known: {sorted(_RULE_TYPES)} "
            "(use the config loader for 'judge')."
        )
    evaluator = _RULE_TYPES[etype](**spec)
    if name:
        evaluator.name = name
    return evaluator


__all__ = [
    "Evaluator",
    "JudgeEvaluator",
    "ExactMatch",
    "Contains",
    "Regex",
    "JSONSchemaValid",
    "NumericTolerance",
    "LengthWithin",
    "build_rule_evaluator",
]
