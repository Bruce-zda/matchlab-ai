import unittest
from forward_selection_validation import evaluate_forward_screen,wilson


class ForwardScreenTests(unittest.TestCase):
    def test_no_evidence_never_promotes(self):
        result=evaluate_forward_screen([],[])
        self.assertEqual(result["eligible_settled_selections"],0)
        self.assertIsNone(result["observed_win_rate"])
        self.assertFalse(result["promotion_eligible"])
        self.assertFalse(result["full_multimarket_selection_validated"])

    def test_forward_results_and_confidence_gate(self):
        ledger=[]; settled=[]
        for i in range(10):
            sid=f"fixture-{i}"
            ledger.append({"snapshot_id":sid,"model":"DC + Bayesian (50/50)",
                           "p_home":.85,"p_draw":.10,"p_away":.05})
            settled.append({"snapshot_id":sid,"home_goals":2 if i<9 else 0,
                            "away_goals":0 if i<9 else 2})
        result=evaluate_forward_screen(ledger,settled)
        self.assertEqual(result["wins"],9)
        self.assertAlmostEqual(result["observed_win_rate"],.9)
        self.assertFalse(result["promotion_eligible"])
        self.assertLess(result["wilson_95pct_interval"][0],.8)

    def test_unsatisfied_threshold_and_missing_settlement(self):
        ledger=[{"snapshot_id":"one","model":"DC + Bayesian (50/50)",
                 "p_home":.70,"p_draw":.20,"p_away":.10}]
        self.assertEqual(evaluate_forward_screen(ledger,[])["eligible_settled_selections"],0)

    def test_wilson_interval(self):
        self.assertIsNone(wilson(0,0))
        lo,hi=wilson(50,100)
        self.assertLess(lo,.5)
        self.assertGreater(hi,.5)


if __name__=="__main__":
    unittest.main()
