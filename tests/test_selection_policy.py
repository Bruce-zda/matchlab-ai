import unittest
from selection_policy import (
    MarketEvidence, assess_market_evidence, assess_calibration_gate,
    describe_candidate, rank_model_outlooks,
)


class SelectionPolicyTests(unittest.TestCase):
    def test_requires_enough_evidence(self):
        item = MarketEvidence("1X", 8, 8, .19, .22)
        self.assertEqual(assess_market_evidence(item), "INSUFFICIENT_EVIDENCE")

    def test_rejects_weak_baseline_comparison(self):
        item = MarketEvidence("1X", 15, 12, .23, .22)
        self.assertEqual(assess_market_evidence(item), "NO_MODEL_ADVANTAGE")

    def test_support_is_not_expert_approval(self):
        item = MarketEvidence("1X", 15, 12, .19, .22)
        self.assertEqual(assess_market_evidence(item), "PRELIMINARY_SUPPORT")
        self.assertIn("no verified market odds", describe_candidate(.82, "PRELIMINARY_SUPPORT"))

    def test_known_report_does_not_promote_weak_markets(self):
        report = {
            "evaluation_type": "exploratory_rolling_historical_not_untouched",
            "markets": {
                "1X": {"folds": 13, "improved_folds": 9, "mean_raw_brier": .193380765, "mean_calibrated_brier": .192218311},
                "X2": {"folds": 13, "improved_folds": 4, "mean_raw_brier": .215967116, "mean_calibrated_brier": .216724798},
                "12": {"folds": 13, "improved_folds": 6, "mean_raw_brier": .203007423, "mean_calibrated_brier": .202885792},
            },
        }
        self.assertEqual(assess_calibration_gate(report, "1X"), "INCONSISTENT_CALIBRATION_GAIN")
        self.assertEqual(assess_calibration_gate(report, "X2"), "NO_CALIBRATION_GAIN")
        self.assertEqual(assess_calibration_gate(report, "12"), "INCONSISTENT_CALIBRATION_GAIN")

    def test_abstains_without_final_validation(self):
        self.assertIn("independent final validation", describe_candidate(.75, "PRELIMINARY_SUPPORT", True))

    def test_rejects_invalid_probability(self):
        with self.assertRaises(ValueError):
            describe_candidate(float("nan"), "PRELIMINARY_SUPPORT")

    def test_ranking_abstains_on_close_markets(self):
        outcome = rank_model_outlooks(
            {"1X": .80, "X2": .78},
            {"1X": "PRELIMINARY_SUPPORT", "X2": "PRELIMINARY_SUPPORT"})
        self.assertEqual(outcome["status"], "ABSTAIN")

    def test_ranking_excludes_unsupported_markets(self):
        outcome = rank_model_outlooks(
            {"1X": .73, "X2": .95},
            {"1X": "PRELIMINARY_SUPPORT", "X2": "NO_MODEL_ADVANTAGE"})
        self.assertEqual(outcome["status"], "DESCRIPTIVE_OUTLOOK_ONLY")
        self.assertEqual(outcome["ranking"][0][0], "1X")

    def test_ranking_abstains_on_low_probability(self):
        outcome = rank_model_outlooks({"1X": .52}, {"1X": "PRELIMINARY_SUPPORT"})
        self.assertEqual(outcome["status"], "ABSTAIN")


if __name__ == "__main__":
    unittest.main()
