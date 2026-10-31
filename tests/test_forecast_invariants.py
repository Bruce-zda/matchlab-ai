"""Numerical invariants for the deployed Dixon-Coles score-grid forecast."""
import ast
import pathlib
import unittest

import numpy as np
from scipy.stats import poisson

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "app.py"


def load_forecast():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "forecast")
    namespace = {"np": np, "poisson": poisson}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace["forecast"]


class ForecastInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Keep the extracted function unbound: unittest instances must not become its first argument.
        cls.forecast = staticmethod(load_forecast())

    def test_grid_is_valid_probability_distribution(self):
        model = (["Home", "Away"], {"Home": 0.1, "Away": -0.1},
                 {"Home": -0.05, "Away": 0.05}, 0.2, 0.0, -0.05)
        lam, mu, grid = self.forecast(model, "Home", "Away")
        self.assertEqual(grid.shape, (13, 13))
        self.assertTrue(np.isfinite(grid).all())
        self.assertTrue((grid >= 0).all())
        self.assertAlmostEqual(float(grid.sum()), 1.0, places=12)
        self.assertGreater(lam, 0)
        self.assertGreater(mu, 0)

    def test_equal_teams_without_home_advantage_are_symmetric(self):
        model = (["A", "B"], {"A": 0., "B": 0.},
                 {"A": 0., "B": 0.}, 0., 0., -0.05)
        _, _, grid = self.forecast(model, "A", "B")
        np.testing.assert_allclose(grid, grid.T, atol=1e-12)
        self.assertAlmostEqual(float(np.tril(grid, -1).sum()),
                               float(np.triu(grid, 1).sum()), places=12)

    def test_double_chance_identities(self):
        model = (["A", "B"], {"A": 0., "B": 0.},
                 {"A": 0., "B": 0.}, 0.2, 0., 0.)
        _, _, grid = self.forecast(model, "A", "B")
        home = float(np.tril(grid, -1).sum())
        draw = float(np.trace(grid))
        away = float(np.triu(grid, 1).sum())
        self.assertAlmostEqual(home + draw + away, 1., places=12)
        self.assertAlmostEqual((home + draw) + away, 1., places=12)
        self.assertAlmostEqual((draw + away) + home, 1., places=12)


if __name__ == "__main__":
    unittest.main()
