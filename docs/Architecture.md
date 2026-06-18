# Architecture & mental model

## The one idea
verdict does **two jobs**:

1. **Evaluate the AI's outputs** — "is the answer good?"
2. **Evaluate the judge itself** — "can we trust the AI that's doing the grading?"  ← the differentiator

Almost every eval tool does Job 1. verdict's edge is Job 2.

---

## Job 1 — the evaluation pipeline

```
 dataset.yaml            config.yaml
 (your test cases)       (model + prompt + which checks)
      │                        │
      ▼                        ▼
 ┌─────────┐   builds   ┌──────────────┐   prompt   ┌─────────────┐
 │ Dataset │──────────▶ │   Target     │──────────▶ │  Provider   │
 │ (Cases) │            │ prompt+model │            │ mock/litellm│
 └─────────┘            └──────────────┘            └──────┬──────┘
                                                          │ output
                                                          ▼
                                   ┌───────────────────────────────────┐
                                   │            Evaluators             │
                                   │  rule-based (exact/regex/json/…)  │
                                   │  + LLM-as-judge (rubric scoring)  │
                                   └─────────────────┬─────────────────┘
                                                     │ Scores
                                                     ▼
                                   ┌───────────────────────────────────┐
                                   │  RunResult → Report (table/JSON)  │
                                   │  + CI regression gate vs baseline │
                                   └───────────────────────────────────┘
```

## Job 2 — the judge-audit pipeline (the differentiator)

```
                         a JUDGE (anything that picks A vs B)
                ┌───────────────────────────────────────────────┐
                │  LLMPairwiseJudge   OR   SyntheticBiasedJudge │
                │  (real model)            (fake, known biases) │
                └───────────────┬───────────────┬───────────────┘
                                │               │
            ┌───────────────────▼──┐     ┌──────▼───────────────────────┐
            │  JudgeAuditor        │     │  Bias Probes                 │
            │  (swap test:         │     │  controlled pairs: same      │
            │   show A,B and B,A)  │     │  content + 1 difference:     │
            │  → position bias,    │     │  position/length/style/      │
            │    swap consistency, │     │  authority/sentiment         │
            │    kappa vs humans   │     │  → score [-1..1] + 95% CI    │
            └──────────────────────┘     └──────────────────────────────┘

   Mitigations that WRAP the judge:  CoT / rubric strategy · format normalize ·
                                     JuryJudge (panel vote) · self-preference warning
```

---

## Components (mapped to the code)

**Core (`src/verdict/core/`)**
- `models.py` — `Case`, `Dataset`, `Score`, `CaseResult`, `RunResult` (+ aggregates like pass-rate).
- `runner.py` — `Target` (prompt + provider = the thing under test) and `run()`.
- `config.py` — loads a YAML config into a Target + dataset + evaluators.

**Providers (`src/verdict/providers/`)** — talk to models behind one interface.
- `base.py` — the `Provider` contract (`complete(prompt) -> text + latency + cost`).
- `mock.py` — deterministic offline fake model (also a fake judge); zero API keys.
- `litellm_provider.py` — real models (OpenAI/Anthropic/Bedrock), imported lazily.
- `cache.py` — SQLite cache so identical calls aren't paid for twice.

**Evaluators (`src/verdict/evaluators/`)** — Job 1 checks.
- `rule_based.py` — exact, contains, regex, JSON-schema, numeric, length.
- `judge.py` — `JudgeEvaluator`: LLM scores an answer 1–5 on a rubric.

**Judge (`src/verdict/judge/`)** — Job 2 machinery.
- `base.py` — `PairwiseJudge` (compare two answers -> A/B/tie).
- `synthetic.py` — `SyntheticBiasedJudge` with injectable bias dials (for offline tests/demos).
- `llm.py` — `LLMPairwiseJudge` with mitigations (`strategy="cot"|"rubric"`, `normalize`).
- `audit.py` — `JudgeAuditor` (swap test), `AuditReport`, `cohen_kappa`, `PairCase`.
- `probes.py` — controlled-pair bias suite: `run_probe`, `run_bias_suite`, scores + CIs.
- `jury.py` — `JuryJudge` (panel vote) + `self_preference_warning`.
- `normalize.py` — `strip_formatting` (kills style bias).

**Support**
- `stats.py` — `bootstrap_ci` (honest uncertainty on every number).
- `report/render.py` — Markdown leaderboard + `regression_check`.
- `cli.py` — `verdict run` / `verdict audit` / `verdict probe`.

**Proof**
- `tests/` — 28 tests, incl. probes detecting injected bias and staying quiet on a fair judge.
- `examples/summarization/` — offline example + `generate_report.py` -> `REPORT.md`.
- `docs/BIASES.md` — bias taxonomy + mitigations + references.
- `.github/workflows/` — CI (lint/type/test) + eval regression gate.

See **[WALKTHROUGH.md](WALKTHROUGH.md)** for a step-by-step run with real data.
