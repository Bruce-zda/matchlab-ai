import unittest
from elo_baseline import EloBaseline, evaluate_elo

class EloBaselineTests(unittest.TestCase):
    def test_probabilities_are_valid(self):
        model = EloBaseline()
        probs = model.predict("A", "B")
        self.assertAlmostEqual(sum(probs), 1.0)
        self.assertTrue(all(0 < p < 1 for p in probs))

    def test_no_future_leakage(self):
        model = EloBaseline()
        before = model.predict("A", "B")
        model.observe("A", "B", 4, 0)
        after = model.predict("A", "B")
        self.assertGreater(after[0], before[0])

    def test_invalid_match_rejected(self):
        with self.assertRaises(ValueError):
            EloBaseline().observe("A", "A", 1, 0)

    def test_walk_forward_scores(self):
        rows = [("A", "B", 2, 0)] * 12
        scores = evaluate_elo(rows, warmup=5)
        self.assertEqual(len(scores), 7)
        self.assertTrue(all(0 <= r["brier"] <= 1 for r in scores))
        self.assertTrue(all(r["log_loss"] >= 0 for r in scores))

if __name__ == "__main__":
    unittest.main()
