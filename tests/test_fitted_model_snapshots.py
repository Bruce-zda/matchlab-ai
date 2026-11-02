import copy
import unittest

import numpy as np
import pandas as pd
from bayesian_goals import BayesianGoals
from elo_baseline import EloBaseline
from football_models import forecast
from fitted_model_snapshots import pack, unpack, training_digest


class SnapshotTests(unittest.TestCase):
    def test_round_trip_and_stale_rejection(self):
        history = pd.DataFrame({
            "Date": pd.date_range("2026-01-01", periods=24),
            "HomeTeam": ["Alpha", "Beta"] * 12,
            "AwayTeam": ["Beta", "Alpha"] * 12,
            "FTHG": [2, 1] * 12,
            "FTAG": [0, 1] * 12,
        })
        dc = (["Alpha", "Beta"], {"Alpha": .2, "Beta": -.2},
              {"Alpha": -.1, "Beta": .1}, .15, .0, -.05)
        bayes = BayesianGoals().fit(history)
        elo = EloBaseline()
        for row in history.itertuples():
            elo.observe(row.HomeTeam, row.AwayTeam, row.FTHG, row.FTAG)
        digest = training_digest(history)
        kwargs = dict(league="Premier League", cutoff_utc_date="2026-11-02",
                      model_version="abc123", history_sha256=digest)
        snapshot = pack(dc, bayes, elo, **kwargs)
        loaded_dc, loaded_bayes, loaded_elo = unpack(snapshot, **kwargs)
        np.testing.assert_allclose(forecast(dc, "Alpha", "Beta")[2],
                                   forecast(loaded_dc, "Alpha", "Beta")[2])
        np.testing.assert_allclose(bayes.predict("Alpha", "Beta"),
                                   loaded_bayes.predict("Alpha", "Beta"))
        np.testing.assert_allclose(elo.predict("Alpha", "Beta"),
                                   loaded_elo.predict("Alpha", "Beta"))
        with self.assertRaises(ValueError):
            unpack(snapshot, **{**kwargs, "cutoff_utc_date": "2026-11-03"})
        with self.assertRaises(ValueError):
            unpack(snapshot, **{**kwargs, "history_sha256": "wrong"})
        corrupted = copy.deepcopy(snapshot)
        corrupted["payload"]["dc"]["home"] = .99
        with self.assertRaises(ValueError):
            unpack(corrupted, **kwargs)


if __name__ == "__main__":
    unittest.main()
