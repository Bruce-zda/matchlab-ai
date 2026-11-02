"""Forward-only multimarket audit. Research reporting; never a betting endorsement.

Input: immutable pre-kickoff snapshots with market_probabilities, and independently
recorded final scores. The evaluator never recalculates picks from outcomes.
"""
import datetime as dt
import math
from collections import defaultdict
from forward_selection_validation import wilson
from selection_policy import rank_model_outlooks

def _utc(value):
    if not isinstance(value, str):
        raise ValueError("Missing timestamp")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include timezone")
    return parsed.astimezone(dt.timezone.utc)

def _settles(market, home, away):
    if market == "btts_yes": return home > 0 and away > 0
    if market == "btts_no": return home == 0 or away == 0
    if market in ("home_win", "draw", "away_win"):
        return {"home_win": home > away, "draw": home == away, "away_win": home < away}[market]
    if market in ("1x", "x2", "12"):
        return {"1x": home >= away, "x2": away >= home, "12": home != away}[market]
    parts = market.split("_")
    if len(parts) >= 3 and parts[-2:] in (["0", "5"], ["1", "5"], ["2", "5"], ["3", "5"]):
        threshold = float(parts[-2] + "." + parts[-1])
        prefix = parts[:-2]
        if prefix in (["over"], ["under"]): goals = home + away; direction = prefix[0]
        elif prefix in (["home", "over"], ["home", "under"]): goals = home; direction = prefix[1]
        elif prefix in (["away", "over"], ["away", "under"]): goals = away; direction = prefix[1]
        else: raise ValueError("Unsupported market: " + market)
        return goals > threshold if direction == "over" else goals < threshold
    raise ValueError("Unsupported market: " + market)

def evaluate_forward_multimarket(snapshots, settlements, supported_markets,
                                 minimum_probability=0.65, minimum_separation=0.05,
                                 min_selections=100):
    """One frozen selection per fixture; unresolved fixtures are not scored.

    Snapshots must contain fixture_id, captured_at_utc, kickoff_utc,
    model_version, market_probabilities. Settlement must contain fixture_id,
    home_goals, away_goals, status='final'. All selection criteria are fixed
    before observing scores. The caller must maintain append-only evidence.
    """
    if not 0 < minimum_probability < 1 or not 0 <= minimum_separation < 1 or min_selections < 1:
        raise ValueError("Invalid prespecified policy")
    finals = {}
    for row in settlements:
        fid = str(row["fixture_id"])
        if fid in finals: raise ValueError("Duplicate settlement")
        if row.get("status") != "final": continue
        h, a = row["home_goals"], row["away_goals"]
        if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in (h, a)):
            raise ValueError("Invalid final score")
        finals[fid] = (h, a)
    seen = set()
    chosen = []
    abstained = 0
    pending = 0
    for row in snapshots:
        fid = str(row["fixture_id"])
        if fid in seen: raise ValueError("Duplicate pre-match fixture snapshot")
        seen.add(fid)
        if _utc(row["captured_at_utc"]) >= _utc(row["kickoff_utc"]):
            raise ValueError("Post-kickoff snapshot is not forward evidence")
        if not row.get("model_version"): raise ValueError("Missing model version")
        probs = row["market_probabilities"]
        if not isinstance(probs, dict) or not probs: raise ValueError("Missing market probabilities")
        for market, p in probs.items():
            if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1:
                raise ValueError("Invalid probability for " + market)
            _settles(market, 0, 0)  # Reject unsupported markets before scoring.
        decision = rank_model_outlooks(probs, supported_markets, minimum_probability, minimum_separation)
        if decision["status"] != "DESCRIPTIVE_OUTLOOK_ONLY":
            abstained += 1
            continue
        market, probability = decision["ranking"][0]
        if fid not in finals:
            pending += 1
            continue
        h, a = finals[fid]
        chosen.append({"fixture_id": fid, "market": market, "probability": probability,
                       "won": bool(_settles(market, h, a))})
    per_market = defaultdict(list)
    for row in chosen: per_market[row["market"]].append(row)
    def metrics(rows):
        n = len(rows)
        wins = sum(r["won"] for r in rows)
        return {"selections": n, "wins": wins, "hit_rate": wins/n if n else None,
                "wilson_95pct": wilson(wins, n),
                "mean_probability": sum(r["probability"] for r in rows)/n if n else None,
                "binary_brier": sum((r["probability"]-int(r["won"]))**2 for r in rows)/n if n else None}
    summary = metrics(chosen)
    return {"evaluation": "FORWARD_MULTIMARKET_RESEARCH_NOT_LIVE_ENDORSEMENT",
            "policy": {"minimum_probability": minimum_probability, "minimum_separation": minimum_separation,
                       "supported_markets": supported_markets, "min_selections": min_selections},
            "snapshots": len(seen), "abstained": abstained, "pending": pending,
            "overall": summary, "by_market": {k: metrics(v) for k, v in sorted(per_market.items())},
            "research_sample_sufficient": summary["selections"] >= min_selections,
            "live_accuracy_validated": False,
            "limitations": ["Requires independently archived immutable pre-kickoff snapshots",
                            "Only markets with supported settlement rules are evaluated",
                            "Accuracy alone does not establish value or profitability",
                            "Full live policy equivalence must be independently verified"]}
