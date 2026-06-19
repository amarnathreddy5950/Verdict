"""Run a target over a dataset and apply evaluators to each output."""

from __future__ import annotations

from dataclasses import dataclass

from verdict.core.models import Case, CaseResult, Dataset, RunResult
from verdict.evaluators.base import Evaluator
from verdict.providers.base import Provider


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:  # tolerate templates that reference missing keys
        return ""


@dataclass
class Target:
    """The thing under test: a provider plus a prompt template."""

    name: str
    provider: Provider
    prompt_template: str = "{input}"
    system: str | None = None

    def build_prompt(self, case: Case) -> str:
        return self.prompt_template.format_map(_SafeDict(input=case.input, **case.metadata))


def run(target: Target, dataset: Dataset, evaluators: list[Evaluator]) -> RunResult:
    results: list[CaseResult] = []
    for case in dataset:
        try:
            prompt = target.build_prompt(case)
            completion = target.provider.complete(
                prompt, system=target.system, temperature=0.0
            )
            scores = [ev.evaluate(case, completion.text) for ev in evaluators]
            results.append(
                CaseResult(
                    case_id=case.id,
                    output=completion.text,
                    scores=scores,
                    latency_ms=completion.latency_ms,
                    cost_usd=completion.cost_usd,
                    tokens=completion.tokens,
                )
            )
        except Exception as exc:  # noqa: BLE001 - record per-case failures, keep going
            results.append(CaseResult(case_id=case.id, error=str(exc)))
    return RunResult(target=target.name, dataset=dataset.name, case_results=results)
