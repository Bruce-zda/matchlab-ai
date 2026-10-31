import unittest
from forward_validation import utc_time
from scripts.collect_forward import collect

class CollectorSafetyTests(unittest.TestCase):
    def test_date_only_kickoff_rejected_without_network(self):
        fixtures=[{'league':'Premier League','home':'Alpha','away':'Beta',
                   'kickoff_utc':'2026-11-01'}]
        ledger,audit=collect(fixtures,[],'2026-10-31T14:00:00+00:00','test-sha')
        self.assertEqual(ledger,[])
        self.assertEqual(audit[0]['status'],'skipped')
        self.assertIn('Timezone required',audit[0]['reason'])

    def test_past_kickoff_rejected_without_network(self):
        fixtures=[{'league':'Premier League','home':'Alpha','away':'Beta',
                   'kickoff_utc':'2026-10-30T14:00:00+00:00'}]
        ledger,audit=collect(fixtures,[],'2026-10-31T14:00:00+00:00','test-sha')
        self.assertEqual(ledger,[])
        self.assertEqual(audit[0]['status'],'skipped')

    def test_time_zone_conversion(self):
        self.assertEqual(utc_time('2026-11-01T16:00:00+01:00').hour,15)

if __name__=='__main__':
    unittest.main()
