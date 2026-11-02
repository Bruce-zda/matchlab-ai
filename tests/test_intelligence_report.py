import unittest
from intelligence_report import build_intelligence_report


class IntelligenceReportTests(unittest.TestCase):
    def records(self):
        base = dict(league="Premier League", home="Alpha", away="Beta",
                    kickoff_utc="2026-11-08T12:00:00+00:00")
        goal = {"markets": {"btts_yes": .58, "btts_no": .42,
                             "over_2_5": .61, "under_2_5": .39}}
        return [
            {**base, "model": "Dixon-Coles", "p_home": .51, "p_draw": .26,
             "p_away": .23, "goal_markets": goal},
            {**base, "model": "Bayesian Goals", "p_home": .55, "p_draw": .24,
             "p_away": .21, "goal_markets": goal},
            {**base, "model": "Elo", "p_home": .50, "p_draw": .25, "p_away": .25},
            {**base, "model": "DC + Bayesian (50/50)", "p_home": .53,
             "p_draw": .25, "p_away": .22, "goal_markets": goal},
        ]

    def test_report_has_consistent_markets_and_no_unearned_endorsement(self):
        report = build_intelligence_report(self.records())
        market = {item["key"]: item["probability"] for item in report["markets"]}
        self.assertAlmostEqual(market["home_win"] + market["draw"] + market["away_win"], 1)
        self.assertAlmostEqual(market["home_or_draw"], .78)
        self.assertAlmostEqual(market["home_draw_no_bet"], .53 / .75, places=5)
        self.assertAlmostEqual(market["btts_yes"] + market["btts_no"], 1)
        self.assertFalse(report["verdict"]["expert_pick"])
        self.assertEqual(len(report["analysis_sections"]), 6)
        self.assertFalse(report["selection_screen"]["expert_pick"])
        self.assertEqual(report["selection_screen"]["calibration"], "NOT_VERIFIED")
        self.assertAlmostEqual(report["verdict"]["model_disagreement"],
                               report["markets"][next(i for i, m in enumerate(report["markets"])
                               if m["key"] == report["verdict"]["market"])]["model_range"]["spread"], places=6)

    def test_rejects_cross_fixture_and_invalid_probabilities(self):
        records = self.records()
        records[0]["home"] = "Wrong"
        with self.assertRaises(ValueError):
            build_intelligence_report(records)
        records = self.records()
        records[2]["p_home"] = float("nan")
        # Elo is not used to calculate the mixture; invalid primary is rejected.
        records[-1]["p_home"] = float("nan")
        with self.assertRaises(ValueError):
            build_intelligence_report(records)

    def test_rejects_duplicate_model(self):
        records = self.records()
        with self.assertRaises(ValueError):
            build_intelligence_report(records + [records[0]])


if __name__ == "__main__":
    unittest.main()
