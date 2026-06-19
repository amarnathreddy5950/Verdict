from verdict.judge import SyntheticBiasedJudge, run_bias_suite
from verdict.judge.probes import (
    authority_pairs,
    default_base_answers,
    length_pairs,
    position_pairs,
    run_probe,
    sentiment_pairs,
    style_pairs,
)

BASE = default_base_answers(60)


def test_clean_judge_shows_little_bias():
    judge = SyntheticBiasedJudge(seed=1, name="clean")
    for gen in (length_pairs, style_pairs, authority_pairs, sentiment_pairs):
        res = run_probe(judge, gen(BASE))
        assert abs(res.bias_score) < 0.35, f"{res.bias_type}: {res.bias_score}"
    # identical-answer position probe should be all ties -> zero signal
    pos = run_probe(judge, position_pairs(BASE))
    assert pos.bias_score == 0.0


def test_style_bias_detected():
    res = run_probe(SyntheticBiasedJudge(style_bias=0.8, seed=2), style_pairs(BASE))
    assert res.bias_score > 0.3 and res.ci_low > 0


def test_length_bias_detected():
    res = run_probe(SyntheticBiasedJudge(length_bias=0.8, seed=2), length_pairs(BASE))
    assert res.bias_score > 0.3 and res.ci_low > 0


def test_authority_bias_detected():
    res = run_probe(SyntheticBiasedJudge(authority_bias=0.8, seed=2), authority_pairs(BASE))
    assert res.bias_score > 0.3 and res.ci_low > 0


def test_sentiment_bias_detected():
    res = run_probe(SyntheticBiasedJudge(sentiment_bias=0.8, seed=2), sentiment_pairs(BASE))
    assert res.bias_score > 0.3 and res.ci_low > 0


def test_position_bias_detected():
    res = run_probe(SyntheticBiasedJudge(position_bias=0.6, seed=2), position_pairs(BASE))
    assert res.bias_score > 0.3 and res.ci_low > 0


def test_suite_has_all_probes():
    suite = run_bias_suite(SyntheticBiasedJudge(style_bias=0.5, seed=3))
    assert {p.bias_type for p in suite.probes} == {
        "position",
        "length",
        "style",
        "authority",
        "sentiment",
    }
    assert "Bias suite" in suite.to_markdown()
