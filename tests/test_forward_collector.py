import unittest
from forward_validation import utc_time
from scripts.collect_forward import collect,match_team

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

    def test_approved_newcastle_alias(self):
        self.assertEqual(match_team('Newcastle United FC',['Newcastle United','Chelsea']), 'Newcastle United')

    def test_unknown_club_is_not_guessed(self):
        with self.assertRaises(ValueError):
            match_team('Newcastle City FC',['Newcastle United','Chelsea'])

    def test_ambiguous_training_names_rejected(self):
        with self.assertRaises(ValueError):
            match_team('Newcastle United FC',['Newcastle United','Newcastle United FC'])

    def test_time_zone_conversion(self):
        self.assertEqual(utc_time('2026-11-01T16:00:00+01:00').hour,15)

if __name__=='__main__':
    unittest.main()
