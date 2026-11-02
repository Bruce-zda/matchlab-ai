"""Reproducible offline model-fit benchmark; no provider token or official archive writes.

Run: python scripts/benchmark_preview_models.py --matches 240 --repeats 2
Synthetic timings are diagnostic only and do not establish live provider latency.
"""
import argparse
import json
import pathlib
import sys
import time

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from football_models import fit_dc, forecast
from bayesian_goals import BayesianGoals
from elo_baseline import EloBaseline


def synthetic_history(count: int) -> pd.DataFrame:
    if count < 150:
        raise ValueError("At least 150 matches required")
    rng = np.random.default_rng(20261102)
    teams = [f"Club {i:02d}" for i in range(12)]
    records = []
    for i in range(count):
        h = i % len(teams)
        a = (h + 1 + (i // len(teams)) % (len(teams) - 1)) % len(teams)
        records.append({"Date": pd.Timestamp("2023-01-01") + pd.Timedelta(days=i),
                        "HomeTeam": teams[h], "AwayTeam": teams[a],
                        "FTHG": int(rng.poisson(1.5)), "FTAG": int(rng.poisson(1.1))})
    return pd.DataFrame(records)


def benchmark(count: int, repeats: int) -> dict:
    if not 1 <= repeats <= 10:
        raise ValueError("Repeats must be between 1 and 10")
    history = synthetic_history(count)
    observations = []
    for _ in range(repeats):
        times = {}
        start = time.perf_counter()
        dc = fit_dc(history)
        times["dixon_coles_fit_seconds"] = round(time.perf_counter() - start, 4)
        start = time.perf_counter()
        bayes = BayesianGoals().fit(history)
        times["bayesian_fit_seconds"] = round(time.perf_counter() - start, 4)
        start = time.perf_counter()
        elo = EloBaseline()
        for row in history.itertuples():
            elo.observe(row.HomeTeam, row.AwayTeam, row.FTHG, row.FTAG)
        times["elo_training_seconds"] = round(time.perf_counter() - start, 4)
        home, away = dc[0][0], dc[0][1]
        start = time.perf_counter()
        forecast(dc, home, away)
        bayes.score_grid(home, away)
        elo.predict(home, away)
        times["combined_inference_seconds"] = round(time.perf_counter() - start, 4)
        observations.append(times)
    return {"dataset": "deterministic_synthetic_not_real_matches", "matches": count,
            "repeats": repeats, "seconds_by_run": observations,
            "median_seconds": {key: round(float(np.median([run[key] for run in observations])), 4)
                               for key in observations[0]},
            "warning": "Not live latency; excludes data downloads, fixture verification and cold starts."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matches", type=int, default=240)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    result = benchmark(args.matches, args.repeats)
    output = json.dumps(result, indent=2) + "\n"
    if args.output:
        if args.output.resolve().is_relative_to((ROOT / "artifacts").resolve()):
            parser.error("Benchmark may not write into official artifacts directory")
        args.output.write_text(output)
    print(output)


if __name__ == "__main__":
    main()
