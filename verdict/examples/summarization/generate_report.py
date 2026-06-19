#!/usr/bin/env python
"""Generate examples/summarization/REPORT.md fully offline.

Doubles as a library-usage example. Re-run with real models by switching the
provider in the config files (mock -> litellm + a model id).
"""

from __future__ import annotations

import random
from pathlib import Path

from verdict.core import runner
from verdict.core.config import load_run_config
from verdict.judge import JudgeAuditor, PairCase, SyntheticBiasedJudge, run_bias_suite
from verdict.report import runs_to_markdown

HERE = Path(__file__).parent


def demo_pairs(n: int = 120) -> list[PairCase]:
    truth = SyntheticBiasedJudge()  # unbiased -> serves as the "human" label
    rng = random.Random(0)
    pairs: list[PairCase] = []
    for i in range(n):
        q = f"Q{i}: briefly explain topic {i}."
        a = ("Answer " + "alpha " * rng.randint(2, 7) + f"#{i}").strip()
        b = ("Answer " + "beta " * rng.randint(2, 7) + f"#{i}").strip()
        pairs.append(
            PairCase(
                id=str(i),
                question=q,
                answer_a=a,
                answer_b=b,
                human_winner=truth.compare(q, a, b),
            )
        )
    return pairs


def main() -> None:
    results = []
    for cfg in ("config.concise.yaml", "config.verbose.yaml"):
        spec = load_run_config(HERE / cfg)
        results.append(runner.run(spec.target, spec.dataset, spec.evaluators))

    pairs = demo_pairs(120)
    auditor = JudgeAuditor()
    biased = auditor.audit(
        SyntheticBiasedJudge(position_bias=0.35, length_bias=0.25, name="biased-judge"), pairs
    )
    unbiased = auditor.audit(SyntheticBiasedJudge(name="unbiased-judge"), pairs)

    suite_biased = run_bias_suite(
        SyntheticBiasedJudge(
            position_bias=0.15,
            length_bias=0.3,
            style_bias=0.6,
            authority_bias=0.4,
            sentiment_bias=0.3,
            name="biased-judge",
        )
    )
    suite_clean = run_bias_suite(SyntheticBiasedJudge(name="unbiased-judge"))

    md = "\n\n".join(
        [
            "# Verdict — example report",
            "_Generated fully offline with the deterministic mock provider "
            "(`python generate_report.py`). Swap the provider in the configs to reproduce "
            "with real models._",
            runs_to_markdown(results, title="Summarization: concise vs verbose"),
            "## Why you must audit the judge",
            "Both judges below score the **same 120 pairs**, each shown in both orders "
            "(A,B) and (B,A). The biased judge has a **known injected** position/length bias; "
            "verdict's auditor detects it (low swap consistency, skewed first-position win rate) "
            "and flags the order-dependent pairs as unreliable. Note the trade-off: swap "
            "calibration converts those flagged pairs to ties, so it buys reliability at the cost "
            "of coverage rather than magically recovering the right answer. The unbiased judge "
            "is the control.",
            "### Biased judge (injected position=0.35, length=0.25)",
            biased.to_markdown(),
            "### Unbiased judge (control)",
            unbiased.to_markdown(),
            "## Full bias suite",
            "Order-flipping only catches *position* bias. The suite below probes five biases "
            "with controlled pairs (same content, one differing feature) and reports a score in "
            "[-1, 1] with a bootstrap 95% CI. See [../../docs/BIASES.md](../../docs/BIASES.md).",
            suite_biased.to_markdown(),
            suite_clean.to_markdown(),
        ]
    )
    (HERE / "REPORT.md").write_text(md)
    print(f"Wrote {HERE / 'REPORT.md'}")


if __name__ == "__main__":
    main()
