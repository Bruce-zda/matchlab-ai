"""Evaluate pre-result chronological goal-market predictions and a fixed screen.

Exploratory folds were previously inspected; results cannot certify an
untouched validation set or future 80% success.
"""
import math
from collections import defaultdict
from forward_selection_validation import wilson


def evaluate_historical_markets(rows, threshold=.80, min_selections=100):
    if not 0 < threshold < 1 or min_selections < 1:
        raise ValueError("Invalid research thresholds")
    grouped = defaultdict(list)
    fixtures = defaultdict(list)
    seen = set()
    for row in rows:
        key = tuple(row[k] for k in ("league","fold","date","home","away"))
        market = row["market"]
        unique = key + (market,)
        if unique in seen:
            raise ValueError("Duplicate market prediction")
        seen.add(unique)
        p, y = float(row["probability"]), int(row["actual"])
        if not math.isfinite(p) or not 0<=p<=1 or y not in (0,1):
            raise ValueError("Invalid probability or outcome")
        grouped[market].append((p,y))
        fixtures[key].append((market,p,y))
    markets = {}
    for market, observations in sorted(grouped.items()):
        n=len(observations)
        selections=[(p,y) for p,y in observations if p>=threshold]
        wins=sum(y for _,y in selections)
        markets[market]={
            "n":n,"brier":sum((p-y)**2 for p,y in observations)/n,
            "high_probability_n":len(selections),
            "high_probability_wins":wins,
            "high_probability_win_rate":wins/len(selections) if selections else None,
            "high_probability_wilson_95pct":wilson(wins,len(selections)),
        }
    # One selection per fixture; deterministic tie-breaker. Unlike the live
    # screen, this uses goal markets only and lacks cross-model disagreement.
    picks=[]
    for key, candidates in fixtures.items():
        eligible=[row for row in candidates if row[1]>=threshold]
        if eligible:
            picks.append(sorted(eligible,key=lambda row:(-row[1],row[0]))[0])
    wins=sum(y for _,_,y in picks)
    interval=wilson(wins,len(picks))
    return {
        "evaluation":"EXPLORATORY_CHRONOLOGICAL_FOLDS_NOT_UNTOUCHED",
        "policy":"FIXED_MAX_PROBABILITY_GOAL_MARKET_PER_FIXTURE",
        "threshold":threshold,
        "fixtures_evaluated":len(fixtures),
        "markets":markets,
        "selected_fixtures":len(picks),
        "selected_wins":wins,
        "selected_win_rate":wins/len(picks) if picks else None,
        "selected_wilson_95pct":interval,
        "meets_research_sample_and_lower_bound":bool(len(picks)>=min_selections and interval and interval[0]>=threshold),
        "live_multimarket_policy_validated":False,
        "limitations":[
            "Previously explored folds; not untouched external validation",
            "Goal-market-only selection does not reproduce the live model-disagreement screen",
            "Correlated markets are evaluated separately, not as independent matches",
            "No calibration fitting or tuning on held-out outcomes",
            "Research pass is not authorization for live high-confidence endorsement",
        ],
    }
