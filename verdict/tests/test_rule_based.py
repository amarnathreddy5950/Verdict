from verdict.core.models import Case
from verdict.evaluators import build_rule_evaluator
from verdict.evaluators.rule_based import (
    Contains,
    ExactMatch,
    JSONSchemaValid,
    LengthWithin,
    NumericTolerance,
    Regex,
)

CASE = Case(id="t", input="x", reference="42")


def test_exact_match():
    ev = ExactMatch(expected="Hello")
    assert ev.evaluate(CASE, "hello").passed
    assert not ev.evaluate(CASE, "world").passed


def test_contains():
    ev = Contains(value="cat")
    assert ev.evaluate(CASE, "the CAT sat").passed
    assert not ev.evaluate(CASE, "the dog sat").passed


def test_regex():
    ev = Regex(pattern=r"\d{3}-\d{4}")
    assert ev.evaluate(CASE, "call 555-1234").passed
    assert not ev.evaluate(CASE, "no number").passed


def test_json_schema():
    schema = {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}
    ev = JSONSchemaValid(schema=schema)
    assert ev.evaluate(CASE, '{"name": "amar"}').passed
    assert not ev.evaluate(CASE, '{"age": 1}').passed
    assert not ev.evaluate(CASE, "not json").passed


def test_numeric_tolerance_uses_reference():
    ev = NumericTolerance(tolerance=0.5)
    assert ev.evaluate(CASE, "the answer is 42.2").passed
    assert not ev.evaluate(CASE, "the answer is 50").passed


def test_length_within():
    ev = LengthWithin(min_words=2, max_words=4)
    assert ev.evaluate(CASE, "two three words").passed
    assert not ev.evaluate(CASE, "one").passed


def test_factory_builds_and_renames():
    ev = build_rule_evaluator({"type": "contains", "value": "x", "name": "has_x"})
    assert ev.name == "has_x"
    assert ev.evaluate(CASE, "x marks").passed
