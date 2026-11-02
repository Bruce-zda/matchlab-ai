"""Conservative, deterministic research screening for preview market outlooks.

A candidate is NOT an expert pick until separately calibrated and evaluated
on untouched forward results. Avoid treating correlated markets as independent.
"""
import math


def screen_outlook(markets, scenarios=None, min_probability=.80, max_model_spread=.10):
    if not 0 < min_probability < 1 or not 0 < max_model_spread < 1:
        raise ValueError("Invalid screening thresholds")
    candidates = []
    for item in markets:
        p = item.get("probability")
        rng = item.get("model_range")
        if item.get("conditional") or rng is None:
            continue
        if not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError("Invalid market probability")
        spread = rng.get("spread")
        if not isinstance(spread, (int, float)) or not math.isfinite(spread) or spread < 0:
            raise ValueError("Invalid model disagreement")
        if p < min_probability or spread > max_model_spread:
            continue
        key = item["key"]
        stress = None
        if scenarios and isinstance(scenarios.get("scenarios"), dict):
            vals = [row[key] for row in scenarios["scenarios"].values() if key in row]
            if vals:
                if not all(isinstance(v, (int, float)) and math.isfinite(v) and 0 <= v <= 1 for v in vals):
                    raise ValueError("Invalid scenario probability")
                stress = min(vals)
        candidates.append({"market": key, "probability": p,
                           "model_disagreement": spread,
                           "minimum_hypothetical_scenario_probability": stress})
    candidates.sort(key=lambda x: (-x["probability"], x["model_disagreement"], x["market"]))
    return {
        "status": "RESEARCH_SCREEN_ONLY" if candidates else "ABSTAIN",
        "candidate": candidates[0] if candidates else None,
        "candidates_considered": len(candidates),
        "expert_pick": False,
        "historical_reliability": "NOT_ESTABLISHED_FOR_THIS_SELECTION_POLICY",
        "calibration": "NOT_VERIFIED",
        "note": "80% is an uncalibrated screening threshold, NOT a measured win rate. "
                "Historical out-of-sample and forward testing are required before endorsement."
    }
