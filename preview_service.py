"""Private authenticated asynchronous prediction service.

Run as a single process with a persistent SQLite volume.
"""
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from preview_jobs import connect, get_job, start_worker, submit

MAX_BODY = 2048
LEAGUES = {"Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"}


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, data):
        raw = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def authorized(self):
        secret = os.environ.get("MATCHLAB_PREVIEW_SERVICE_TOKEN", "")
        return bool(secret) and hmac.compare_digest(
            self.headers.get("Authorization", ""), "Bearer " + secret)

    def do_GET(self):
        if self.path == "/health":
            ready = bool(os.environ.get("MATCHLAB_PREVIEW_SERVICE_TOKEN")
                         and os.environ.get("FOOTBALL_DATA_TOKEN"))
            return self.reply(200 if ready else 503,
                              {"status": "ok" if ready else "unconfigured"})
        if not self.authorized():
            return self.reply(401, {"error": "Unauthorized"})
        route = urlparse(self.path)
        if route.path.startswith("/jobs/") and route.query == "":
            job_id = route.path.removeprefix("/jobs/")
            result = get_job(job_id)
            return self.reply(200, result) if result else self.reply(404, {"error": "Unknown job"})
        return self.reply(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/jobs":
            return self.reply(404, {"error": "Not found"})
        if not self.authorized():
            return self.reply(401, {"error": "Unauthorized"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY:
                return self.reply(413, {"error": "Invalid request size"})
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError()
            league, home, away, kickoff = (payload[k] for k in
                                           ("league", "home", "away", "kickoff_utc"))
            if league not in LEAGUES or not all(
                isinstance(x, str) and 0 < len(x) <= 100
                for x in (home, away, kickoff)
            ) or home.strip().casefold() == away.strip().casefold():
                raise ValueError()
            from datetime import datetime, timezone, timedelta
            when = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if when.tzinfo is None or not now < when <= now + timedelta(days=7):
                raise ValueError()
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return self.reply(400, {"error": "Invalid fixture request"})
        try:
            job_id = submit({"league": league, "home": home.strip(),
                             "away": away.strip(), "kickoff_utc": kickoff})
        except OverflowError:
            return self.reply(429, {"error": "Compute quota exceeded"})
        except Exception:
            return self.reply(503, {"error": "Queue unavailable"})
        return self.reply(202, {"job_id": job_id, "status": "queued"})


if __name__ == "__main__":
    if not os.environ.get("MATCHLAB_PREVIEW_SERVICE_TOKEN") or not os.environ.get("FOOTBALL_DATA_TOKEN"):
        raise SystemExit("Configure MATCHLAB_PREVIEW_SERVICE_TOKEN and FOOTBALL_DATA_TOKEN")
    from pathlib import Path
    from preview_jobs import DB_PATH
    if str(DB_PATH).startswith("/tmp/") or not os.environ.get("MATCHLAB_PREVIEW_DB"):
        raise SystemExit("MATCHLAB_PREVIEW_DB must point to a mounted persistent volume")
    if not DB_PATH.parent.is_dir() or not os.access(DB_PATH.parent, os.W_OK):
        raise SystemExit("Persistent queue directory must exist and be writable")
    connect().close()
    start_worker()
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Handler).serve_forever()
