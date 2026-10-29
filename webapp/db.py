"""Small SQLite layer (standard library only). Stores check results and feedback, not message text."""
from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, subject TEXT NOT NULL,
    verdict TEXT NOT NULL, probability REAL NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, ref_id INTEGER,
    rating INTEGER NOT NULL, comment TEXT, created_at TEXT NOT NULL);
"""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextmanager
def connection(app):
    conn = sqlite3.connect(str(app.config["DB_PATH"]), timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(app) -> None:
    Path(app.config["DB_PATH"]).parent.mkdir(parents=True, exist_ok=True)
    with connection(app) as conn:
        conn.executescript(SCHEMA)


def message_subject(text: str) -> str:
    """Privacy: store a short fingerprint of a message instead of its content."""
    return "message[%d chars] %s" % (len(text), hashlib.sha256(text.encode("utf-8")).hexdigest()[:8])


def record_check(app, kind: str, subject: str, verdict: str, probability: float) -> int:
    with connection(app) as conn:
        cur = conn.execute("INSERT INTO checks (kind, subject, verdict, probability, created_at) VALUES (?,?,?,?,?)",
                           (kind, subject[:500], verdict, float(probability), _now()))
        return int(cur.lastrowid)


def record_feedback(app, kind: str, rating: int, ref_id=None, comment: str = "") -> int:
    with connection(app) as conn:
        cur = conn.execute("INSERT INTO feedback (kind, ref_id, rating, comment, created_at) VALUES (?,?,?,?,?)",
                           (kind, ref_id, int(rating), (comment or "")[:500], _now()))
        return int(cur.lastrowid)


def get_stats(app) -> dict:
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with connection(app) as conn:
        by_kind = {r["kind"]: r["n"] for r in conn.execute("SELECT kind, COUNT(*) AS n FROM checks GROUP BY kind")}
        by_verdict = {r["verdict"]: r["n"] for r in conn.execute("SELECT verdict, COUNT(*) AS n FROM checks GROUP BY verdict")}
        last_24h = conn.execute("SELECT COUNT(*) AS n FROM checks WHERE created_at >= ?", (since,)).fetchone()["n"]
        ratings = {r["rating"]: r["n"] for r in conn.execute("SELECT rating, COUNT(*) AS n FROM feedback GROUP BY rating")}
    return {
        "total_checks": sum(by_kind.values()), "checks_last_24h": last_24h, "by_kind": by_kind, "by_verdict": by_verdict,
        "feedback": {"helpful": ratings.get(1, 0), "not_helpful": ratings.get(-1, 0)},
    }
