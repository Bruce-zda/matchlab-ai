"""Conservative research-stage selection policy for MatchLab markets.

Never interpret a high event probability as betting value. This module
only screens model reliability; it does not make wagering recommendations.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class MarketEvidence:
    market: str
    evaluated_folds: int
    wins_against_club: int
    model_brier: float
    club_brier: float


def assess_market_evidence(evidence, minimum_folds=12, minimum_win_rate=0.60):
    """Return an evidence label, not a profitability or safety claim."""
    if evidence.evaluated_folds < minimum_folds:
        return "INSUFFICIENT_EVIDENCE"
    if not all(math.isfinite(v) and v >= 0 for v in (evidence.model_brier, evidence.club_brier)):
        return "INVALID_EVIDENCE"
    if evidence.wins_against_club < 0 or evidence.wins_against_club > evidence.evaluated_folds:
        return "INVALID_EVIDENCE"
    if evidence.model_brier >= evidence.club_brier:
        return "NO_MODEL_ADVANTAGE"
    if evidence.wins_against_club / evidence.evaluated_folds < minimum_win_rate:
        return "INCONSISTENT_ADVANTAGE"
    return "PRELIMINARY_SUPPORT"


def assess_calibration_gate(report, market="1X", minimum_folds=12, minimum_win_rate=0.70):
    """Only allow a research candidate; final untouched evaluation is mandatory."""
    if report.get("evaluation_type") != "exploratory_rolling_historical_not_untouched":
        return "UNVERIFIED_EVALUATION"
    item = report.get("markets", {}).get(market)
    if not item:
        return "INSUFFICIENT_EVIDENCE"
    try:
        folds = int(item["folds"])
        improved = int(item["improved_folds"])
        raw = float(item["mean_raw_brier"])
        calibrated = float(item["mean_calibrated_brier"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return "INVALID_EVIDENCE"
    if folds < minimum_folds:
        return "INSUFFICIENT_EVIDENCE"
    if improved < 0 or improved > folds or not all(math.isfinite(x) and x >= 0 for x in (raw, calibrated)):
        return "INVALID_EVIDENCE"
    if calibrated >= raw:
        return "NO_CALIBRATION_GAIN"
    if improved / folds < minimum_win_rate:
        return "INCONSISTENT_CALIBRATION_GAIN"
    return "RESEARCH_CANDIDATE_ONLY"


def describe_candidate(probability, evidence_status, odds_available=False):
    """Always abstain from expert endorsement without verified odds and final testing."""
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("Probability must be finite and between 0 and 1")
    if evidence_status != "PRELIMINARY_SUPPORT":
        return "No expert selection — historical support is insufficient."
    if not odds_available:
        return "Model probability only — no verified market odds to assess value."
    return "Research candidate only — independent final validation required."


def rank_model_outlooks(market_probabilities, supported_markets, minimum_probability=0.65,
                        minimum_separation=0.05):
    """Rank descriptive model outlooks, abstaining when evidence is inadequate.

    supported_markets maps market labels to evidence statuses. This is not a
    betting edge, expected return, or expert endorsement.
    """
    candidates = []
    for market, probability in market_probabilities.items():
        if not isinstance(probability, (int, float)) or not math.isfinite(probability):
            raise ValueError("Market probabilities must be finite")
        if not 0 <= probability <= 1:
            raise ValueError("Market probabilities must be in [0, 1]")
        if supported_markets.get(market) != "PRELIMINARY_SUPPORT":
            continue
        if probability >= minimum_probability:
            candidates.append((market, float(probability)))
    candidates.sort(key=lambda pair: (-pair[1], pair[0]))
    if not candidates:
        return {"status": "ABSTAIN", "reason": "No supported market clears the screening threshold.", "ranking": []}
    if len(candidates) > 1 and candidates[0][1] - candidates[1][1] < minimum_separation:
        return {"status": "ABSTAIN", "reason": "Top supported markets are too closely matched.", "ranking": candidates}
    return {"status": "DESCRIPTIVE_OUTLOOK_ONLY",
            "reason": "Probability ranking only; no verified odds or independent final validation.",
            "ranking": candidates}
