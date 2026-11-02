"""Adapt immutable MatchLab forward snapshots to the live research screen.

Only goal markets with a stored model disagreement range can be scored.
No retrospective reconstruction of probabilities or model ranges is allowed.
"""
from intelligence_selection import screen_outlook
from forward_multimarket_validation import _settles, _utc
from forward_selection_validation import wilson

def evaluate_live_screen(snapshots, settlements, min_selections=100):
    finals = {}
    for row in settlements:
        key = str(row["provider_match_id"])
        if key in finals:
            raise ValueError("Duplicate final score")
        if row.get("status") != "final":
            continue
        h, a = row["home_goals"], row["away_goals"]
        if any(type(v) is not int or v < 0 for v in (h, a)):
            raise ValueError("Invalid final score")
        finals[key] = (h, a)
    seen = set()
    selected = []
    abstained = pending = 0
    for row in snapshots:
        if row.get("model") != "DC + Bayesian (50/50)":
            continue
        key = str(row["provider_match_id"])
        if key in seen:
            raise ValueError("Duplicate fixture snapshot")
        seen.add(key)
        if _utc(row["captured_at_utc"]) >= _utc(row["kickoff_utc"]):
            raise ValueError("Forecast captured after kickoff")
        if not row.get("model_version"):
            raise ValueError("Missing model version")
        markets = row.get("screen_markets")
        if not isinstance(markets, list):
            raise ValueError("Missing frozen live screen markets; old 1X2-only snapshots cannot be upgraded")
        for item in markets:
            _settles(item["key"], 0, 0)
        decision = screen_outlook(markets)
        if decision["status"] == "ABSTAIN":
            abstained += 1
            continue
        candidate = decision["candidate"]
        if key not in finals:
            pending += 1
            continue
        h, a = finals[key]
        selected.append((candidate["market"], candidate["probability"],
                         int(_settles(candidate["market"], h, a))))
    n = len(selected)
    wins = sum(x[2] for x in selected)
    by_market = {}
    for market in sorted({x[0] for x in selected}):
        rows = [x for x in selected if x[0] == market]
        count = len(rows)
        hit = sum(x[2] for x in rows)
        by_market[market] = {"selections": count, "wins": hit, "hit_rate": hit/count,
                             "wilson_95pct": wilson(hit, count)}
    return {"evaluation": "FORWARD_LIVE_SCREEN_RESEARCH",
            "screen": "intelligence_selection.screen_outlook_default_80pct_10pct_spread",
            "eligible_snapshots": len(seen), "abstained": abstained, "pending": pending,
            "settled_selections": n, "wins": wins, "hit_rate": wins/n if n else None,
            "wilson_95pct": wilson(wins, n), "by_market": by_market,
            "sample_sufficient": n >= min_selections,
            "live_policy_validated": False,
            "limitations": ["Historical snapshots without frozen screen_markets cannot be scored",
                            "Model disagreement ranges must be captured before kickoff",
                            "Only final-score-settleable markets are supported",
                            "No promotion until independent prospective evidence review"]}
