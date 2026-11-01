"""Private on-demand MatchLab preview service. Never writes the official archive.

Deploy as a separate single-worker Python service, behind HTTPS. Configure
MATCHLAB_PREVIEW_SERVICE_TOKEN and FOOTBALL_DATA_TOKEN on the service.
"""
import datetime as dt
import hmac
import json
import os
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from football_data_provider import get_matches, upcoming_fixtures
from scripts.manual_preview import preview, json_native

MAX_BODY = 2048
WINDOW = 3600
LIMIT = 3
LOCK = threading.Lock()
FIT_LOCK = threading.Lock()
COUNTS = defaultdict(deque)


def validate_fixture(league, home, away, kickoff):
    """Require exact provider identity and UTC kickoff; never trust user text alone."""
    token = os.environ.get("FOOTBALL_DATA_TOKEN", "")
    if not token:
        raise RuntimeError("Fixture verification provider is not configured")
    when = dt.datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
    now = dt.datetime.now(dt.timezone.utc)
    if when.tzinfo is None or not now < when <= now + dt.timedelta(days=7):
        raise ValueError("Kickoff must be within the next seven days")
    start = now.date().isoformat()
    end = (now + dt.timedelta(days=7)).date().isoformat()
    matches = upcoming_fixtures(get_matches(token, start, end), now.isoformat())
    found = [m for m in matches if m["league"] == league and m["home"] == home
             and m["away"] == away and
             abs((dt.datetime.fromisoformat(m["kickoff_utc"]) - when).total_seconds()) < 60]
    if len(found) != 1:
        raise ValueError("Fixture not independently verified; use exact provider team names and kickoff")
    return found[0]


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, data):
        raw = json.dumps(data, default=json_native).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path != "/health":
            return self.reply(404, {"error": "Not found"})
        ready = bool(os.environ.get("MATCHLAB_PREVIEW_SERVICE_TOKEN") and os.environ.get("FOOTBALL_DATA_TOKEN"))
        self.reply(200 if ready else 503, {"status": "ok" if ready else "unconfigured"})

    def do_POST(self):
        if self.path != "/preview":
            return self.reply(404, {"error": "Not found"})
        secret = os.environ.get("MATCHLAB_PREVIEW_SERVICE_TOKEN", "")
        supplied = self.headers.get("Authorization", "")
        if not secret or not hmac.compare_digest(supplied, "Bearer " + secret):
            return self.reply(401, {"error": "Unauthorized"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY:
                return self.reply(413, {"error": "Invalid request size"})
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError("Expected JSON object")
            league, home, away, kickoff = (body[k] for k in ("league", "home", "away", "kickoff_utc"))
            if not all(isinstance(x, str) and 0 < len(x) <= 100 for x in (league, home, away, kickoff)):
                raise ValueError("Invalid fields")
            if home == away:
                raise ValueError("Teams must differ")
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            return self.reply(400, {"error": "Invalid preview request"})
        # Rate limit per authorized service token. Keep one worker: counters are in-memory.
        with LOCK:
            now = time.monotonic()
            q = COUNTS["authorized"]
            while q and now - q[0] > WINDOW:
                q.popleft()
            if len(q) >= LIMIT:
                return self.reply(429, {"error": "Preview compute quota exceeded"})
            q.append(now)
        if not FIT_LOCK.acquire(blocking=False):
            return self.reply(429, {"error": "Preview compute busy"})
        try:
            verified = validate_fixture(league, home, away, kickoff)
            result = preview(verified["league"], verified["home"], verified["away"], verified["kickoff_utc"])
            result["fixture_verified"] = True
            result["provider_match_id"] = verified["provider_match_id"]
            result["warning"] = "Fresh, verified-fixture analysis; NOT an official pre-kickoff archive snapshot. No guarantee of accuracy."
            return self.reply(200, result)
        except ValueError:
            return self.reply(422, {"error": "Fixture verification or model validation failed"})
        except Exception:
            return self.reply(503, {"error": "Preview compute unavailable"})
        finally:
            FIT_LOCK.release()


if __name__ == "__main__":
    if not os.environ.get("MATCHLAB_PREVIEW_SERVICE_TOKEN") or not os.environ.get("FOOTBALL_DATA_TOKEN"):
        raise SystemExit("Configure MATCHLAB_PREVIEW_SERVICE_TOKEN and FOOTBALL_DATA_TOKEN")
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
