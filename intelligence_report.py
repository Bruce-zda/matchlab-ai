"""Evidence-grounded, deterministic MatchLab intelligence report.

No LLM-generated facts, bookmaker odds, invented injury reports or asserted
historical win rates. Descriptive forecasts only, not wagering advice.
"""
import math

LABELS = {
    "home_win": "Home win", "draw": "Draw", "away_win": "Away win",
    "home_or_draw": "Home or draw", "away_or_draw": "Away or draw",
    "home_or_away": "Home or away", "home_draw_no_bet": "Home draw no bet",
    "away_draw_no_bet": "Away draw no bet",
    "btts_yes": "Both teams to score", "btts_no": "Both teams not to score",
}


def _valid(p):
    if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError("Invalid model probability")
    return float(p)


def build_intelligence_report(forecasts):
    """Produce structured market analysis from existing pre-match model outputs.

    No artificial probability adjustments or synthetic scenarios. Model
    disagreement is shown as sensitivity evidence, not a calibrated interval.
    """
    by_model = {row["model"]: row for row in forecasts}
    if len(by_model) != len(forecasts) or not forecasts:
        raise ValueError("Expected unique nonempty model forecasts")
    primary = by_model.get("DC + Bayesian (50/50)")
    dc = by_model.get("Dixon-Coles")
    bayes = by_model.get("Bayesian Goals")
    if not all((primary, dc, bayes)):
        raise ValueError("Required fitted model forecasts unavailable")
    for row in forecasts:
        if (row["league"], row["home"], row["away"], row["kickoff_utc"]) != (
                primary["league"], primary["home"], primary["away"], primary["kickoff_utc"]):
            raise ValueError("Forecasts describe different fixtures")
    p = [_valid(primary[key]) for key in ("p_home", "p_draw", "p_away")]
    if abs(sum(p) - 1) > 1e-5:
        raise ValueError("Inconsistent 1X2 probabilities")
    outcomes = {"home_win": p[0], "draw": p[1], "away_win": p[2],
                "home_or_draw": p[0] + p[1], "away_or_draw": p[1] + p[2],
                "home_or_away": p[0] + p[2]}
    if p[0] + p[2] > 1e-10:
        outcomes["home_draw_no_bet"] = p[0] / (p[0] + p[2])
        outcomes["away_draw_no_bet"] = p[2] / (p[0] + p[2])
    goal = primary.get("goal_markets", {})
    for name, probability in goal.get("markets", {}).items():
        outcomes[name] = _valid(probability)
    for key, value in outcomes.items():
        _valid(value)
    models = [dc, bayes]
    sensitivity = {}
    for name, key in (("home_win", "p_home"), ("draw", "p_draw"), ("away_win", "p_away")):
        values = [_valid(row[key]) for row in models]
        sensitivity[name] = {"minimum": min(values), "maximum": max(values),
                             "spread": max(values) - min(values)}
    for name in goal.get("markets", {}):
        values = []
        for row in models:
            markets = row.get("goal_markets", {}).get("markets", {})
            if name in markets:
                values.append(_valid(markets[name]))
        if len(values) == len(models):
            sensitivity[name] = {"minimum": min(values), "maximum": max(values),
                                 "spread": max(values) - min(values)}
    # Conservative descriptive verdict: only compare non-conditional events
    # with two-model sensitivity, and explicitly abstain from endorsement.
    eligible = [(name, probability) for name, probability in outcomes.items()
                if name in sensitivity and name not in ("home_draw_no_bet", "away_draw_no_bet")]
    eligible.sort(key=lambda item: (-item[1], item[0]))
    best_name, best_p = eligible[0]
    spread = sensitivity[best_name]["spread"]
    return {
        "schema_version": 1,
        "status": "DESCRIPTIVE_MODEL_OUTLOOK_NOT_VALIDATED",
        "fixture": {key: primary[key] for key in ("league", "home", "away", "kickoff_utc")},
        "methodology": {
            "probability_source": "Uncalibrated 50/50 Dixon-Coles and Bayesian goal-model mixture",
            "model_sensitivity": "Range across Dixon-Coles and Bayesian estimates, NOT a confidence interval",
            "conditional_markets": ["home_draw_no_bet", "away_draw_no_bet"],
            "limitations": [
                "No independent verification of user-supplied kickoff",
                "No verified injuries, lineups, tactics or suspensions",
                "No proven 80 percent win rate",
                "Score-grid truncation and renormalization may affect tail probabilities",
                "Historical reliability and scenario stress testing not yet validated",
            ],
        },
        "simulation": primary.get("simulation"),
        "scenarios": primary.get("scenarios"),
        "markets": [{"key": name, "label": LABELS.get(name, name.replace("_", " ").title()),
                     "probability": round(probability, 6),
                     "model_range": sensitivity.get(name),
                     "conditional": name.endswith("_draw_no_bet")}
                    for name, probability in sorted(outcomes.items())],
        "verdict": {
            "type": "MOST_PROBABLE_MODELED_EVENT_ONLY",
            "market": best_name,
            "probability": round(best_p, 6),
            "model_disagreement": round(spread, 6),
            "expert_pick": False,
            "reason": (
                f"{LABELS.get(best_name, best_name.replace('_', ' '))} has the highest "
                f"estimated probability ({best_p:.1%}) among the supported "
                "non-conditional score-derived events. "
                f"The two goal models differ by {spread:.1%} on this event. "
                "This is a mathematical ranking, not a verified high-confidence pick."
            ),
        },
        "analysis_sections": [
            {"title": "Match overview", "text": (
                f"{primary['home']} vs {primary['away']} in {primary['league']}. "
                "Kickoff and team availability require independent verification.")},
            {"title": "Mathematical assessment", "text": (
                f"The model mixture estimates home win {p[0]:.1%}, draw {p[1]:.1%}, "
                f"away win {p[2]:.1%}. These are pre-match model estimates, not observed frequencies.")},
            {"title": "Model disagreement", "text": (
                f"For home wins, the Dixon-Coles and Bayesian estimates span "
                f"{sensitivity['home_win']['minimum']:.1%}–{sensitivity['home_win']['maximum']:.1%}. "
                "This is model sensitivity, not a probabilistic uncertainty interval.")},
            {"title": "Verdict and risk", "text": (
                "The displayed leading event is descriptive only. Unverified team news, "
                "model misspecification and changing match conditions may alter the outcome. "
                "No expert endorsement is issued without forward validation.")},
        ],
    }
