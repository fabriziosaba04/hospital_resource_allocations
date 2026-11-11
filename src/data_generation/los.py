"""Length-of-stay distribution: discretised (ceiling) lognormal.

Approved interpretation (owner, 2026-11-11):
- sigma is fixed by the coefficient of variation of the *continuous* lognormal: sigma^2 = ln(1 + CV^2);
- mu is solved numerically so that the mean of ceil(X) equals the approved discrete mean exactly.
"""

from __future__ import annotations

import math

_SQRT2 = math.sqrt(2.0)


def lognormal_sigma(cv: float) -> float:
    return math.sqrt(math.log1p(cv * cv))


def _cdf(x: float, mu: float, sigma: float) -> float:
    """P(X <= x) for X ~ lognormal(mu, sigma)."""
    if x <= 0:
        return 0.0
    return 0.5 * math.erfc(-(math.log(x) - mu) / (sigma * _SQRT2))


def ceil_pmf(mu: float, sigma: float, tol: float = 1e-15, k_max: int = 100_000) -> list[float]:
    """pmf[k-1] = P(ceil(X) = k) = F(k) - F(k-1), for k = 1, 2, ... until the tail is below tol."""
    pmf: list[float] = []
    prev = 0.0
    for k in range(1, k_max + 1):
        cur = _cdf(k, mu, sigma)
        pmf.append(cur - prev)
        prev = cur
        if 1.0 - cur < tol and k > math.exp(mu):
            break
    return pmf


def ceil_moments(mu: float, sigma: float) -> tuple[float, float]:
    """Mean and coefficient of variation of ceil(X)."""
    pmf = ceil_pmf(mu, sigma)
    mean = sum(k * p for k, p in enumerate(pmf, start=1))
    second = sum(k * k * p for k, p in enumerate(pmf, start=1))
    var = max(second - mean * mean, 0.0)
    return mean, math.sqrt(var) / mean


def calibrate_mu(target_mean: float, sigma: float, iters: int = 200) -> float:
    """Solve E[ceil(X)] = target_mean for mu by bisection (E[ceil X] is increasing in mu)."""
    if target_mean <= 1.0:
        raise ValueError("discrete mean must exceed 1, since ceil(X) >= 1")
    lo, hi = -20.0, math.log(target_mean) + 1.0
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if ceil_moments(mid, sigma)[0] < target_mean:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def calibrate(cv: float, discrete_means: dict[int, float]) -> dict:
    """Return sigma, mu per level and the resulting theoretical discrete mean and CV per level."""
    sigma = lognormal_sigma(cv)
    out = {"sigma": sigma, "mu": {}, "discrete_mean": {}, "discrete_cv": {}}
    for level, target in sorted(discrete_means.items()):
        mu = calibrate_mu(float(target), sigma)
        mean, dcv = ceil_moments(mu, sigma)
        out["mu"][level] = mu
        out["discrete_mean"][level] = mean
        out["discrete_cv"][level] = dcv
    return out
