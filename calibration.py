"""Training-only binary probability calibration utilities.

Experimental: do not fit on evaluation outcomes or use for live forecasts until
a chronological, out-of-sample promotion gate is passed.
"""
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit


def fit_binary_calibrator(probabilities, outcomes, regularization=10.0):
    """Fit a regularized logistic recalibrator on a historical training split only.

    Returns (intercept, slope). Neutral mapping is (0, 1).
    """
    p = np.asarray(probabilities, dtype=float)
    y = np.asarray(outcomes, dtype=float)
    if p.ndim != 1 or y.ndim != 1 or p.shape != y.shape or len(p) < 30:
        raise ValueError("Calibration needs at least 30 paired training observations")
    if not (np.isfinite(p).all() and np.isfinite(y).all()):
        raise ValueError("Calibration inputs must be finite")
    if np.any((p < 0) | (p > 1)) or np.any((y != 0) & (y != 1)):
        raise ValueError("Expected probabilities in [0,1] and binary outcomes")
    if not np.isfinite(regularization) or regularization <= 0:
        raise ValueError("Regularization must be positive")
    if len(np.unique(y)) < 2:
        return 0.0, 1.0  # Abstain from fitting degenerate samples.
    x = logit(np.clip(p, 1e-6, 1 - 1e-6))

    def objective(theta):
        intercept, slope = theta
        z = intercept + slope * x
        loss = np.logaddexp(0, z).sum() - np.dot(y, z)
        return float(loss + regularization * (intercept**2 + (slope - 1)**2))

    result = minimize(objective, np.array([0.0, 1.0]), method="L-BFGS-B",
                      bounds=[(-5, 5), (0, 4)])
    if not result.success or not np.isfinite(result.x).all():
        return 0.0, 1.0
    return float(result.x[0]), float(result.x[1])


def apply_binary_calibrator(probabilities, parameters):
    """Apply frozen training-fitted parameters to held-out probabilities."""
    p = np.asarray(probabilities, dtype=float)
    if not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError("Invalid forecast probabilities")
    intercept, slope = parameters
    return expit(intercept + slope * logit(np.clip(p, 1e-6, 1 - 1e-6)))


def chronological_calibration_report(probabilities, outcomes, train_fraction=0.65):
    """Evaluate a frozen calibrator on a later, disjoint chronological segment.

    Inputs must already be sorted by event time and represent out-of-sample
    predictions from models trained before each event. Do not pass in-sample
    fitted probabilities. This function never modifies the live predictor.
    """
    p = np.asarray(probabilities, dtype=float)
    y = np.asarray(outcomes, dtype=float)
    if p.ndim != 1 or y.ndim != 1 or p.shape != y.shape or len(p) < 60:
        raise ValueError("Need at least 60 chronologically ordered forecast/outcome pairs")
    if not 0.5 <= train_fraction <= 0.8:
        raise ValueError("Training fraction must be between 0.5 and 0.8")
    cut = int(len(p) * train_fraction)
    params = fit_binary_calibrator(p[:cut], y[:cut])
    held_raw = p[cut:]
    held_calibrated = apply_binary_calibrator(held_raw, params)
    held_truth = y[cut:]
    return {
        "calibration_train_n": cut,
        "evaluation_n": len(held_truth),
        "raw_brier": float(np.mean((held_raw - held_truth) ** 2)),
        "calibrated_brier": float(np.mean((held_calibrated - held_truth) ** 2)),
        "parameters": params,
        "calibration_improved": bool(np.mean((held_calibrated - held_truth) ** 2) <
                                     np.mean((held_raw - held_truth) ** 2)),
    }
