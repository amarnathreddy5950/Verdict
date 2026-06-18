# Walkthrough: using verdict end to end

Two everyday files drive everything:

- **`dataset.yaml`** = *your test cases* (your data, specific to your use-case).
- **`config.yaml`**  = *how to run the test* (which model, what prompt, which checks).

Both are written by you and customized per use-case.

---

## Scenario A — "Is my summarizer any good?" (`verdict run`)

### 1. Write the test cases (`dataset.yaml`)
```yaml
cases:
  - id: photosynthesis
    input: "Photosynthesis is how plants turn sunlight, CO2, and water into glucose and oxygen."
    reference: "Plants turn sunlight, CO2, and water into food and oxygen."
```

### 2. Write the config (`config.yaml`)
```yaml
target:
  provider: mock              # offline fake model; use 'litellm' + model: for a real one
  prompt: "Summarize in one sentence: {input}"
dataset: dataset.yaml
evaluators:
  - type: length              # objective check: 4–25 words
    min_words: 4
    max_words: 25
  - type: judge               # subjective check: an AI scores faithfulness 1–5
    rubric: "5 = faithful & concise; 1 = wrong/empty"
```

### 3. Run it
```
$ verdict run config.yaml
```

### 4. Real output (concise vs verbose prompt)
```
concise-summarizer   Overall pass rate: 100%   (all summaries short + faithful)
verbose-summarizer   Overall pass rate:  50%   (faithful, but length check FAILS:
                                                 it padded every answer with filler)
```

### What happened inside
```
USER          CLI         Config       Runner        Provider       Evaluators
 │ run ──────▶ │           │            │              │              │
 │             │ load ───▶ │            │              │              │
 │             │ ◀ Target + Dataset + Evaluators       │              │
 │             │ run() ─────────────────▶│             │              │
 │             │                         │ fill prompt │              │
 │             │                         │ ───────────▶│ complete()   │
 │             │                         │ ◀ "Photosynthesis is…"     │
 │             │                         │ score ──────────────────-─▶│
 │             │                         │   length 12 words → PASS   │
 │             │                         │   judge 5/5 → PASS         │
 │             │ ◀ RunResult (100%)      │             │              │
 │ ◀ table ────│           │            │              │              │
```

---

## Scenario B — "Can I trust the AI judge?" (`verdict probe` / `verdict audit`)

The judge above gave 5/5 — but is it *fair*? We feed it **trick pairs**: two answers with the
**same content**, differing only in one feature. A fair judge should say "tie".

### One trick pair (style bias)
```
Question: "Summarize: plants make food from sunlight."
Answer A: "**Summary:**\n- Plants make food from sunlight"   (same content, but formatted)
Answer B: "Plants make food from sunlight"                    (same content, plain)

Round 1: show (A,B) -> judge picks A   (the formatted one)
Round 2: show (B,A) -> judge picks B   (STILL the formatted one!)
=> formatting won regardless of order  =>  STYLE BIAS
```

### Real output (`verdict probe`, against a deliberately biased judge)
```
| Bias      | Score (-1..1) | 95% CI         | Reading                          |
|-----------|---------------|----------------|----------------------------------|
| position  | +1.00         | [+1.00,+1.00]  | prefers first position           |
| length    | +0.35         | [+0.21,+0.49]  | prefers the longer answer        |
| style     | +0.59         | [+0.49,+0.68]  | prefers formatted answers        |
| authority | +0.53         | [+0.42,+0.64]  | prefers (even fake) citations    |
| sentiment | +0.40         | [+0.27,+0.53]  | prefers polite tone              |
```
Reading: **0 = fair.** A CI that doesn't cross 0 means the bias is real, not luck.

### Sequence for one pair
```
verdict probe
   │ build controlled pair (same content; A=formatted, B=plain)
   ▼
 compare(q, A, B) ─▶ Judge ─▶ "A"   (formatted, slot 1)
 compare(q, B, A) ─▶ Judge ─▶ "B"   (formatted, slot 2)
   → formatted won both → style bias = +1 for this pair
   │ repeat ×120, average → +0.59, bootstrap → CI [0.49, 0.68]
   ▼ print table
```

### Fix it (built-in mitigations)
```yaml
judge:
  provider: litellm
  model: gpt-4o-mini
  strategy: cot         # judge reasons step-by-step before scoring
  normalize: true       # strip formatting before judging -> kills style bias
```
Re-run `verdict probe`; the style score should drop toward 0.

---

## The whole flow (flowchart)

```
        ┌───────────────────────────────────────────┐
        │ I want to know if my AI outputs are good  │
        └───────────────────┬───────────────────────┘
                            ▼
            write dataset.yaml + config.yaml
                            ▼
                 $ verdict run config.yaml
                            ▼
              scoreboard: pass rate, scores
                            ▼
              used an AI judge?  ── no ──▶ done (rule checks are objective)
                            │ yes
                            ▼
                 $ verdict probe   (or verdict audit)
                            ▼
                  bias table with CIs
              ┌─────────────┴──────────────┐
        biases ~0                      biases real
        trust it                       turn on fixes
                                  (cot / rubric / normalize /
                                   jury / different judge)
                                            ▼
                                   re-run verdict probe
                                            ▼
                                   biases shrink → trust it
                            │
                            ▼
        wire `verdict run --baseline` into CI:
        every prompt change is auto-graded; quality drops block the PR.
```

---

## The regression gate, demonstrated
```
# good change vs saved baseline:
$ verdict run config.concise.yaml --baseline baseline.json
   Overall pass rate: 100%
   No regressions beyond threshold.            exit 0  ✅

# bad change (a worse prompt) vs the same baseline:
$ verdict run config.verbose.yaml --baseline baseline.json
   Overall pass rate: 50%
   Overall pass rate dropped 100% -> 50% (> 5% threshold).
   'length' pass rate dropped 100% -> 0%.      exit 1  🔴  (this blocks a PR)
```
