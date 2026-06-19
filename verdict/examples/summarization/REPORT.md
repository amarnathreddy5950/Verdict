# Verdict — example report

_Generated fully offline with the deterministic mock provider (`python generate_report.py`). Swap the provider in the configs to reproduce with real models._

## Summarization: concise vs verbose

| Target | Pass rate | length (mean) | faithfulness (mean) | Latency (ms) | Cost ($) |
|---|---|---|---|---|---|
| concise-summarizer | 100% | 1.00 | 0.90 | 12.0 | 0.0000 |
| verbose-summarizer | 50% | 0.00 | 0.50 | 12.0 | 0.0000 |

## Why you must audit the judge

Both judges below score the **same 120 pairs**, each shown in both orders (A,B) and (B,A). The biased judge has a **known injected** position/length bias; verdict's auditor detects it (low swap consistency, skewed first-position win rate) and flags the order-dependent pairs as unreliable. Note the trade-off: swap calibration converts those flagged pairs to ties, so it buys reliability at the cost of coverage rather than magically recovering the right answer. The unbiased judge is the control.

### Biased judge (injected position=0.35, length=0.25)

### Judge bias audit: `biased-judge`

- Pairs evaluated: **120** (each shown in both orders)
- Swap consistency: **55%** (higher is better; 100% = order-independent)
- Position bias rate: **42%** (picked the *first* answer under both orders)
- First-position win rate: **69%** (50% = unbiased)
- Length bias rate: **55%** (chose the longer answer; 50% = unbiased)
- Agreement with humans (Cohen's kappa): raw **0.5029** -> swap-calibrated **0.3446**
- Swap test flagged 45% of pairs as order-dependent (unreliable); swap-calibration marks those as ties.

### Unbiased judge (control)

### Judge bias audit: `unbiased-judge`

- Pairs evaluated: **120** (each shown in both orders)
- Swap consistency: **100%** (higher is better; 100% = order-independent)
- Position bias rate: **0%** (picked the *first* answer under both orders)
- First-position win rate: **50%** (50% = unbiased)
- Length bias rate: **47%** (chose the longer answer; 50% = unbiased)
- Agreement with humans (Cohen's kappa): raw **1.0** -> swap-calibrated **1.0**

## Full bias suite

Order-flipping only catches *position* bias. The suite below probes five biases with controlled pairs (same content, one differing feature) and reports a score in [-1, 1] with a bootstrap 95% CI. See [../../docs/BIASES.md](../../docs/BIASES.md).

### Bias suite: `biased-judge`

| Bias | Score (-1..1) | 95% CI | Tie rate | Reading |
|---|---|---|---|---|
| position | +1.00 | [+1.00, +1.00] | 82% | prefers first position (significant) |
| length | +0.35 | [+0.21, +0.49] | 0% | prefers the length-featured answer (significant) |
| style | +0.59 | [+0.49, +0.68] | 0% | prefers the style-featured answer (significant) |
| authority | +0.53 | [+0.42, +0.64] | 0% | prefers the authority-featured answer (significant) |
| sentiment | +0.40 | [+0.27, +0.53] | 0% | prefers the sentiment-featured answer (significant) |

_Score 0 = unbiased. CI excluding 0 means a statistically detectable bias._

### Bias suite: `unbiased-judge`

| Bias | Score (-1..1) | 95% CI | Tie rate | Reading |
|---|---|---|---|---|
| position | +0.00 | [+0.00, +0.00] | 100% | no significant bias |
| length | +0.18 | [+0.00, +0.37] | 0% | no significant bias |
| style | +0.18 | [+0.00, +0.37] | 0% | no significant bias |
| authority | +0.10 | [-0.08, +0.28] | 0% | no significant bias |
| sentiment | +0.17 | [-0.02, +0.35] | 0% | no significant bias |

_Score 0 = unbiased. CI excluding 0 means a statistically detectable bias._