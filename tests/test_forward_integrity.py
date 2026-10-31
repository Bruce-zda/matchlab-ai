import unittest
from forward_integrity import ledger_digest,manifest,verify

class IntegrityTests(unittest.TestCase):
    def test_exact_record_changes_invalidate_digest(self):
        ledger=[{'snapshot_id':'abc','p_home':0.5,'model':'Dixon-Coles'}]
        proof=manifest(ledger)
        self.assertTrue(verify(ledger,proof))
        with self.assertRaises(ValueError):
            verify([{'snapshot_id':'abc','p_home':0.6,'model':'Dixon-Coles'}],proof)
    def test_reorder_changes_digest(self):
        self.assertNotEqual(ledger_digest([{'id':1},{'id':2}]),
                            ledger_digest([{'id':2},{'id':1}]))
    def test_reject_nonfinite(self):
        with self.assertRaises(ValueError):
            ledger_digest([{'probability':float('nan')}])

if __name__=='__main__':
    unittest.main()
