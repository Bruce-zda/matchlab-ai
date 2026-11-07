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

    def test_asian_handicap_push_and_symmetry(self):
        grid=np.zeros((5,5))
        grid[1,0]=0.4
        grid[1,1]=0.3
        grid[0,0]=0.2
        grid[2,1]=0.1
        handicap=market_probabilities(grid)['asian_handicap']
        home_zero=handicap['home_plus_0_0']
        away_zero=handicap['away_plus_0_0']
        self.assertAlmostEqual(home_zero['win'],0.5)
        self.assertAlmostEqual(home_zero['push'],0.5)
        self.assertAlmostEqual(home_zero['loss'],0.0)
        self.assertAlmostEqual(away_zero['win'],home_zero['loss'])
        self.assertAlmostEqual(away_zero['loss'],home_zero['win'])
        self.assertAlmostEqual(away_zero['push'],home_zero['push'])
        self.assertAlmostEqual(handicap['home_minus_0_5']['win'],0.5)
        self.assertAlmostEqual(handicap['home_minus_0_5']['push'],0.0)

    def test_reject_invalid_handicap_settlement(self):
        data=market_probabilities(np.ones((4,4)))
        data['asian_handicap']['home_plus_0_0']['push']=0.9
        with self.assertRaises(ValueError):
            validate_goal_markets(data)

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
