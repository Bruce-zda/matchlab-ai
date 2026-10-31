import unittest
from football_data_provider import upcoming_fixtures,finished_scores

class FootballProviderTests(unittest.TestCase):
    def test_upcoming_requires_future_kickoff(self):
        base={'id':12,'competition':{'code':'PL'},'status':'SCHEDULED',
              'homeTeam':{'name':'Arsenal'},'awayTeam':{'name':'Chelsea'},
              'utcDate':'2026-11-02T15:00:00Z'}
        result=upcoming_fixtures([base],'2026-10-31T15:00:00Z')
        self.assertEqual(result[0]['provider_match_id'],12)
        self.assertEqual(result[0]['league'],'Premier League')
        self.assertEqual(upcoming_fixtures([base],'2026-11-03T15:00:00Z'),[])
    def test_only_finished_scores(self):
        matches=[{'id':1,'status':'FINISHED','score':{'fullTime':{'home':2,'away':1}}},
                 {'id':2,'status':'IN_PLAY','score':{'fullTime':{'home':1,'away':0}}}]
        self.assertEqual(finished_scores(matches),[{'provider_match_id':1,'home_goals':2,'away_goals':1}])

if __name__=='__main__':
    unittest.main()
