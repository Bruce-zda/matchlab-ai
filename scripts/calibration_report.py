"""Run MatchLab's existing rolling evaluation without launching Streamlit UI.

Usage: python scripts/calibration_report.py
Outputs artifacts/calibration_report.json and artifacts/rolling_validation.csv.
Exploratory only: previously inspected historical folds are not an untouched test.
"""
import ast
import datetime as dt
import io
import json
import pathlib
import re
import sys

import numpy as np
import pandas as pd
import requests
from scipy.optimize import minimize
from scipy.stats import poisson

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from calibration import chronological_calibration_report
from selection_policy import assess_calibration_gate
SOURCE = (ROOT / "app.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
NAMES = {
    "fit_dc", "forecast", "matchday_csv", "normalized", "map_team",
    "fetch_season", "get_league", "rolling_league_evaluation",
}
# Only explicitly audited model/data functions are executed. This deliberately
# avoids executing the Streamlit app, widgets, and top-level UI side effects.
functions = []
for node in TREE.body:
    if isinstance(node, ast.FunctionDef) and node.name in NAMES:
        node.decorator_list = []
        functions.append(node)
if {n.name for n in functions} != NAMES:
    raise RuntimeError("MatchLab model/data function contract changed")
namespace = {
    "dt": dt, "io": io, "re": re, "np": np, "pd": pd,
    "requests": requests, "minimize": minimize, "poisson": poisson,
    "chronological_calibration_report": chronological_calibration_report,
    "LEAGUES": {
        "Premier League": "en.1", "La Liga": "es.1", "Serie A": "it.1",
        "Bundesliga": "de.1", "Ligue 1": "fr.1",
    },
    "TODAY": dt.date.today(),
    "OPEN_MATCHDAY": "https://raw.githubusercontent.com/oladeeayo/open-matchday/master/data",
    "FOLDERS": {
        "en.1": "ENG_1_premier-league", "es.1": "ESP_1_la-liga",
        "it.1": "ITA_1_serie-a", "de.1": "GER_1_bundesliga",
        "fr.1": "FRA_1_ligue-1",
    },
}
module = ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[]))
exec(compile(module, str(ROOT / "app.py"), "exec"), namespace)
rolling, errors = namespace["rolling_league_evaluation"]()
output = ROOT / "artifacts"
output.mkdir(exist_ok=True)
rolling.to_csv(output / "rolling_validation.csv", index=False)
summary = {
    "date_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    "evaluation_type": "exploratory_rolling_historical_not_untouched",
    "folds": len(rolling),
    "errors": errors,
    "markets": {},
}
for market in ("1X", "X2", "12"):
    raw = f"{market} calibration raw Brier"
    adjusted = f"{market} calibration adjusted Brier"
    if raw in rolling:
        valid = rolling[[raw, adjusted]].dropna()
        if len(valid):
            summary["markets"][market] = {
                "folds": len(valid),
                "improved_folds": int((valid[adjusted] < valid[raw]).sum()),
                "mean_raw_brier": float(valid[raw].mean()),
                "mean_calibrated_brier": float(valid[adjusted].mean()),
            }
summary["calibration_gate"] = {market: assess_calibration_gate(summary, market) for market in ("1X", "X2", "12")}
summary["live_calibration_enabled"] = False
(output / "calibration_report.json").write_text(
    json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
)
print(json.dumps(summary, indent=2))
if len(rolling) < 10 or len(summary["markets"]) != 3:
    raise SystemExit("Insufficient historical coverage: review data source errors and fold counts")
