# verdict

**A small, model-agnostic LLM evaluation toolkit with a judge bias audit you can actually trust.**

Most eval setups score outputs with an LLM "judge" and never check whether that judge is
**biased**. Research is clear that LLM judges systematically prefer the **first-shown** answer
(position bias) and **longer** answers (length bias). `verdict` makes auditing and calibrating
the judge a first-class step, alongside the usual rule-based and LLM-as-judge evaluators.

- ✅ Runs **fully offline** with a deterministic mock provider (zero API keys to try it).
- ⚖️ **Judge bias suite**: position, length, **style**, authority, and sentiment probes with
  bootstrap CIs, plus swap calibration and human-agreement (Cohen's kappa). See
  [docs/BIASES.md](docs/BIASES.md).
- 🛡️ **Mitigations built in**: chain-of-thought and rubric judging, format normalization, a
  multi-judge jury, and a self-preference guardrail.
- 🧪 Rule-based + LLM-as-judge evaluators, composable per case.
- 🚦 **CI regression gate**: treat prompts as testable artifacts; fail PRs on quality drops.
- 🔌 Real models via [litellm] (OpenAI, Anthropic, Amazon Bedrock, ...) behind one interface.

> Status: portfolio / educational project. The eval space has mature tools (promptfoo, DeepEval,
> Ragas, Inspect, Phoenix). `verdict`'s niche is making **judge trustworthiness** the headline.

## Use it from GitHub

```bash
git clone https://github.com/amarnathreddy5950/verdict.git
cd verdict
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"        # editable install + dev tools (ruff, mypy, pytest)
# optional, for real models:
pip install -e ".[providers]"  # litellm: OpenAI / Anthropic / Bedrock / ...
```

## Quickstart (no API key needed)

```bash
# 1) Evaluate a target over a dataset (offline mock provider)
verdict run examples/summarization/config.concise.yaml

# 2) Audit a judge for bias (offline demos with KNOWN injected biases)
verdict audit            # swap test: position bias + human agreement
verdict probe            # full bias suite: position/length/style/authority/sentiment

# 3) Regenerate the example report
python examples/summarization/generate_report.py
```

See [`examples/summarization/REPORT.md`](examples/summarization/REPORT.md) for a generated
comparison table **and** a judge bias audit.

## The differentiator: audit your judge

```python
from verdict.judge import JudgeAuditor, SyntheticBiasedJudge, PairCase

pairs = [PairCase(id="1", question="...", answer_a="...", answer_b="...")]
report = JudgeAuditor().audit(SyntheticBiasedJudge(position_bias=0.35), pairs)
print(report.to_markdown())
# -> swap consistency, position-bias rate, length-bias rate, and
#    human-agreement (Cohen's kappa) raw vs swap-calibrated
```

To audit a **real** judge, build an `LLMPairwiseJudge` over any provider and pass it to the
same `JudgeAuditor`.

## The full bias suite + mitigations

Order-flipping only catches **position** bias, which on modern models is small. The bigger
problems are **style/format**, length, authority, and sentiment bias. Run the whole suite:

```python
from verdict.judge import SyntheticBiasedJudge, run_bias_suite

suite = run_bias_suite(SyntheticBiasedJudge(style_bias=0.6))
print(suite.to_markdown())   # per-bias score in [-1, 1] with a bootstrap 95% CI
```

Mitigations the research validates, all built in:

```python
from verdict.judge import LLMPairwiseJudge, JuryJudge, self_preference_warning

# chain-of-thought + format normalization (counters the dominant style bias)
judge = LLMPairwiseJudge(provider, strategy="cot", normalize=True)

# a diverse panel dilutes any single judge's bias
jury = JuryJudge([judge_a, judge_b, judge_c])

# never let a model grade its own outputs
warn = self_preference_warning(judge_model="gpt-4o", target_model="gpt-4o")
```

See **[docs/BIASES.md](docs/BIASES.md)** for the full taxonomy, what verdict measures, and
which mitigation to use when.

## Use real models

```yaml
# config.yaml
target:
  name: gpt-4o-mini
  provider: litellm
  model: gpt-4o-mini
  prompt: "Summarize in one sentence:\n{input}"
dataset: dataset.yaml
evaluators:
  - type: length
    min_words: 4
    max_words: 25
```

```bash
pip install -e ".[providers]"
export OPENAI_API_KEY=...        # or Anthropic / Bedrock creds
verdict run config.yaml --report report.md
```

## How it works

```
Dataset ──> Target (prompt + Provider) ──> output ──> Evaluators ──> Scores ──> Report
                                                          │
                              rule-based (exact/regex/contains/json-schema/numeric/length)
                              LLM-as-judge (pointwise rubric)

Judge auditing (separate, the headline):
  PairwiseJudge ──> JudgeAuditor (swap test) ──> bias metrics + swap-calibrated verdicts
```

Core abstractions: `Case` / `Dataset`, `Provider`, `Target`, `Evaluator`, `PairwiseJudge`,
`JudgeAuditor`, `RunResult`.

## CI regression gate

`.github/workflows/eval-gate.yml` runs the eval on PRs and fails if the pass rate drops more
than a threshold versus a committed baseline:

```bash
verdict run config.yaml --baseline baseline.json --threshold 0.05
```

## Documentation

- **[docs/WALKTHROUGH.md](docs/WALKTHROUGH.md)** — step-by-step example with diagrams, a
  flowchart, and real command output. Start here.
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — the mental model, data-flow diagrams, and
  every component explained.
- **[docs/BIASES.md](docs/BIASES.md)** — the full judge-bias taxonomy, what verdict measures,
  which mitigations to use when, and references.
- **[examples/summarization/REPORT.md](examples/summarization/REPORT.md)** — a generated report
  comparing two summarizers and a biased vs. fair judge.

## Development

```bash
pip install -e ".[dev]"
ruff check . && mypy && pytest --cov=verdict
```


[litellm]: https://github.com/BerriAI/litellm
