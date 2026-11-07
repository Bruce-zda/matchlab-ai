import unittest
from forward_multimarket_validation import evaluate_forward_multimarket

BASE = {"fixture_id":"match-1","captured_at_utc":"2026-11-03T12:00:00Z",
        "kickoff_utc":"2026-11-03T15:00:00Z","model_version":"v1",
        "market_probabilities":{"over_1_5":0.90,"btts_yes":0.60}}
FINAL = {"fixture_id":"match-1","status":"final","home_goals":2,"away_goals":1}

class ForwardMultimarketTests(unittest.TestCase):
    def test_scores_frozen_selection(self):
        report = evaluate_forward_multimarket([BASE], [FINAL], {"over_1_5":"PRELIMINARY_SUPPORT"})
        self.assertEqual(report["overall"]["wins"], 1)
        self.assertEqual(report["overall"]["selections"], 1)
        self.assertFalse(report["live_accuracy_validated"])

    def test_post_kickoff_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_forward_multimarket([{**BASE,"captured_at_utc":"2026-11-03T15:00:00Z"}],
                                         [FINAL], {"over_1_5":"PRELIMINARY_SUPPORT"})

    def test_duplicate_snapshot_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_forward_multimarket([BASE, BASE], [FINAL], {"over_1_5":"PRELIMINARY_SUPPORT"})

    def test_abstention(self):
        report = evaluate_forward_multimarket([BASE], [FINAL], {})
        self.assertEqual(report["abstained"], 1)
        self.assertEqual(report["overall"]["selections"], 0)

    def test_pending_is_not_scored(self):
        report = evaluate_forward_multimarket([BASE], [], {"over_1_5":"PRELIMINARY_SUPPORT"})
        self.assertEqual(report["pending"], 1)
        self.assertEqual(report["overall"]["selections"], 0)

    def test_unsupported_market_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_forward_multimarket([{**BASE,"market_probabilities":{"corners_over_9_5":0.9}}],
                                         [FINAL], {"corners_over_9_5":"PRELIMINARY_SUPPORT"})

if __name__ == "__main__":
    unittest.main()
