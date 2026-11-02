"""Reproducible score-grid stress tests and Monte Carlo sampling.

Stress tests are hypothetical, not verified team news or calibrated forecasts.
"""
import numpy as np


def simulate_score_grid(grid, samples=20000, seed=20261102):
    g = np.asarray(grid, dtype=float)
    if g.ndim != 2 or not np.isfinite(g).all() or (g < 0).any() or g.sum() <= 0:
        raise ValueError("Invalid score grid")
    if not isinstance(samples, int) or not 1000 <= samples <= 100000:
        raise ValueError("Samples outside safe bounds")
    g = g / g.sum()
    rng = np.random.default_rng(seed)
    indices = rng.choice(g.size, size=samples, p=g.ravel())
    home, away = np.unravel_index(indices, g.shape)
    analytical = {"home_win": float(np.tril(g, -1).sum()),
                  "draw": float(np.trace(g)),
                  "away_win": float(np.triu(g, 1).sum())}
    empirical = {"home_win": float(np.mean(home > away)),
                 "draw": float(np.mean(home == away)),
                 "away_win": float(np.mean(home < away))}
    return {"samples": samples, "seed": seed, "analytical": analytical,
            "simulated": empirical, "monte_carlo_sampling_error_only": True}


def stress_expected_goals(home_lambda, away_lambda, rho=0.0, max_goals=12):
    """Change scoring intensities under explicit hypothetical conditions."""
    from scipy.stats import poisson
    if not all(np.isfinite(v) for v in (home_lambda, away_lambda, rho)):
        raise ValueError("Nonfinite parameters")
    if min(home_lambda, away_lambda) <= 0 or abs(rho) > .15:
        raise ValueError("Invalid goal intensity or dependence")
    scenarios = {"baseline": (1., 1.),
                 "home_attack_minus_15pct": (.85, 1.),
                 "away_attack_minus_15pct": (1., .85),
                 "higher_tempo_plus_15pct": (1.15, 1.15),
                 "lower_tempo_minus_15pct": (.85, .85)}
    out = {}
    for name, (hf, af) in scenarios.items():
        lam, mu = home_lambda * hf, away_lambda * af
        goals = np.arange(max_goals + 1)
        g = np.outer(poisson.pmf(goals, lam), poisson.pmf(goals, mu))
        g[0, 0] *= 1 - lam * mu * rho
        g[0, 1] *= 1 + lam * rho
        g[1, 0] *= 1 + mu * rho
        g[1, 1] *= 1 - rho
        if (g < 0).any() or g.sum() <= 0:
            raise ValueError("Stress scenario creates invalid probability mass")
        g /= g.sum()
        out[name] = {"home_win": float(np.tril(g, -1).sum()),
                     "draw": float(np.trace(g)),
                     "away_win": float(np.triu(g, 1).sum()),
                     "over_2_5": float(sum(g[i, j] for i, j in np.ndindex(g.shape) if i + j >= 3))}
    return {"status": "HYPOTHETICAL_UNCALIBRATED_STRESS_TEST",
            "assumptions": "Goal intensities varied by 15%; not injury or tactical claims",
            "scenarios": out}
