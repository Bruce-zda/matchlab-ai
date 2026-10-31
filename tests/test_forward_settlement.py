import unittest
from forward_validation import append_snapshot
from scripts.settle_forward import reconcile,summary

class ForwardSettlementTests(unittest.TestCase):
    def setUp(self):
        self.row={'league':'Premier League','home':'Alpha','away':'Beta',
                  'kickoff_utc':'2026-11-01T15:00:00+00:00',
                  'captured_at_utc':'2026-10-31T14:00:00+00:00',
                  'model':'Dixon-Coles','model_version':'commit-abc',
                  'provider_match_id':123,'p_home':0.5,'p_draw':0.3,'p_away':0.2}
        self.ledger=append_snapshot([],self.row)
        self.finished=[{'id':123,'status':'FINISHED','score':{'fullTime':{'home':2,'away':1}}}]
    def test_settle_and_idempotence(self):
        settled,audit=reconcile(self.ledger,self.finished)
        self.assertEqual(audit['newly_settled'],1)
        self.assertEqual(summary(self.ledger,settled)['settled_fixtures'],1)
        again,audit=reconcile(self.ledger,self.finished,settled)
        self.assertEqual(again,settled)
        self.assertEqual(audit['already_settled'],1)
    def test_live_match_never_settles(self):
        games=[dict(self.finished[0],status='IN_PLAY')]
        settled,audit=reconcile(self.ledger,games)
        self.assertEqual(settled,[])
        self.assertEqual(audit['awaiting_verified_result'],1)
    def test_corrected_score_requires_review(self):
        settled,_=reconcile(self.ledger,self.finished)
        corrected=[{'id':123,'status':'FINISHED','score':{'fullTime':{'home':0,'away':2}}}]
        with self.assertRaises(ValueError):
            reconcile(self.ledger,corrected,settled)

if __name__=='__main__':
    unittest.main()
