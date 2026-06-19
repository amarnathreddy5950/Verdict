from verdict.stats import bootstrap_ci, mean_ci


def test_bootstrap_ci_constant():
    assert bootstrap_ci([0.5] * 20) == (0.5, 0.5)


def test_bootstrap_ci_brackets_mean():
    point, lo, hi = mean_ci([0, 1] * 50)
    assert lo <= point <= hi
    assert 0.3 < point < 0.7


def test_bootstrap_ci_empty():
    assert bootstrap_ci([]) == (0.0, 0.0)
