# Judge biases: taxonomy, what verdict does, and how to counter them

LLM "judges" are convenient but **not neutral**. They prefer answers for reasons unrelated
to quality. Swapping answer order only addresses *one* bias (position). This document is the
map verdict is built around.

> Key 2026 finding: on modern frontier models, **position bias is now small (≤0.04)** while
> **style/format bias dominates (0.76–0.92)** yet is rarely audited. So order-flipping alone
> is no longer enough. (Soumik 2026.)

## The taxonomy

### Style / presentation biases (implicit)
| Bias | What it is | verdict probe | Mitigation |
|---|---|---|---|
| **Style/format** | Prefers Markdown/formatting even with identical content. *Dominant today.* | `style` | Normalize formatting; CoT; rubric |
| **Length/verbosity** | Prefers longer answers (nuanced: modern judges often penalize filler but reward genuine completeness) | `length` | Rubric; length-controlled scoring |
| **Rich content / elaboration** | Rewards extra detail/examples regardless of need | (style/length) | Rubric |
| **Chain-of-thought style** | Scores differ based on whether reasoning is shown | — | Rubric |
| **Sentiment / tone** | Rewards polite/positive phrasing | `sentiment` | CoT; "ignore tone" instruction |

### Content / social biases (explicit)
| Bias | What it is | verdict support | Mitigation |
|---|---|---|---|
| **Position / order** | Prefers the first-shown answer | `position` probe + swap audit | Swap calibration (context-dependent) |
| **Self-preference** | Favors the judge's *own* outputs / familiar text | `self_preference_warning` guardrail | Use a different judge than the model under test |
| **Authority / citation** | Rewards references, even fabricated | `authority` | CoT; instruct to verify, not trust, citations |
| **Factual-error insensitivity** | Confident-but-wrong slips through | — (use reference-guided judging) | Reference answers; rubric on accuracy |
| **Bandwagon / popularity** | Favors "most people think X" | — | CoT; remove popularity cues |
| **Distraction** | Impressed by irrelevant detail | — | Rubric on relevance |
| **Provenance / source** | Favors answers labeled from an "expert"/known model | — | Blind the source labels |
| **Recency** | Favors answers framed as "new" | — | Remove temporal framing |
| **Demographic / gender** | Scoring shifts on identity cues | — | Instruct to disregard identity; audit |

## What verdict measures

`verdict probe` runs **controlled pairs** that should be a tie (same content, differing only
along one axis) in both orders, and reports a **bias score in [-1, 1]** with a bootstrap 95% CI:

- `0` = unbiased; a CI that excludes 0 means a statistically detectable bias.
- Covered probes: **position, length, style, authority, sentiment**.

`verdict`'s swap auditor (`JudgeAuditor`) additionally reports swap consistency, first-position
win rate, and human agreement (Cohen's kappa) on arbitrary pairs.

## Mitigations verdict ships (and what the research says works)

| Mitigation | In verdict | Evidence |
|---|---|---|
| **Chain-of-thought judging** | `LLMPairwiseJudge(strategy="cot")` | Safest, most universally positive; best style-bias reduction (Soumik 2026) |
| **Calibrated rubric** | `strategy="rubric"` | Neutral-to-positive; best verbosity-bias reduction |
| **Format normalization** | `normalize=True` / `strip_formatting` | Direct fix for the dominant style bias |
| **Swap calibration** | `JudgeAuditor` | Helps for position-sensitive judges; can hurt on clear-cut cases — context-dependent |
| **Multi-judge jury** | `JuryJudge` | Diverse panels dilute individual bias (Verga et al. 2024) |
| **Avoid self-judging** | `self_preference_warning` | Simplest fix for self-preference (Panickssery et al. 2024) |
| **Uncertainty reporting** | bootstrap CIs everywhere | Raw judge numbers are a biased, noisy estimator |

### Practical defaults
- Unknown context: **CoT** (1× cost, universally positive).
- Comparing models with different formatting: **normalize formatting** before judging.
- High stakes: **jury** of diverse judges + human spot-checks.
- Never let a model judge its own outputs.

## References
- Zheng et al. 2024, *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena* (position, verbosity, self-enhancement).
- Saito et al. 2023; Dubois et al. 2024 (verbosity / length-controlled win rates).
- Wu & Aji 2024, *Style over Substance* (style bias).
- Panickssery et al. 2024 (self-preference: judges recognize and favor their own generations).
- Verga et al. 2024 (panel of LLM judges).
- Soumik 2026, *Judging the Judges* (systematic mitigation comparison; style dominates, position now small).
- Gao et al. 2026 (11-bias taxonomy in pointwise judging).
