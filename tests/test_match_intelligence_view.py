import unittest
from match_intelligence_view import archived_goal_market_rows, archived_research_screen, LABELS
from intelligence_selection import screen_outlook

class ArchivedIntelligenceTests(unittest.TestCase):
    def test_complete_market_catalog(self):
        self.assertEqual(len(LABELS), 20)

    def test_sort_and_validate(self):
        rows = archived_goal_market_rows({"goal_markets": {"markets": {
            "over_2_5": 0.65, "btts_yes": 0.72}}})
        self.assertEqual(rows[0]["Market"], LABELS["btts_yes"])
        with self.assertRaises(ValueError):
            archived_goal_market_rows({"goal_markets": {"markets": {"btts_yes": float("nan")}}})

    def test_old_snapshots_have_no_reconstructed_pick(self):
        self.assertIsNone(archived_research_screen({"goal_markets": {"markets": {}}}))

    def test_frozen_pick_is_checked(self):
        markets = [{"key": "over_1_5", "probability": 0.9,
                    "model_range": {"spread": 0.03}, "conditional": False}]
        decision = screen_outlook(markets)
        self.assertEqual(archived_research_screen({"screen_markets": markets,
                         "frozen_screen": decision}), decision)
        with self.assertRaises(ValueError):
            archived_research_screen({"screen_markets": markets,
                                      "frozen_screen": {**decision, "status": "ABSTAIN"}})

if __name__ == "__main__":
    unittest.main()
