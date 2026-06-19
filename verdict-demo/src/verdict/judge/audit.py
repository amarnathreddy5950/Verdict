"""The differentiator: audit an LLM judge for bias, then calibrate it.

Judges have well-documented, systematic biases:
  * position bias  - the first-shown answer wins more than chance
  * length bias    - longer answers win regardless of quality

We measure these with a **swap test** (show each pair as (A,B) and (B,A)) and report:
  * swap_consistency      - how often the judge picks the same answer under both orders
  * position_bias_rate    - how often it picks the first position under *both* orders
  * length_bias_rate      - how often it picks the longer answer
  * agreement with humans  (Cohen's kappa), raw vs swap-calibrated

Swap calibration keeps a verdict only when both orderings agree, otherwise 'tie'.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, Field

from verdict.judge.base import PairwiseJudge, Verdict


class PairCase(BaseModel):
    id: str
    question: str
    answer_a: str
    answer_b: str
    human_winner: Verdict | None = None  # optional gold label from humans


def cohen_kappa(rater_a: Sequence[str], rater_b: Sequence[str]) -> float:
    """Cohen's kappa for two raters over categorical labels."""
    if not rater_a or len(rater_a) != len(rater_b):
        return 0.0
    n = len(rater_a)
    labels = set(rater_a) | set(rater_b)
    po = sum(1 for x, y in zip(rater_a, rater_b, strict=False) if x == y) / n
    pe = 0.0
    for label in labels:
        pa = sum(1 for x in rater_a if x == label) / n
        pb = sum(1 for y in rater_b if y == label) / n
        pe += pa * pb
    if pe >= 1.0:
        return 0.0
    return round((po - pe) / (1.0 - pe), 4)


class AuditReport(BaseModel):
    judge: str
    n: int
    swap_consistency: float
    position_bias_rate: float
    first_position_win_rate: float
    length_bias_rate: float
    raw_human_kappa: float | None = None
    calibrated_human_kappa: float | None = None
    notes: list[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            f"### Judge bias audit: `{self.judge}`",
            "",
            f"- Pairs evaluated: **{self.n}** (each shown in both orders)",
            f"- Swap consistency: **{self.swap_consistency:.0%}** "
            "(higher is better; 100% = order-independent)",
            f"- Position bias rate: **{self.position_bias_rate:.0%}** "
            "(picked the *first* answer under both orders)",
            f"- First-position win rate: **{self.first_position_win_rate:.0%}** "
            "(50% = unbiased)",
            f"- Length bias rate: **{self.length_bias_rate:.0%}** "
            "(chose the longer answer; 50% = unbiased)",
        ]
        if self.raw_human_kappa is not None:
            lines.append(
                f"- Agreement with humans (Cohen's kappa): raw **{self.raw_human_kappa}** "
                f"-> swap-calibrated **{self.calibrated_human_kappa}**"
            )
        for note in self.notes:
            lines.append(f"- {note}")
        return "\n".join(lines)


class JudgeAuditor:
    """Runs the swap test and computes bias metrics + a swap-calibrated verdict."""

    def _swap(self, judge: PairwiseJudge, pair: PairCase) -> tuple[Verdict, Verdict]:
        r1 = judge.compare(pair.question, pair.answer_a, pair.answer_b)
        r2 = judge.compare(pair.question, pair.answer_b, pair.answer_a)
        return r1, r2

    @staticmethod
    def _actual(result: Verdict, swapped: bool) -> Verdict:
        """Map a positional verdict to the actual answer ('A'==answer_a)."""
        if result == "tie":
            return "tie"
        if not swapped:
            return result
        return "A" if result == "B" else "B"

    def calibrated_verdicts(
        self, judge: PairwiseJudge, pairs: list[PairCase]
    ) -> list[Verdict]:
        out: list[Verdict] = []
        for pair in pairs:
            r1, r2 = self._swap(judge, pair)
            a1, a2 = self._actual(r1, False), self._actual(r2, True)
            out.append(a1 if a1 == a2 else "tie")
        return out

    def audit(self, judge: PairwiseJudge, pairs: list[PairCase]) -> AuditReport:
        n = len(pairs)
        consistent = 0
        both_first = 0
        first_wins = 0
        non_tie_presentations = 0
        longer_chosen = 0
        length_diff_presentations = 0

        raw_actuals: list[Verdict] = []
        calibrated: list[Verdict] = []
        humans: list[Verdict] = []

        for pair in pairs:
            r1, r2 = self._swap(judge, pair)
            a1, a2 = self._actual(r1, False), self._actual(r2, True)

            if a1 == a2:
                consistent += 1
            if r1 == "A" and r2 == "A":
                both_first += 1

            la, lb = len(pair.answer_a), len(pair.answer_b)
            for result, first_text, second_text in (
                (r1, pair.answer_a, pair.answer_b),
                (r2, pair.answer_b, pair.answer_a),
            ):
                if result == "tie":
                    continue
                non_tie_presentations += 1
                if result == "A":
                    first_wins += 1
                if la != lb:
                    length_diff_presentations += 1
                    chosen_text = first_text if result == "A" else second_text
                    other_text = second_text if result == "A" else first_text
                    if len(chosen_text) > len(other_text):
                        longer_chosen += 1

            raw_actuals.append(a1)
            calibrated.append(a1 if a1 == a2 else "tie")
            if pair.human_winner is not None:
                humans.append(pair.human_winner)

        raw_kappa = calib_kappa = None
        notes: list[str] = []
        order_dependent = round(1.0 - consistent / n, 4) if n else 0.0
        if order_dependent > 0:
            notes.append(
                f"Swap test flagged {order_dependent:.0%} of pairs as order-dependent "
                "(unreliable); swap-calibration marks those as ties."
            )
        if len(humans) == n and n > 0:
            raw_kappa = cohen_kappa(raw_actuals, humans)
            calib_kappa = cohen_kappa(calibrated, humans)

        return AuditReport(
            judge=judge.name,
            n=n,
            swap_consistency=round(consistent / n, 4) if n else 0.0,
            position_bias_rate=round(both_first / n, 4) if n else 0.0,
            first_position_win_rate=(
                round(first_wins / non_tie_presentations, 4)
                if non_tie_presentations
                else 0.0
            ),
            length_bias_rate=(
                round(longer_chosen / length_diff_presentations, 4)
                if length_diff_presentations
                else 0.0
            ),
            raw_human_kappa=raw_kappa,
            calibrated_human_kappa=calib_kappa,
            notes=notes,
        )
