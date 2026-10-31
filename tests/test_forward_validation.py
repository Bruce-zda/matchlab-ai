import unittest
from forward_validation import append_snapshot,settle_snapshot,validate_forecast,snapshot_id

class ForwardValidationTests(unittest.TestCase):
    def setUp(self):
        self.row={'league':'Premier League','home':'Alpha','away':'Beta',
                  'kickoff_utc':'2026-11-01T15:00:00+00:00',
                  'captured_at_utc':'2026-10-31T14:00:00+00:00',
                  'model':'Dixon-Coles','model_version':'commit-abc',
                  'p_home':0.5,'p_draw':0.3,'p_away':0.2}
    def test_snapshot_append_and_score(self):
        ledger=append_snapshot([],self.row)
        self.assertEqual(len(ledger),1)
        self.assertEqual(ledger[0]['snapshot_id'],snapshot_id(self.row))
        self.assertAlmostEqual(settle_snapshot(self.row,2,0)['brier'],(0.25+0.09+0.04)/3)
    def test_no_duplicate_forecast(self):
        with self.assertRaises(ValueError):
            append_snapshot(append_snapshot([],self.row),self.row)
    def test_after_kickoff_rejected(self):
        self.row['captured_at_utc']='2026-11-01T15:00:00+00:00'
        with self.assertRaises(ValueError):
            validate_forecast(self.row)
    def test_bad_probabilities_rejected(self):
        self.row['p_home']=0.7
        with self.assertRaises(ValueError):
            validate_forecast(self.row)
    def test_timezone_required(self):
        self.row['kickoff_utc']='2026-11-01T15:00:00'
        with self.assertRaises(ValueError):
            validate_forecast(self.row)

if __name__=='__main__':
    unittest.main()
