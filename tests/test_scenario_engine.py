import unittest
import numpy as np
from scenario_engine import simulate_score_grid, stress_expected_goals


class ScenarioEngineTests(unittest.TestCase):
    def test_monte_carlo_reproducible_and_matches_analytical(self):
        grid = np.array([[.15,.1,.05],[.2,.2,.05],[.15,.05,.05]])
        first = simulate_score_grid(grid)
        self.assertEqual(first, simulate_score_grid(grid))
        for key in ("home_win","draw","away_win"):
            self.assertLess(abs(first["simulated"][key]-first["analytical"][key]), .02)
        self.assertAlmostEqual(sum(first["analytical"].values()),1)

    def test_stress_scenarios_bounded_and_directional(self):
        data = stress_expected_goals(1.6,1.1)
        base = data["scenarios"]["baseline"]
        lower = data["scenarios"]["home_attack_minus_15pct"]
        self.assertLess(lower["home_win"],base["home_win"])
        self.assertGreater(data["scenarios"]["higher_tempo_plus_15pct"]["over_2_5"],
                           data["scenarios"]["lower_tempo_minus_15pct"]["over_2_5"])
        for row in data["scenarios"].values():
            self.assertAlmostEqual(row["home_win"]+row["draw"]+row["away_win"],1)

    def test_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):
            simulate_score_grid(np.array([[float("nan"),1],[1,1]]))
        with self.assertRaises(ValueError):
            stress_expected_goals(-1,1)


if __name__ == "__main__":
    unittest.main()
