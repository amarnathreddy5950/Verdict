"""Small statistics helpers (pure stdlib, no numpy).

Why this exists: research on LLM judges stresses that raw judge numbers are noisy
and a biased estimator, so any reported metric should carry uncertainty. We use a
simple nonparametric **bootstrap** to put confidence intervals on rates/scores.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from statistics import mean


def bootstrap_ci(
    values: Sequence[float],
    statistic: Callable[[Sequence[float]], float] = mean,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float]:
    """Return a (low, high) bootstrap confidence interval for ``statistic(values)``.

    Parameters
    ----------
    values    : sample observations (e.g., per-item 0/1 outcomes).
    statistic : aggregate to bootstrap (default: mean).
    n_boot    : number of resamples.
    alpha     : 1 - confidence (0.05 -> 95% CI).
    seed      : RNG seed for reproducibility.
    """
    vals = list(values)
    if not vals:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(vals)
    estimates: list[float] = []
    for _ in range(n_boot):
        sample = [vals[rng.randrange(n)] for _ in range(n)]
        estimates.append(statistic(sample))
    estimates.sort()
    lo_idx = int((alpha / 2) * n_boot)
    hi_idx = min(n_boot - 1, int((1 - alpha / 2) * n_boot))
    return (round(estimates[lo_idx], 4), round(estimates[hi_idx], 4))


def mean_ci(values: Sequence[float], **kwargs: object) -> tuple[float, float, float]:
    """Convenience: return (mean, ci_low, ci_high)."""
    vals = list(values)
    point = round(mean(vals), 4) if vals else 0.0
    lo, hi = bootstrap_ci(vals, **kwargs)  # type: ignore[arg-type]
    return point, lo, hi
