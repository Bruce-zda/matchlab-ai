"""Evaluate frozen forward forecasts without selecting on observed outcomes.

Only snapshots captured before kickoff qualify. The research screen is NOT
promoted to a live expert pick by this report.
"""
import math
from statistics import NormalDist

def wilson(successes, n, z=1.959963984540054):
    if n <= 0:
        return None
    p = successes / n
    d = 1 + z*z/n
    center = (p + z*z/(2*n))/d
    margin = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return [max(0.,center-margin),min(1.,center+margin)]

def evaluate_forward_screen(ledger, settlements, threshold=.80, min_selections=100):
    """Evaluate a predeclared 1X2 high-probability screen, not a tuned strategy.

    The full 10–15 market selection policy cannot be assessed from 1X2-only
    archived snapshots; its status remains NOT_VALIDATED.
    """
    if not 0 < threshold < 1 or min_selections < 1:
        raise ValueError("Invalid evaluation policy")
    by_id = {row["snapshot_id"]:row for row in settlements}
    if len(by_id) != len(settlements):
        raise ValueError("Duplicate settlement identifiers")
    candidates = []
    seen = set()
    for row in ledger:
        if row.get("model") != "DC + Bayesian (50/50)":
            continue
        sid = row.get("snapshot_id")
        if sid in seen:
            raise ValueError("Duplicate forecast identifiers")
        seen.add(sid)
        probs = [row.get(k) for k in ("p_home","p_draw","p_away")]
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1 for v in probs):
            raise ValueError("Invalid archived probability")
        if abs(sum(probs)-1)>1e-5:
            raise ValueError("Unnormalized archived probabilities")
        best = max(range(3),key=lambda i:probs[i])
        if probs[best] < threshold:
            continue
        settled = by_id.get(sid)
        if not settled:
            continue
        hg,ag = settled["home_goals"],settled["away_goals"]
        actual = 0 if hg>ag else 1 if hg==ag else 2
        candidates.append((float(probs[best]),int(best==actual)))
    n=len(candidates)
    wins=sum(result for _,result in candidates)
    interval=wilson(wins,n)
    return {
        "policy":"FROZEN_1X2_MAX_PROBABILITY_AT_LEAST_80_PERCENT",
        "scope":"forward_settled_ensemble_1x2_only",
        "threshold":threshold,
        "eligible_settled_selections":n,
        "wins":wins,
        "observed_win_rate":wins/n if n else None,
        "wilson_95pct_interval":interval,
        "mean_predicted_probability":sum(p for p,_ in candidates)/n if n else None,
        "mean_binary_brier":sum((p-y)**2 for p,y in candidates)/n if n else None,
        "promotion_eligible":bool(n>=min_selections and interval and interval[0]>=threshold),
        "full_multimarket_selection_validated":False,
        "note":"Exploratory forward audit only; this report does not validate the newer multimarket selection screen. Selection frequency and confidence intervals matter."
    }
