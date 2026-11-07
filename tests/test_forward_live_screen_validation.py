import unittest
from forward_live_screen_validation import evaluate_live_screen

SNAP = {"provider_match_id": 1, "model": "DC + Bayesian (50/50)",
        "model_version": "frozen-v1", "captured_at_utc": "2026-11-03T12:00:00Z",
        "kickoff_utc": "2026-11-03T15:00:00Z",
        "screen_markets": [{"key": "over_1_5", "probability": 0.91,
                            "model_range": {"spread": 0.04}, "conditional": False}]}
FINAL = {"provider_match_id": 1, "status": "final", "home_goals": 2, "away_goals": 1}

class LiveScreenValidationTests(unittest.TestCase):
    def test_matches_real_screen_and_scores(self):
        r = evaluate_live_screen([SNAP], [FINAL])
        self.assertEqual(r["settled_selections"], 1)
        self.assertEqual(r["wins"], 1)
        self.assertFalse(r["live_policy_validated"])

    def test_no_backfill_from_old_snapshots(self):
        with self.assertRaisesRegex(ValueError, "Missing frozen"):
            evaluate_live_screen([{k:v for k,v in SNAP.items() if k != "screen_markets"}], [FINAL])

    def test_disagreement_causes_abstention(self):
        s = {**SNAP, "screen_markets": [{"key": "over_1_5", "probability": 0.91,
                                         "model_range": {"spread": 0.20}}]}
        r = evaluate_live_screen([s], [FINAL])
        self.assertEqual(r["abstained"], 1)

    def test_tampered_frozen_decision_rejected(self):
        from intelligence_selection import screen_outlook
        frozen = screen_outlook(SNAP["screen_markets"])
        altered = {**frozen, "status": "ABSTAIN"}
        with self.assertRaisesRegex(ValueError, "Frozen research-screen"):
            evaluate_live_screen([{**SNAP, "frozen_screen": altered}], [FINAL])

    def test_post_kickoff_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_live_screen([{**SNAP, "captured_at_utc": "2026-11-03T15:01:00Z"}], [FINAL])

    def test_pending_not_counted_as_loss(self):
        r = evaluate_live_screen([SNAP], [])
        self.assertEqual(r["pending"], 1)
        self.assertEqual(r["settled_selections"], 0)

if __name__ == "__main__":
    unittest.main()
