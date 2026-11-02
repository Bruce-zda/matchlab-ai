import unittest
from intelligence_selection import screen_outlook


class ResearchSelectionTests(unittest.TestCase):
    def test_strong_probability_is_not_an_expert_endorsement(self):
        markets = [{"key": "over_1_5", "probability": .86,
                    "model_range": {"spread": .03}, "conditional": False},
                   {"key": "home_win", "probability": .72,
                    "model_range": {"spread": .02}, "conditional": False}]
        result = screen_outlook(markets)
        self.assertEqual(result["status"], "RESEARCH_SCREEN_ONLY")
        self.assertEqual(result["candidate"]["market"], "over_1_5")
        self.assertFalse(result["expert_pick"])
        self.assertEqual(result["calibration"], "NOT_VERIFIED")

    def test_disagreement_and_conditional_markets_do_not_qualify(self):
        result = screen_outlook([
            {"key": "home_win", "probability": .92,
             "model_range": {"spread": .20}, "conditional": False},
            {"key": "home_draw_no_bet", "probability": .96,
             "model_range": {"spread": .01}, "conditional": True}])
        self.assertEqual(result["status"], "ABSTAIN")
        self.assertIsNone(result["candidate"])

    def test_scenario_weakness_is_exposed(self):
        result = screen_outlook(
            [{"key": "home_win", "probability": .85,
              "model_range": {"spread": .02}, "conditional": False}],
            {"scenarios": {"baseline": {"home_win": .85},
                           "home_attack_minus_15pct": {"home_win": .73}}})
        self.assertEqual(result["candidate"]["minimum_hypothetical_scenario_probability"], .73)


if __name__ == "__main__":
    unittest.main()
