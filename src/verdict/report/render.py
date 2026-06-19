"""Render run results to Markdown and check for regressions against a baseline."""

from __future__ import annotations

from typing import Any

from verdict.core.models import RunResult


def runs_to_markdown(results: list[RunResult], title: str = "Verdict results") -> str:
    evaluators: list[str] = []
    for r in results:
        for name in r.evaluator_names():
            if name not in evaluators:
                evaluators.append(name)

    header = [
        "Target",
        "Pass rate",
        *[f"{n} (mean)" for n in evaluators],
        "Latency (ms)",
        "Cost ($)",
    ]
    lines = [f"## {title}", "", "| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in results:
        row = [r.target, f"{r.pass_rate():.0%}"]
        for name in evaluators:
            ms = r.mean_score(name)
            row.append("-" if ms is None else f"{ms:.2f}")
        lat = r.mean_latency_ms()
        row.append("-" if lat is None else f"{lat:.1f}")
        row.append(f"{r.total_cost_usd():.4f}")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def regression_check(
    baseline_summary: dict[str, Any], current: RunResult, threshold: float = 0.05
) -> tuple[bool, list[str]]:
    """Return (ok, messages). ok=False if quality dropped beyond ``threshold``."""
    ok = True
    messages: list[str] = []

    base_pr = float(baseline_summary.get("pass_rate", 0.0))
    cur_pr = current.pass_rate()
    if cur_pr < base_pr - threshold:
        ok = False
        messages.append(
            f"Overall pass rate dropped {base_pr:.0%} -> {cur_pr:.0%} "
            f"(> {threshold:.0%} threshold)."
        )

    base_by = baseline_summary.get("by_evaluator", {})
    for name in current.evaluator_names():
        prev = base_by.get(name, {}).get("pass_rate")
        if prev is None:
            continue
        cur = current.pass_rate(name)
        if cur < float(prev) - threshold:
            ok = False
            messages.append(f"'{name}' pass rate dropped {float(prev):.0%} -> {cur:.0%}.")

    if ok:
        messages.append("No regressions beyond threshold.")
    return ok, messages
