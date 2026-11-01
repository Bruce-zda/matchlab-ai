import unittest
import numpy as np
from goal_markets import market_probabilities,validate_goal_markets

class GoalMarketsTests(unittest.TestCase):
    def test_market_complements_and_score_order(self):
        grid=np.zeros((5,5))
        grid[1,0]=0.4
        grid[1,1]=0.3
        grid[0,0]=0.2
        grid[2,1]=0.1
        data=market_probabilities(grid)
        self.assertTrue(validate_goal_markets(data))
        m=data['markets']
        self.assertAlmostEqual(m['btts_yes'],0.4)
        self.assertAlmostEqual(m['btts_yes']+m['btts_no'],1)
        for n in ('1_5','2_5','3_5'):
            self.assertAlmostEqual(m['over_'+n]+m['under_'+n],1)
        for side in ('home','away'):
            for n in ('0_5','1_5','2_5'):
                self.assertAlmostEqual(m[side+'_over_'+n]+m[side+'_under_'+n],1)
        self.assertEqual((data['correct_scores'][0]['home_goals'],data['correct_scores'][0]['away_goals']),(1,0))

    def test_reject_invalid_market(self):
        grid=np.ones((5,5))
        data=market_probabilities(grid)
        data['markets']['btts_yes']=0.99
        with self.assertRaises(ValueError):
            validate_goal_markets(data)

    def test_reject_bad_grid(self):
        with self.assertRaises(ValueError):
            market_probabilities(np.zeros((4,4)))
        with self.assertRaises(ValueError):
            market_probabilities(np.array([[float('nan')]*4]*4))

if __name__=='__main__':
    unittest.main()
