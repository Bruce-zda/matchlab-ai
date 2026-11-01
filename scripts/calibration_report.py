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
from data_quality import valid_score_pair, valid_team_pair
from historical_calibration import rolling_league_evaluation
rolling, errors = rolling_league_evaluation()
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
