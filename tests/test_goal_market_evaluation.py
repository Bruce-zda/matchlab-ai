import unittest
import numpy as np
from goal_markets import market_probabilities
from goal_market_evaluation import evaluate_goal_markets

class GoalEvaluationTests(unittest.TestCase):
    def test_actual_goal_outcomes(self):
        grid=np.zeros((5,5))
        grid[2,1]=1.0
        forecast={'snapshot_id':'test','goal_markets':market_probabilities(grid)}
        result={'snapshot_id':'test','home_goals':2,'away_goals':1}
        scored={r['market']:r for r in evaluate_goal_markets(forecast,result)}
        self.assertEqual(scored['btts_yes']['actual'],1)
        self.assertEqual(scored['over_2_5']['actual'],1)
        self.assertEqual(scored['under_3_5']['actual'],1)
        self.assertEqual(scored['away_over_1_5']['actual'],0)
        self.assertAlmostEqual(scored['btts_yes']['brier'],0.0)

    def test_missing_market_data_does_not_invent_forecasts(self):
        self.assertEqual(evaluate_goal_markets({'snapshot_id':'x'},{'snapshot_id':'x'}),[])

    def test_mismatched_snapshot_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_goal_markets({'snapshot_id':'x'},{'snapshot_id':'y'})

if __name__=='__main__':
    unittest.main()
