from verdict.judge import JuryJudge, self_preference_warning
from verdict.judge.base import PairwiseJudge, Verdict


class _Const(PairwiseJudge):
    def __init__(self, verdict: Verdict, name: str = "const") -> None:
        self._v = verdict
        self.name = name

    def compare(self, question: str, answer_a: str, answer_b: str) -> Verdict:
        return self._v


def test_jury_majority_vote():
    jury = JuryJudge([_Const("A"), _Const("A"), _Const("B")])
    assert jury.compare("q", "a", "b") == "A"


def test_jury_split_is_tie():
    jury = JuryJudge([_Const("A"), _Const("B")])
    assert jury.compare("q", "a", "b") == "tie"


def test_self_preference_warning():
    assert self_preference_warning("gpt-4o", "gpt-4o") is not None
    assert self_preference_warning("gpt-4o", "claude-3-5-sonnet") is None
