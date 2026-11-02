"""Durable single-worker preview job queue.

SQLite stores job states and quotas across restarts. Run exactly one service
replica with a persistent volume; use a shared queue/DB for horizontal scaling.
"""
import datetime as dt
import json
import os
import secrets
import sqlite3
import threading
import time
from pathlib import Path

from football_data_provider import get_matches, upcoming_fixtures
from scripts.manual_preview import preview, json_native

DB_PATH = Path(os.environ.get("MATCHLAB_PREVIEW_DB", "/tmp/matchlab_preview.sqlite3"))
LOCK = threading.Lock()
MAX_PENDING = 4
MAX_PER_HOUR = 3
MAX_PER_DAY = 12
RETENTION_SECONDS = 86400
# Worker-only, per-process cache. Never persisted or shared with public callers.
FITTED_CACHE = {}


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=10000")
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY, created REAL NOT NULL, updated REAL NOT NULL,
        state TEXT NOT NULL, request TEXT NOT NULL, result TEXT,
        error TEXT)""")
    db.execute("CREATE INDEX IF NOT EXISTS jobs_created_idx ON jobs(created)")
    db.commit()
    return db


def validate_fixture(league, home, away, kickoff):
    token = os.environ.get("FOOTBALL_DATA_TOKEN", "")
    if not token:
        raise RuntimeError("Fixture verification provider is not configured")
    when = dt.datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
    now = dt.datetime.now(dt.timezone.utc)
    if when.tzinfo is None or not now < when <= now + dt.timedelta(days=7):
        raise ValueError("Kickoff must be within the next seven days")
    matches = upcoming_fixtures(get_matches(token, now.date().isoformat(),
                          (now + dt.timedelta(days=7)).date().isoformat()), now.isoformat())
    found = [m for m in matches if m["league"] == league and m["home"] == home
             and m["away"] == away and
             abs((dt.datetime.fromisoformat(m["kickoff_utc"]) - when).total_seconds()) < 60]
    if len(found) != 1:
        raise ValueError("Fixture not independently verified")
    return found[0]


def submit(payload):
    now = time.time()
    with LOCK, connect() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM jobs WHERE created < ?", (now - RETENTION_SECONDS,))
        # Identical requests share one existing queued/running/completed job.
        # This avoids refitting all models for repeated button presses and
        # prevents duplicate requests from consuming the global compute quota.
        request_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        existing = db.execute("SELECT id FROM jobs WHERE request=? AND state IN ('queued','running','complete') ORDER BY created DESC LIMIT 1", (request_json,)).fetchone()
        if existing is not None:
            db.rollback()
            return existing['id']
        hourly = db.execute("SELECT count(*) FROM jobs WHERE created > ?", (now - 3600,)).fetchone()[0]
        daily = db.execute("SELECT count(*) FROM jobs WHERE created > ?", (now - 86400,)).fetchone()[0]
        pending = db.execute("SELECT count(*) FROM jobs WHERE state IN ('queued','running')").fetchone()[0]
        if hourly >= MAX_PER_HOUR or daily >= MAX_PER_DAY or pending >= MAX_PENDING:
            db.rollback()
            raise OverflowError("Compute quota or queue capacity reached")
        job_id = secrets.token_urlsafe(24)
        db.execute("INSERT INTO jobs(id,created,updated,state,request) VALUES (?,?,?,?,?)",
                   (job_id, now, now, "queued", request_json))
        db.commit()
        return job_id


def get_job(job_id):
    if not isinstance(job_id, str) or len(job_id) > 128:
        return None
    with connect() as db:
        row = db.execute("SELECT id,state,result,error FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            return None
        output = {"job_id": row["id"], "status": row["state"]}
        if row["state"] == "complete":
            output["preview"] = json.loads(row["result"])
        if row["state"] == "failed":
            output["error"] = row["error"] or "Preview failed"
        return output


def process_one():
    with LOCK, connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT id,request FROM jobs WHERE state='queued' ORDER BY created LIMIT 1").fetchone()
        if row is None:
            db.rollback()
            return False
        db.execute("UPDATE jobs SET state='running',updated=? WHERE id=?", (time.time(), row["id"]))
        db.commit()
    try:
        data = json.loads(row["request"])
        fixture = validate_fixture(data["league"], data["home"], data["away"], data["kickoff_utc"])
        result = preview(fixture["league"], fixture["home"], fixture["away"], fixture["kickoff_utc"], fitted_cache=FITTED_CACHE)
        result["fixture_verified"] = True
        result["provider_match_id"] = fixture["provider_match_id"]
        result["warning"] = "Fresh provider-verified preview, not an archived forecast."
        serialized = json.dumps(result, default=json_native)
        with connect() as db:
            db.execute("UPDATE jobs SET state='complete',result=?,updated=? WHERE id=?",
                       (serialized, time.time(), row["id"]))
            db.commit()
    except Exception:
        with connect() as db:
            db.execute("UPDATE jobs SET state='failed',error=?,updated=? WHERE id=?",
                       ("Fixture verification or model fitting failed", time.time(), row["id"]))
            db.commit()
    return True


def worker():
    with connect() as db:
        db.execute("UPDATE jobs SET state='queued' WHERE state='running'")
        db.commit()
    while True:
        if not process_one():
            time.sleep(1)


def start_worker():
    thread = threading.Thread(target=worker, name="matchlab-preview-worker", daemon=True)
    thread.start()
    return thread
