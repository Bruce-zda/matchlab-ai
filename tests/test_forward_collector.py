import unittest
import pandas as pd
from forward_validation import utc_time
from scripts.collect_forward import collect,match_team,canonicalize_history

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

    def test_precomputed_models_expire_on_utc_day_change(self):
        cache = {('Premier League', '2026-10-31', 'test-sha'): object()}
        fixtures = [{'league': 'Premier League', 'home': 'Alpha', 'away': 'Beta',
                     'kickoff_utc': '2026-11-04T14:00:00+00:00'}]
        from unittest.mock import patch
        with patch('scripts.collect_forward.models_from_app', return_value={
            'fetch_season': lambda season, code: pd.DataFrame()}):
            ledger, audit = collect(fixtures, [], '2026-11-02T12:00:00+00:00',
                                    'test-sha', preview=True, fitted_cache=cache)
        self.assertEqual(ledger, [])
        self.assertEqual(audit[0]['status'], 'skipped')
        self.assertEqual(cache, {})

    def test_history_merges_approved_aliases_across_venues(self):
        frame=pd.DataFrame({'HomeTeam':['Aston Villa','Chelsea','Aston Villa FC'],
                            'AwayTeam':['Chelsea','Aston Villa FC','Chelsea']})
        result=canonicalize_history(frame)
        names=set(result.HomeTeam)|set(result.AwayTeam)
        self.assertEqual(len([n for n in names if n.startswith('Aston Villa')]),1)
        self.assertEqual(match_team('Aston Villa FC',names),
                         next(n for n in names if n.startswith('Aston Villa')))

    def test_approved_newcastle_alias(self):
        self.assertEqual(match_team('Newcastle United FC',['Newcastle United','Chelsea']), 'Newcastle United')

    def test_newcastle_full_club_name(self):
        self.assertEqual(match_team('Newcastle United FC',['Newcastle United FC']), 'Newcastle United FC')
        self.assertEqual(match_team('Newcastle United FC',['Newcastle United Football Club']), 'Newcastle United Football Club')

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
