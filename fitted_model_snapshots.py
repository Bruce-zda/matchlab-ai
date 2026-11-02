"""Versioned, integrity-checked fitted-model snapshots (never official forecasts).

These helpers do not load arbitrary pickle/code and require callers to verify
the training dataset digest and cutoff before using the reconstructed models.
"""
import hashlib
import json
from bayesian_goals import BayesianGoals
from elo_baseline import EloBaseline

SCHEMA = 1


def training_digest(history):
    """SHA256 of chronological, canonical training rows including score and date."""
    rows = []
    for row in history.sort_values(["Date", "HomeTeam", "AwayTeam"]).itertuples():
        rows.append([row.Date.isoformat(), str(row.HomeTeam), str(row.AwayTeam),
                     int(row.FTHG), int(row.FTAG)])
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def pack(dc, bayes, elo, *, league, cutoff_utc_date, model_version, history_sha256):
    teams, attack, defense, home, base, rho = dc
    data = {
        "schema": SCHEMA, "league": league, "cutoff_utc_date": cutoff_utc_date,
        "model_version": model_version, "history_sha256": history_sha256,
        "dc": {"teams": list(teams), "attack": attack, "defense": defense,
               "home": float(home), "base": float(base), "rho": float(rho)},
        "bayes": {
            "prior_matches": bayes.prior_matches, "max_goals": bayes.max_goals,
            "home_mean": bayes.home_mean, "away_mean": bayes.away_mean,
            "teams": sorted(bayes.teams),
            **{name: {key: list(value) for key, value in getattr(bayes, name).items()}
               for name in ("hf", "ha", "af", "aa")},
        },
        "elo": {"k": elo.k, "home_advantage": elo.home_advantage,
                "ratings": elo.ratings, "draw_rate": elo.draw_rate,
                "matches": elo.matches},
    }
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return {"payload": data, "sha256": hashlib.sha256(payload.encode()).hexdigest()}


def unpack(snapshot, *, league, cutoff_utc_date, model_version, history_sha256):
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("payload"), dict):
        raise ValueError("Malformed fitted-model snapshot")
    data = snapshot["payload"]
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if hashlib.sha256(payload.encode()).hexdigest() != snapshot.get("sha256"):
        raise ValueError("Fitted-model snapshot integrity failure")
    expected = (SCHEMA, league, cutoff_utc_date, model_version, history_sha256)
    actual = tuple(data.get(key) for key in
                   ("schema", "league", "cutoff_utc_date", "model_version", "history_sha256"))
    if actual != expected:
        raise ValueError("Fitted-model snapshot is stale or from another training set")
    d = data["dc"]
    teams = d["teams"]
    if len(teams) < 2 or set(teams) != set(d["attack"]) or set(teams) != set(d["defense"]):
        raise ValueError("Invalid Dixon-Coles team parameters")
    dc = (teams, d["attack"], d["defense"], d["home"], d["base"], d["rho"])
    b = data["bayes"]
    bayes = BayesianGoals(b["prior_matches"], b["max_goals"])
    bayes.home_mean, bayes.away_mean = b["home_mean"], b["away_mean"]
    bayes.teams = set(b["teams"])
    for name in ("hf", "ha", "af", "aa"):
        setattr(bayes, name, {key: tuple(value) for key, value in b[name].items()})
    e = data["elo"]
    elo = EloBaseline(e["k"], e["home_advantage"])
    elo.ratings, elo.draw_rate, elo.matches = e["ratings"], e["draw_rate"], e["matches"]
    return dc, bayes, elo
