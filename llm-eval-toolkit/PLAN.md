# Implementation Plan — LLM Eval Toolkit (flagship project)

> Status: IMPLEMENTED (v0.2) — built at ../verdict/. Core engine, evaluators, swap auditor, and a
> research-backed **bias suite** (position/length/style/authority/sentiment with bootstrap CIs)
> plus mitigations (CoT/rubric judging, format normalization, multi-judge jury, self-preference
> guardrail) are built, tested (30 tests, ruff+mypy clean), and documented in verdict/docs/BIASES.md.
> Remaining stretch: agent/trajectory eval (v0.3).

## 1. Positioning (why this isn't a clone)
The eval space is crowded (promptfoo, DeepEval, Ragas, Inspect AI, Phoenix, Braintrust,
Langfuse, Opik, MLflow). We are **not** trying to beat them. This is a portfolio flagship that
**demonstrates mastery** and owns a sharp, research-backed niche most projects ignore:

**"A judge you can actually trust."** Headline differentiator = a built-in **judge bias audit +
calibration** layer (position / length / format / self bias), uncertainty reporting, and
human-agreement scoring — plus **agent/trajectory evaluation** and a **CI regression gate**.

This maps directly to target employers: Weights & Biases, Arize, Braintrust, Humanloop, Cohere,
Hugging Face — and mirrors your real AWS work (LLM-as-judge eval framework, monitoring, GA rigor).

## 2. Scope (phased)
**v0.1 — Core engine (must-have)**
- Test cases + datasets (YAML/JSON/CSV loaders)
- Provider-agnostic model calls with caching + cost/latency tracking
- Rule-based evaluators: exact match, regex, contains, JSON-schema validity, numeric tolerance
- LLM-as-judge evaluators: pointwise (rubric) and pairwise (with position-swap)
- Reports: rich CLI table + Markdown/HTML + JSON; pytest-style assertions
- CLI: `eval run config.yaml`

**v0.2 — Judge Audit + CI gate (the differentiator)**
- Bias probes: position (swap-consistency), length (score-vs-length correlation), self/format bias
- Calibration: permutation-based; report calibrated scores + bootstrap confidence intervals
- Human-agreement: load human labels, compute Cohen's kappa / % agreement
- GitHub Action: on PRs touching `prompts/**`, run evals vs a baseline, comment score delta,
  fail on regression beyond a threshold

**v0.3 — Agent/trajectory eval (stretch, ties to your story)**
- Trajectory metrics: task success, tool-selection precision, step utility
- Efficiency metrics: latency, tokens, tool-call count, loop detection
- Example multi-step agent under eval

## 3. Tech stack
- **Python 3.11+** (the lingua franca of this space)
- **litellm** for provider-agnostic calls (OpenAI, Anthropic, **Bedrock**, etc. for free)
- **Pydantic v2** for typed configs/results, **Typer** (CLI), **Rich** (tables)
- **pytest** integration; **ruff** + **mypy**; **uv**/**hatch** packaging
- **SQLite cache** for model calls -> cheap, reproducible reruns
- **asyncio** for concurrency; **GitHub Actions** for CI; MkDocs-Material (docs, optional)
- License: **MIT**

## 4. Architecture (core abstractions)
- `Case` — input, optional reference/expected, metadata
- `Dataset` — collection + loaders
- `Target` — the thing under test (prompt template + model, or a callable/agent)
- `Provider` — model-call interface (litellm-backed), with caching + cost
- `Evaluator` — scores an output -> `Score{value, passed, rationale}`; rule-based + judge; composable
- `Judge` — LLM-as-judge with bias controls (swap, rubric, reference-guided)
- `Audit` — bias probes + calibration + human-agreement on a judge
- `Runner` — async orchestration: produce outputs, run evaluators, retries, caching
- `Report` — aggregate, compare-to-baseline, render md/html/json

## 5. Repo structure
```
<project-name>/
├── README.md                 # problem, architecture diagram, results, quickstart
├── REPORT.md                 # example run with real numbers + a judge bias audit
├── pyproject.toml
├── src/<pkg>/
│   ├── core/                 # case, dataset, target, runner, config, score
│   ├── providers/            # litellm wrapper, caching, cost
│   ├── evaluators/           # rule_based, judge, schema
│   ├── judge/                # judge, bias, calibration
│   ├── agents/               # trajectory eval (v0.3)
│   ├── report/               # render + compare
│   └── cli.py
├── examples/
│   ├── summarization/        # dataset.yaml, config.yaml, REPORT.md
│   └── function-calling/     # agent/tool-use example (v0.3)
├── tests/
├── .github/workflows/        # ci.yml (lint+test), eval-gate.yml (regression gate)
└── docs/
```

## 6. The showcase deliverable
A bundled example that evaluates 2–3 models/prompts on a real task, producing a `REPORT.md` with:
- A comparison table (quality, latency, cost per model/prompt)
- **A judge bias audit**: e.g., "judge shows 8% position bias and a length-score correlation of
  r=0.31; after permutation calibration, the model ranking changes / stabilizes."
- Agreement with a small human-labeled set (Cohen's kappa)
This single artifact is what makes recruiters stop scrolling.

## 7. Build order (weekend-scale chunks)
1. Core engine + rule-based evaluators + CLI + 1 example + tests + CI lint/test  (v0.1)
2. LLM-as-judge (pointwise + pairwise w/ swap) + caching + cost                 (v0.1)
3. Judge Audit (bias + calibration + human-agreement) + REPORT with numbers     (v0.2) ← headline
4. Regression-gate GitHub Action + baseline compare + PR comment                 (v0.2)
5. Agent/trajectory eval + example                                               (v0.3)
6. Docs + polish + a short blog writeup                                          (v0.3)

## 8. Honest expectations
- This won't get thousands of stars (mature competitors exist). That's fine.
- Its job is to **prove depth** (you understand judge bias, calibration, agent eval, CI rigor)
  and give recruiters/interviewers a concrete, high-quality thing to discuss.
- The README + REPORT (with real numbers and a bias audit) matter as much as the code.

## 9. Open questions to decide before building
1. **Project name** — options: `judgelab`, `evalforge`, `verdict`, `calibre`, `fair-eval`. Pick one.
2. **Providers** — confirm litellm (recommended) so Bedrock/OpenAI/Anthropic all work.
3. **v1 cut** — ship Core + Judge Audit + CI first; defer agent/trajectory to v0.3? (recommended)
4. **Example domain** — summarization, RAG/QA, or function-calling/agent? (agent ties to your story)
5. **Language** — Python first (confirm). Optional thin TS client later.
6. **UI** — keep CLI + static HTML report for v1 (no web app)? (recommended, stays lean)
7. **Hosting** — publish the example REPORT via GitHub Pages?
