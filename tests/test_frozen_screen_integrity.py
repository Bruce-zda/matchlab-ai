import unittest
import numpy as np
from goal_markets import market_probabilities
from intelligence_selection import screen_outlook
from forward_validation import validate_forecast

def sample():
    goals=market_probabilities(np.ones((4,4))/16)
    markets=[{"key":key,"probability":p,"model_range":{"spread":0.02},
              "conditional":False} for key,p in sorted(goals["markets"].items())]
    return {"league":"Premier League","home":"Home","away":"Away",
            "kickoff_utc":"2026-11-03T15:00:00Z",
            "captured_at_utc":"2026-11-03T12:00:00Z",
            "model":"DC + Bayesian (50/50)","model_version":"test",
            "p_home":0.4,"p_draw":0.3,"p_away":0.3,
            "goal_markets":goals,"screen_markets":markets,
            "frozen_screen":screen_outlook(markets),
            "screen_policy_version":"intelligence_selection.screen_outlook_default_80pct_10pct_spread"}

class FrozenCaptureIntegrityTests(unittest.TestCase):
    def test_valid_capture(self):
        self.assertTrue(validate_forecast(sample()))

    def test_probability_tampering_rejected(self):
        r=sample()
        r["screen_markets"][0]["probability"]=0.99
        with self.assertRaises(ValueError):
            validate_forecast(r)

    def test_decision_tampering_rejected(self):
        r=sample()
        r["frozen_screen"]["status"]="RESEARCH_SCREEN_ONLY"
        with self.assertRaises(ValueError):
            validate_forecast(r)

    def test_duplicate_market_rejected(self):
        r=sample()
        r["screen_markets"].append(dict(r["screen_markets"][0]))
        with self.assertRaises(ValueError):
            validate_forecast(r)

if __name__=="__main__":
    unittest.main()
