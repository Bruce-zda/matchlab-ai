"""Offline end-to-end fitted snapshot benchmark with deterministic synthetic matches.

Measures full fitting versus a validated disk snapshot reload. Excludes network,
fixture verification, production hardware, and queue latency.
"""
import json
import pathlib
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.benchmark_preview_models import synthetic_history
from football_models import fit_dc, forecast
from bayesian_goals import BayesianGoals
from elo_baseline import EloBaseline
from fitted_model_snapshots import pack, unpack, training_digest


def measure(matches=240):
    history = synthetic_history(matches)
    metadata = dict(league="Synthetic Test League", cutoff_utc_date="2026-11-02",
                    model_version="benchmark-only", history_sha256=training_digest(history))
    t = time.perf_counter()
    dc = fit_dc(history)
    bayes = BayesianGoals().fit(history)
    elo = EloBaseline()
    for row in history.itertuples():
        elo.observe(row.HomeTeam, row.AwayTeam, row.FTHG, row.FTAG)
    fresh = time.perf_counter() - t
    with tempfile.TemporaryDirectory() as directory:
        path = pathlib.Path(directory) / "fitted.json"
        path.write_text(json.dumps(pack(dc, bayes, elo, **metadata)))
        t = time.perf_counter()
        loaded = unpack(json.loads(path.read_text()), **metadata)
        warm = time.perf_counter() - t
    home, away = dc[0][:2]
    original = forecast(dc, home, away)[2]
    restored = forecast(loaded[0], home, away)[2]
    import numpy as np
    np.testing.assert_allclose(original, restored, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(bayes.predict(home, away), loaded[1].predict(home, away))
    np.testing.assert_allclose(elo.predict(home, away), loaded[2].predict(home, away))
    return {"dataset": "synthetic", "matches": matches,
            "fresh_fit_seconds": round(fresh, 6),
            "validated_disk_reload_seconds": round(warm, 6),
            "speedup_fit_only": round(fresh / max(warm, 1e-9), 2),
            "predictions_identical": True,
            "warning": "Does not include network downloads, training digest computation, cold starts or provider verification."}


if __name__ == "__main__":
    print(json.dumps(measure(), indent=2))
