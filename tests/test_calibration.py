"""Calibration contract tests. Synthetic data only; no live model promotion."""
import unittest
import numpy as np
from calibration import fit_binary_calibrator, apply_binary_calibrator, chronological_calibration_report


class CalibrationTests(unittest.TestCase):
    def test_fitted_probabilities_stay_bounded_and_ordered(self):
        p = np.linspace(.05, .95, 100)
        y = (np.arange(100) % 7 < (p * 7)).astype(int)
        params = fit_binary_calibrator(p, y)
        out = apply_binary_calibrator(p, params)
        self.assertTrue(np.isfinite(out).all())
        self.assertTrue(((out > 0) & (out < 1)).all())
        self.assertTrue((np.diff(out) >= -1e-12).all())

    def test_rejects_small_and_invalid_training_sets(self):
        with self.assertRaises(ValueError):
            fit_binary_calibrator([.5] * 10, [0] * 10)
        with self.assertRaises(ValueError):
            fit_binary_calibrator([1.5] * 30, [0, 1] * 15)

    def test_single_class_falls_back_to_identity(self):
        p = np.linspace(.1, .9, 40)
        params = fit_binary_calibrator(p, np.zeros(40))
        self.assertEqual(params, (0., 1.))
        np.testing.assert_allclose(apply_binary_calibrator(p, params), p, atol=1e-12)

    def test_chronological_report_is_disjoint_and_non_promotional(self):
        p = np.linspace(.1, .9, 100)
        y = (np.arange(100) % 5 < (p * 5)).astype(float)
        report = chronological_calibration_report(p, y)
        self.assertEqual(report["calibration_train_n"], 65)
        self.assertEqual(report["evaluation_n"], 35)
        self.assertTrue(np.isfinite(report["raw_brier"]))
        self.assertTrue(np.isfinite(report["calibrated_brier"]))
        self.assertIsInstance(report["calibration_improved"], bool)

    def test_chronological_report_rejects_short_series(self):
        with self.assertRaises(ValueError):
            chronological_calibration_report([.5] * 40, [0] * 40)


if __name__ == "__main__":
    unittest.main()
