from verdict.cli import _demo_pairs
from verdict.judge import JudgeAuditor, SyntheticBiasedJudge, cohen_kappa


def test_cohen_kappa_perfect_and_chance():
    assert cohen_kappa(["A", "B", "A"], ["A", "B", "A"]) == 1.0
    # identical single-category -> no agreement beyond chance
    assert cohen_kappa(["A", "A"], ["A", "A"]) == 0.0


def test_auditor_detects_position_bias():
    pairs = _demo_pairs(150)
    auditor = JudgeAuditor()
    biased = auditor.audit(SyntheticBiasedJudge(position_bias=0.5, seed=1), pairs)
    clean = auditor.audit(SyntheticBiasedJudge(seed=1), pairs)

    # An unbiased judge is perfectly swap-consistent; a biased one is not.
    assert clean.swap_consistency == 1.0
    assert biased.swap_consistency < clean.swap_consistency
    # Position bias surfaces as picking the first option under both orders.
    assert biased.position_bias_rate > 0.15
    assert biased.first_position_win_rate > 0.5


def test_auditor_detects_length_bias():
    pairs = _demo_pairs(150)
    auditor = JudgeAuditor()
    biased = auditor.audit(SyntheticBiasedJudge(length_bias=0.8, seed=2), pairs)
    assert biased.length_bias_rate > 0.55


def test_bias_lowers_human_agreement_and_audit_flags_it():
    pairs = _demo_pairs(150)
    auditor = JudgeAuditor()
    biased = auditor.audit(SyntheticBiasedJudge(position_bias=0.4, seed=3, name="biased"), pairs)
    clean = auditor.audit(SyntheticBiasedJudge(seed=3, name="clean"), pairs)

    assert clean.raw_human_kappa is not None and biased.raw_human_kappa is not None
    # The unbiased judge matches the (content-based) human labels perfectly.
    assert clean.raw_human_kappa == 1.0
    # Injected bias measurably reduces agreement with humans, and the swap test flags it.
    assert biased.raw_human_kappa < clean.raw_human_kappa
    assert biased.swap_consistency < clean.swap_consistency
