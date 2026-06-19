"""Controlled bias probes for LLM judges.

Idea (from the LLM-as-judge bias literature): build pairs that should be a **tie**
because the two answers carry the *same content* and differ only along one axis
(formatting, length, a citation, tone, or merely position). Show each pair in both
orders, and measure how often the judge prefers the answer carrying the
"bias-inducing feature". A fair judge sits near 0.

Bias score = 2 * P(prefers feature answer | non-tie) - 1, in [-1, 1]:
  0  -> unbiased,  +1 -> always prefers the feature,  -1 -> always avoids it.
We report a bootstrap 95% CI so noise is visible.

References: Zheng et al. 2024 (position); Saito et al. 2023, Dubois et al. 2024
(length); Wu & Aji 2024, Soumik 2026 (style dominates); Chen et al. 2024,
Gao et al. 2026 (authority/sentiment taxonomy).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from verdict.judge.base import PairwiseJudge
from verdict.stats import bootstrap_ci

BiasType = str  # "position" | "length" | "style" | "authority" | "sentiment"


class ControlledPair(BaseModel):
    id: str
    question: str
    answer_a: str  # carries the bias-inducing feature (except for 'position', where a == b)
    answer_b: str
    bias_type: BiasType


class BiasProbeResult(BaseModel):
    bias_type: BiasType
    n: int
    bias_score: float
    ci_low: float
    ci_high: float
    feature_or_first_rate: float
    tie_rate: float
    interpretation: str

    def to_markdown_row(self) -> str:
        return (
            f"| {self.bias_type} | {self.bias_score:+.2f} "
            f"| [{self.ci_low:+.2f}, {self.ci_high:+.2f}] "
            f"| {self.tie_rate:.0%} | {self.interpretation} |"
        )


# --------------------------------------------------------------------------- #
# Pair generators                                                             #
# --------------------------------------------------------------------------- #
def default_base_answers(n: int = 120) -> list[tuple[str, str]]:
    """Plain-prose (question, answer) seeds with no markdown/citations/politeness."""
    out: list[tuple[str, str]] = []
    for i in range(n):
        q = f"Q{i}: explain concept number {i} in one line."
        a = f"Concept {i} is a simple idea that connects input {i} to outcome {i} clearly."
        out.append((q, a))
    return out


def _pairs(bias_type: BiasType, make_a, base: list[tuple[str, str]]) -> list[ControlledPair]:
    pairs: list[ControlledPair] = []
    for i, (q, ans) in enumerate(base):
        pairs.append(
            ControlledPair(
                id=f"{bias_type}-{i}",
                question=q,
                answer_a=make_a(ans),
                answer_b=ans,
                bias_type=bias_type,
            )
        )
    return pairs


def position_pairs(base: list[tuple[str, str]]) -> list[ControlledPair]:
    """Identical answers in both slots; any non-tie reveals position preference."""
    return _pairs("position", lambda ans: ans, base)


def length_pairs(base: list[tuple[str, str]]) -> list[ControlledPair]:
    filler = " It is worth restating this point with additional words for emphasis here."
    return _pairs("length", lambda ans: ans + filler * 2, base)


def style_pairs(base: list[tuple[str, str]]) -> list[ControlledPair]:
    return _pairs("style", lambda ans: f"**Answer:**\n- {ans}\n- `key point`", base)


def authority_pairs(base: list[tuple[str, str]]) -> list[ControlledPair]:
    return _pairs("authority", lambda ans: f"{ans} According to Smith et al. (2020) [1].", base)


def sentiment_pairs(base: list[tuple[str, str]]) -> list[ControlledPair]:
    return _pairs(
        "sentiment", lambda ans: f"I'd be happy to help! {ans} Thank you for asking!", base
    )


# --------------------------------------------------------------------------- #
# Probe runner                                                                #
# --------------------------------------------------------------------------- #
def run_probe(judge: PairwiseJudge, pairs: list[ControlledPair]) -> BiasProbeResult:
    """Run one bias probe (all pairs must share a bias_type)."""
    bias_type = pairs[0].bias_type if pairs else "unknown"
    is_position = bias_type == "position"

    per_pair_scores: list[float] = []  # in [-1, 1], for bootstrapping
    ties = 0
    presentations = 0

    for pair in pairs:
        r1 = judge.compare(pair.question, pair.answer_a, pair.answer_b)  # feature in slot A
        r2 = judge.compare(pair.question, pair.answer_b, pair.answer_a)  # feature in slot B
        hits = 0  # times the (feature answer | first position) was chosen
        non_tie = 0
        for result, feature_is_first in ((r1, True), (r2, False)):
            presentations += 1
            if result == "tie":
                ties += 1
                continue
            non_tie += 1
            picked_first = result == "A"
            if is_position:
                chose_target = picked_first
            else:
                # feature answer chosen if it was picked in whichever slot it sat
                chose_target = picked_first if feature_is_first else (not picked_first)
            if chose_target:
                hits += 1
        if non_tie:
            per_pair_scores.append(2.0 * (hits / non_tie) - 1.0)

    bias_score = round(sum(per_pair_scores) / len(per_pair_scores), 4) if per_pair_scores else 0.0
    ci_low, ci_high = bootstrap_ci(per_pair_scores) if per_pair_scores else (0.0, 0.0)
    feature_rate = round((bias_score + 1) / 2, 4)
    tie_rate = round(ties / presentations, 4) if presentations else 0.0

    target = "first position" if is_position else f"the {bias_type}-featured answer"
    if ci_low > 0:
        interp = f"prefers {target} (significant)"
    elif ci_high < 0:
        interp = f"avoids {target} (significant)"
    else:
        interp = "no significant bias"

    return BiasProbeResult(
        bias_type=bias_type,
        n=len(pairs),
        bias_score=bias_score,
        ci_low=ci_low,
        ci_high=ci_high,
        feature_or_first_rate=feature_rate,
        tie_rate=tie_rate,
        interpretation=interp,
    )


_GENERATORS = {
    "position": position_pairs,
    "length": length_pairs,
    "style": style_pairs,
    "authority": authority_pairs,
    "sentiment": sentiment_pairs,
}


class BiasSuiteResult(BaseModel):
    judge: str
    probes: list[BiasProbeResult] = Field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            f"### Bias suite: `{self.judge}`",
            "",
            "| Bias | Score (-1..1) | 95% CI | Tie rate | Reading |",
            "|---|---|---|---|---|",
            *[p.to_markdown_row() for p in self.probes],
            "",
            "_Score 0 = unbiased. CI excluding 0 means a statistically detectable bias._",
        ]
        return "\n".join(lines)


def run_bias_suite(
    judge: PairwiseJudge,
    base: list[tuple[str, str]] | None = None,
    bias_types: list[BiasType] | None = None,
) -> BiasSuiteResult:
    """Run all (or selected) bias probes against a judge and collect the results."""
    base = base or default_base_answers()
    bias_types = bias_types or list(_GENERATORS)
    probes = [run_probe(judge, _GENERATORS[bt](base)) for bt in bias_types]
    return BiasSuiteResult(judge=judge.name, probes=probes)
