from verdict.core import runner
from verdict.core.models import Case, Dataset
from verdict.core.runner import Target
from verdict.evaluators.rule_based import Contains, LengthWithin
from verdict.providers.mock import MockProvider


def _dataset():
    return Dataset(
        name="d",
        cases=[
            Case(id="1", input="Cats are great. They purr a lot."),
            Case(id="2", input="Dogs are loyal. They bark sometimes."),
        ],
    )


def test_runner_produces_results_and_aggregates():
    target = Target(
        name="concise",
        provider=MockProvider(variant="concise"),
        prompt_template="Summarize: {input}",
    )
    evaluators = [LengthWithin(min_words=1, max_words=20), Contains(value="are")]
    result = runner.run(target, _dataset(), evaluators)

    assert result.n == 2
    assert "length" in result.evaluator_names()
    assert "contains" in result.evaluator_names()
    # concise variant returns the first sentence, which contains "are"
    assert result.pass_rate("contains") == 1.0
    assert 0.0 <= result.pass_rate() <= 1.0
    assert result.case_results[0].output  # non-empty output


def test_runner_records_per_case_output():
    target = Target(name="echo", provider=MockProvider(variant="echo"), prompt_template="{input}")
    result = runner.run(target, _dataset(), [LengthWithin(max_words=50)])
    assert all(r.error is None for r in result.case_results)
