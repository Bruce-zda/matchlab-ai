"""Durable preview queue tests with temporary SQLite database."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import preview_jobs


class QueueTests(unittest.TestCase):
    def test_persists_jobs_and_enforces_hourly_quota(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(preview_jobs, "DB_PATH", Path(temp) / "jobs.db"):
            ids = [preview_jobs.submit({"league": "Premier League", "home": f"Team {i}"}) for i in range(3)]
            self.assertEqual(len(set(ids)), 3)
            self.assertEqual(preview_jobs.get_job(ids[0])["status"], "queued")
            with self.assertRaises(OverflowError):
                preview_jobs.submit({"league": "Premier League", "home": "Fourth team"})
            self.assertIsNone(preview_jobs.get_job("unknown"))

    def test_identical_requests_share_job_and_quota(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(preview_jobs, "DB_PATH", Path(temp) / "jobs.db"):
            payload = {"league": "Premier League", "home": "Arsenal", "away": "Chelsea"}
            first = preview_jobs.submit(payload)
            second = preview_jobs.submit({"away": "Chelsea", "home": "Arsenal", "league": "Premier League"})
            self.assertEqual(first, second)
            with preview_jobs.connect() as db:
                self.assertEqual(db.execute("SELECT count(*) FROM jobs").fetchone()[0], 1)

    def test_completes_without_archiving(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(preview_jobs, "DB_PATH", Path(temp) / "jobs.db"):
            fixture = {"league": "Premier League", "home": "Arsenal", "away": "Chelsea",
                       "kickoff_utc": "2026-11-07T15:00:00Z", "provider_match_id": 123}
            jid = preview_jobs.submit(fixture)
            with patch.object(preview_jobs, "validate_fixture", return_value=fixture), patch.object(
                preview_jobs, "preview", return_value={"kind": "on_demand_preview",
                   "official_forward_archive": False, "forecasts": [1, 2, 3, 4]}
            ):
                self.assertTrue(preview_jobs.process_one())
            result = preview_jobs.get_job(jid)
            self.assertEqual(result["status"], "complete")
            self.assertTrue(result["preview"]["fixture_verified"])
            self.assertFalse(result["preview"]["official_forward_archive"])


if __name__ == "__main__":
    unittest.main()
