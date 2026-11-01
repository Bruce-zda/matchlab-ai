"""Preview backend must fail closed without provider verification."""
import datetime as dt
import os
import unittest
from unittest.mock import patch

from preview_jobs import validate_fixture

NOW = dt.datetime.now(dt.timezone.utc)
FUTURE = (NOW + dt.timedelta(days=2)).replace(microsecond=0).isoformat()
RECORD = {"league": "Premier League", "home": "Arsenal FC", "away": "Chelsea FC",
          "kickoff_utc": FUTURE, "provider_match_id": 123}

class PreviewServiceTests(unittest.TestCase):
    def test_missing_provider_token_rejected(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                validate_fixture("Premier League", "Arsenal FC", "Chelsea FC", FUTURE)

    def test_provider_match_verified(self):
        with patch.dict(os.environ, {"FOOTBALL_DATA_TOKEN": "test"}), patch(
            "preview_jobs.get_matches", return_value=[]
        ), patch("preview_jobs.upcoming_fixtures", return_value=[RECORD]):
            self.assertEqual(validate_fixture("Premier League", "Arsenal FC", "Chelsea FC", FUTURE)["provider_match_id"], 123)

    def test_unmatched_kickoff_rejected(self):
        with patch.dict(os.environ, {"FOOTBALL_DATA_TOKEN": "test"}), patch(
            "preview_jobs.get_matches", return_value=[]
        ), patch("preview_jobs.upcoming_fixtures", return_value=[RECORD]):
            with self.assertRaises(ValueError):
                validate_fixture("Premier League", "Arsenal FC", "Chelsea FC", (NOW + dt.timedelta(days=3)).isoformat())

if __name__ == "__main__":
    unittest.main()
