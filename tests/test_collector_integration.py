"""Offline end-to-end forecast collector test."""
import unittest
from unittest.mock import patch
import numpy as np
from scripts import collect_forward as collector
from forward_validation import validate_forecast

class FakeBayes:
    def score_grid(self,home,away):
        return np.ones((4,4))/16

class FakeElo:
    def predict(self,home,away):
        return np.array([0.4,0.3,0.3])

class CollectorIntegrationTests(unittest.TestCase):
    def test_truncated_grids_are_normalized_before_capture(self):
        fixture={"league":"Premier League","home":"Alpha","away":"Beta",
                 "kickoff_utc":"2026-11-03T15:00:00Z","provider_match_id":124}
        now="2026-11-02T12:00:00Z"
        cache={("Premier League","2026-11-02","test-version"):
               ((["Alpha","Beta"],None,None,None,None,0.1),FakeBayes(),FakeElo())}
        models={"forecast":lambda dc,home,away:(1.2,1.0,np.ones((4,4))/20)}
        with patch.object(collector,"models_from_app",return_value=models), patch.object(
                collector,"match_team",side_effect=lambda name,names:name):
            records,audit=collector.collect([fixture],[],now,"test-version",fitted_cache=cache)
        self.assertEqual(audit[0]["status"],"recorded",audit)
        self.assertEqual(len(records),4)
        self.assertTrue(all(validate_forecast(row) for row in records))


    def test_capture_and_immutable_replay(self):
        fixture={"league":"Premier League","home":"Alpha","away":"Beta",
                 "kickoff_utc":"2026-11-03T15:00:00Z","provider_match_id":123}
        now="2026-11-02T12:00:00Z"
        grid=np.ones((4,4))/16
        cache={("Premier League","2026-11-02","test-version"):
               ((["Alpha","Beta"],None,None,None,None,0.1),FakeBayes(),FakeElo())}
        models={"forecast":lambda dc,home,away:(1.2,1.0,grid)}
        with patch.object(collector,"models_from_app",return_value=models), patch.object(
                collector,"match_team",side_effect=lambda name,names:name):
            records,audit=collector.collect([fixture],[],now,"test-version",fitted_cache=cache)
            self.assertEqual(audit[0]["status"],"recorded",audit)
            self.assertEqual(len(records),4)
            hybrid=next(r for r in records if r["model"]=="DC + Bayesian (50/50)")
            self.assertEqual(len(hybrid["screen_markets"]),20)
            self.assertFalse(hybrid["frozen_screen"]["expert_pick"])
            self.assertTrue(all(validate_forecast(r) for r in records))
            replay,replay_audit=collector.collect([fixture],records,now,"test-version",fitted_cache=cache)
            self.assertEqual(replay,records)
            self.assertEqual(replay_audit[0]["status"],"already_recorded")

if __name__=="__main__":
    unittest.main()
