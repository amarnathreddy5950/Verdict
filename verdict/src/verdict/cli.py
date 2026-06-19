"""verdict command-line interface."""

from __future__ import annotations

import json
import random
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from verdict.core import runner as runner_mod
from verdict.core.config import load_run_config
from verdict.core.models import RunResult
from verdict.judge import (
    JudgeAuditor,
    LLMPairwiseJudge,
    PairCase,
    PairwiseJudge,
    SyntheticBiasedJudge,
    run_bias_suite,
    self_preference_warning,
)
from verdict.providers import SqliteCache, build_provider
from verdict.report import regression_check, runs_to_markdown

app = typer.Typer(
    add_completion=False,
    help="Evaluate LLMs, and audit the judge you evaluate with.",
)
console = Console()


def _print_run_table(result: RunResult) -> None:
    table = Table(title=f"{result.target}  ({result.dataset}, n={result.n})")
    table.add_column("case")
    table.add_column("output", overflow="fold", max_width=48)
    for name in result.evaluator_names():
        table.add_column(name, justify="center")
    for r in result.case_results:
        cells = [r.case_id, (r.error and f"[red]ERROR: {r.error}") or r.output]
        for name in result.evaluator_names():
            s = r.score(name)
            cells.append("[green]PASS" if (s and s.passed) else "[red]fail" if s else "-")
        table.add_row(*cells)
    console.print(table)
    console.print(f"Overall pass rate: [bold]{result.pass_rate():.0%}[/bold]")


@app.command()
def run(
    config: str = typer.Argument(..., help="Path to a run config YAML."),
    out: str | None = typer.Option(None, help="Write full results JSON here."),
    report: str | None = typer.Option(None, help="Write a Markdown report here."),
    baseline: str | None = typer.Option(None, help="Baseline results JSON to gate against."),
    threshold: float = typer.Option(0.05, help="Max allowed pass-rate drop vs baseline."),
    no_cache: bool = typer.Option(False, help="Disable the SQLite model-call cache."),
) -> None:
    """Run an evaluation; optionally gate against a baseline (non-zero exit on regression)."""
    cache = None if no_cache else SqliteCache()
    spec = load_run_config(config, cache=cache)
    result = runner_mod.run(spec.target, spec.dataset, spec.evaluators)
    _print_run_table(result)

    if report:
        Path(report).write_text(runs_to_markdown([result], title=f"Verdict: {result.target}"))
        console.print(f"Wrote report -> {report}")
    if out:
        payload = {"summary": result.summary(), "result": result.model_dump()}
        Path(out).write_text(json.dumps(payload, indent=2))
        console.print(f"Wrote results -> {out}")

    if baseline:
        base = json.loads(Path(baseline).read_text())
        base_summary = base.get("summary", base)
        ok, messages = regression_check(base_summary, result, threshold)
        for m in messages:
            console.print(f"[green]{m}" if ok else f"[red]{m}")
        if not ok:
            raise typer.Exit(code=1)


def _demo_pairs(n: int) -> list[PairCase]:
    """Synthetic pairs with unbiased 'human' labels (an unbiased judge's content preference)."""
    truth = SyntheticBiasedJudge()  # all biases zero -> stable content preference
    rng = random.Random(0)
    pairs: list[PairCase] = []
    for i in range(n):
        q = f"Q{i}: briefly explain topic {i}."
        a = "Answer " + "alpha " * rng.randint(2, 7) + f"#{i}"
        b = "Answer " + "beta " * rng.randint(2, 7) + f"#{i}"
        pairs.append(
            PairCase(
                id=str(i),
                question=q,
                answer_a=a.strip(),
                answer_b=b.strip(),
                human_winner=truth.compare(q, a.strip(), b.strip()),
            )
        )
    return pairs


@app.command()
def audit(
    pairs: str | None = typer.Option(None, help="JSON file of pairwise cases (real audit)."),
    provider: str = typer.Option("mock", help="Provider for a real judge: mock|litellm."),
    model: str | None = typer.Option(None, help="Model id when provider=litellm."),
    out: str | None = typer.Option(None, help="Write the audit report Markdown here."),
    position_bias: float = typer.Option(0.35, help="Demo only: injected position bias."),
    length_bias: float = typer.Option(0.25, help="Demo only: injected length bias."),
    n: int = typer.Option(120, help="Demo only: number of synthetic pairs."),
) -> None:
    """Audit a pairwise judge for position/length bias and swap-calibrate it.

    With no --pairs file, runs an offline DEMO against a judge with KNOWN injected
    biases, so you can see the auditor catch them.
    """
    judge: PairwiseJudge
    if pairs:
        cases = [PairCase(**p) for p in json.loads(Path(pairs).read_text())]
        spec = {"provider": provider}
        if model:
            spec["model"] = model
        judge = LLMPairwiseJudge(build_provider(spec))
    else:
        judge = SyntheticBiasedJudge(
            position_bias=position_bias, length_bias=length_bias, name="synthetic-biased-judge"
        )
        cases = _demo_pairs(n)

    report = JudgeAuditor().audit(judge, cases)
    console.print(report.to_markdown())
    if out:
        Path(out).write_text(report.to_markdown())
        console.print(f"\nWrote audit -> {out}")


@app.command()
def probe(
    provider: str = typer.Option("mock", help="'mock' = offline demo; else litellm."),
    model: str | None = typer.Option(None, help="Model id when provider=litellm."),
    strategy: str = typer.Option("cot", help="Real-judge mitigation: naive|cot|rubric."),
    normalize: bool = typer.Option(False, help="Strip Markdown before judging (style mitigation)."),
    target_model: str | None = typer.Option(None, help="Model under test (self-preference check)."),
    out: str | None = typer.Option(None, help="Write the bias-suite Markdown here."),
) -> None:
    """Run the controlled bias suite (position/length/style/authority/sentiment).

    With provider=mock this is an offline DEMO against a judge with KNOWN injected
    biases. With provider=litellm it audits a real judge model.
    """
    judge: PairwiseJudge
    if provider == "mock":
        judge = SyntheticBiasedJudge(
            position_bias=0.15,
            length_bias=0.3,
            style_bias=0.6,
            authority_bias=0.4,
            sentiment_bias=0.3,
            name="synthetic-biased-judge",
        )
    else:
        spec = {"provider": provider}
        if model:
            spec["model"] = model
        judge = LLMPairwiseJudge(build_provider(spec), strategy=strategy, normalize=normalize)
        if target_model:
            warning = self_preference_warning(model or provider, target_model)
            if warning:
                console.print(f"[yellow]⚠ {warning}")

    suite = run_bias_suite(judge)
    console.print(suite.to_markdown())
    if out:
        Path(out).write_text(suite.to_markdown())
        console.print(f"\nWrote bias suite -> {out}")


if __name__ == "__main__":
    app()
