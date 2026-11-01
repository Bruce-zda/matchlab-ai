"""Contract tests for non-archived manual previews."""
import datetime as dt
import unittest
from unittest.mock import patch
from scripts.manual_preview import preview

NOW = dt.datetime(2026, 11, 1, 12, tzinfo=dt.timezone.utc)
KICKOFF = "2026-11-05T15:00:00Z"

class ManualPreviewTests(unittest.TestCase):
    def test_rejects_same_team(self):
        with self.assertRaises(ValueError):
            preview("Premier League", "Arsenal", "arsenal", KICKOFF, NOW)

    def test_rejects_unverified_past_kickoff(self):
        with self.assertRaises(ValueError):
            preview("Premier League", "Arsenal", "Chelsea", "2026-10-30T15:00:00Z", NOW)

    def test_preview_does_not_use_existing_ledger(self):
        records = [dict(model=name) for name in ("Dixon-Coles", "Bayesian Goals", "Elo", "DC + Bayesian (50/50)")]
        with patch("scripts.manual_preview.subprocess.check_output", return_value="testsha"), patch(
            "scripts.manual_preview.collect", return_value=(records, [{"status": "preview"}])
        ) as collect:
            result = preview("Premier League", "Arsenal", "Chelsea", KICKOFF, NOW)
        self.assertEqual(collect.call_args.args[1], [])
        self.assertFalse(result["official_forward_archive"])
        self.assertFalse(result["fixture_verified"])
        self.assertEqual(len(result["forecasts"]), 4)

if __name__ == "__main__":
    unittest.main()
