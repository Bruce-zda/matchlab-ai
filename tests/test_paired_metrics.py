import unittest
from paired_metrics import compare

class PairedComparisonTests(unittest.TestCase):
    def setUp(self):
        self.ledger=[
            {'snapshot_id':'dc','provider_match_id':17,'kickoff_utc':'2026-11-01T15:00:00+00:00','league':'Premier League'},
            {'snapshot_id':'hybrid','provider_match_id':17,'kickoff_utc':'2026-11-01T15:00:00+00:00','league':'Premier League'}]
        self.results=[
            {'snapshot_id':'dc','provider_match_id':17,'model':'Dixon-Coles','actual':0,'brier':0.2,'log_loss':0.8},
            {'snapshot_id':'hybrid','provider_match_id':17,'model':'DC + Bayesian (50/50)','actual':0,'brier':0.18,'log_loss':0.75}]
    def test_paired_difference(self):
        rows=compare(self.ledger,self.results)
        self.assertEqual(len(rows),1)
        self.assertAlmostEqual(rows[0]['brier_delta'],-0.02)
    def test_unpaired_fixture_not_counted(self):
        self.assertEqual(compare(self.ledger,self.results[:1]),[])
    def test_conflicting_result_rejected(self):
        self.results[1]['actual']=1
        with self.assertRaises(ValueError):
            compare(self.ledger,self.results)
    def test_duplicate_model_rejected(self):
        with self.assertRaises(ValueError):
            compare(self.ledger,self.results+[self.results[0]])
if __name__=='__main__':
    unittest.main()
