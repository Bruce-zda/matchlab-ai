import unittest
from scripts.validate_forward_append import check
from forward_validation import append_snapshot

class AppendOnlyTests(unittest.TestCase):
    def setUp(self):
        self.row={'league':'Premier League','home':'Alpha','away':'Beta',
                  'kickoff_utc':'2026-11-01T15:00:00+00:00',
                  'captured_at_utc':'2026-10-31T14:00:00+00:00',
                  'model':'Dixon-Coles','model_version':'commit-abc',
                  'p_home':0.5,'p_draw':0.3,'p_away':0.2}
    def test_valid_extension(self):
        old=append_snapshot([],self.row)
        row2=dict(self.row,model='Elo')
        new=append_snapshot(old,row2)
        self.assertEqual(check(old,new),1)
    def test_modification_rejected(self):
        old=append_snapshot([],self.row)
        changed=[dict(old[0],p_home=0.6,p_draw=0.2)]
        with self.assertRaises(ValueError):
            check(old,changed)
    def test_deletion_rejected(self):
        with self.assertRaises(ValueError):
            check(append_snapshot([],self.row),[])

if __name__=='__main__':
    unittest.main()
