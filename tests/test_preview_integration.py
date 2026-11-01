"""HTTP-to-queue-to-worker smoke test without network or real credentials."""
import http.client
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import preview_jobs
from preview_service import Handler


class PreviewIntegrationTests(unittest.TestCase):
    def test_authenticated_job_lifecycle(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(
            preview_jobs, "DB_PATH", Path(folder) / "jobs.sqlite"
        ), patch.dict(os.environ, {"MATCHLAB_PREVIEW_SERVICE_TOKEN": "integration-secret",
                                  "FOOTBALL_DATA_TOKEN": "provider-secret"}):
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                def request(method, path, body=None, authorized=True):
                    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                    headers = {"Content-Type": "application/json"}
                    if authorized:
                        headers["Authorization"] = "Bearer integration-secret"
                    connection.request(method, path, body=json.dumps(body) if body else None, headers=headers)
                    result = connection.getresponse()
                    status = result.status
                    payload = json.loads(result.read())
                    connection.close()
                    return status, payload

                fixture = {"league": "Premier League", "home": "Arsenal FC",
                           "away": "Chelsea FC", "kickoff_utc": "2099-01-01T12:00:00Z"}
                status, _ = request("POST", "/jobs", fixture, authorized=False)
                self.assertEqual(status, 401)
                from datetime import datetime, timedelta, timezone
                fixture["kickoff_utc"] = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
                status, result = request("POST", "/jobs", fixture)
                self.assertEqual(status, 202)
                jid = result["job_id"]
                status, queued = request("GET", "/jobs/" + jid)
                self.assertEqual(status, 200)
                self.assertEqual(queued["status"], "queued")
                verified = {**fixture, "provider_match_id": 123}
                with patch.object(preview_jobs, "validate_fixture", return_value=verified), patch.object(
                    preview_jobs, "preview", return_value={"kind": "on_demand_preview",
                    "official_forward_archive": False, "forecasts": [1, 2, 3, 4]}
                ):
                    self.assertTrue(preview_jobs.process_one())
                status, done = request("GET", "/jobs/" + jid)
                self.assertEqual(status, 200)
                self.assertEqual(done["status"], "complete")
                self.assertTrue(done["preview"]["fixture_verified"])
                self.assertFalse(done["preview"]["official_forward_archive"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
