import unittest
from historical_market_validation import evaluate_historical_markets


class HistoricalMarketValidationTests(unittest.TestCase):
    def test_market_metrics_and_one_selection_per_fixture(self):
        rows=[]
        for i in range(12):
            for market,p,y in [('over_1_5',.90,int(i<10)),('btts_yes',.81,int(i<7))]:
                rows.append(dict(league='L',fold=1,date=f'2026-01-{i+1:02d}',
                                 home='A',away='B',market=market,probability=p,actual=y))
        result=evaluate_historical_markets(rows)
        self.assertEqual(result['fixtures_evaluated'],12)
        self.assertEqual(result['selected_fixtures'],12)
        self.assertEqual(result['selected_wins'],10)
        self.assertFalse(result['meets_research_sample_and_lower_bound'])
        self.assertFalse(result['live_multimarket_policy_validated'])
        self.assertEqual(result['markets']['btts_yes']['high_probability_n'],12)

    def test_duplicate_rejected(self):
        row=dict(league='L',fold=1,date='2026-01-01',home='A',away='B',
                 market='over_2_5',probability=.7,actual=1)
        with self.assertRaises(ValueError):
            evaluate_historical_markets([row,row])

    def test_no_selection_abstains(self):
        row=dict(league='L',fold=1,date='2026-01-01',home='A',away='B',
                 market='over_2_5',probability=.7,actual=1)
        result=evaluate_historical_markets([row])
        self.assertIsNone(result['selected_win_rate'])
        self.assertEqual(result['selected_fixtures'],0)


if __name__=="__main__":
    unittest.main()
