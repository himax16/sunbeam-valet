import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sunbeam_valet.dashboard.models import Bug

DB_PATH = Path.home() / ".cache" / "sunbeam-valet"


@contextmanager
def _connect():
    DB_PATH.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH / "cache.db"))
    db.row_factory = sqlite3.Row
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    with _connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS bugs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT '',
                importance TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'launchpad',
                synced_at REAL NOT NULL DEFAULT 0.0
            );
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at REAL NOT NULL,
                finished_at REAL,
                status TEXT NOT NULL DEFAULT 'running',
                bugs_synced INTEGER NOT NULL DEFAULT 0,
                error TEXT
            );
            CREATE TABLE IF NOT EXISTS judgements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bug_id TEXT NOT NULL,
                bug_title TEXT NOT NULL,
                bug_description TEXT NOT NULL,
                bug_source TEXT NOT NULL DEFAULT 'launchpad',
                verdict TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 0.0,
                summary TEXT NOT NULL DEFAULT '',
                concerns TEXT NOT NULL DEFAULT '',
                raw_output TEXT NOT NULL DEFAULT '',
                judged_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_judgements_bug_id ON judgements(bug_id);
            """
        )
        db.commit()


def clear_bugs() -> int:
    with _connect() as db:
        cursor = db.execute("DELETE FROM bugs")
        db.commit()
        return cursor.rowcount


def count_bugs() -> int:
    with _connect() as db:
        row = db.execute("SELECT COUNT(*) as cnt FROM bugs").fetchone()
        return row["cnt"]


def list_bugs(limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
    with _connect() as db:
        rows = db.execute(
            "SELECT * FROM bugs ORDER BY synced_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]


def upsert_bugs(bugs: list[Bug]) -> int:
    now = time.time()
    count = 0
    with _connect() as db:
        for bug in bugs:
            db.execute(
                "INSERT OR REPLACE INTO bugs"
                " (id, title, status, importance, description, url, source, synced_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    bug.id,
                    bug.title,
                    bug.status,
                    bug.importance,
                    bug.description,
                    bug.url,
                    bug.source,
                    now,
                ),
            )
            count += 1
        db.commit()
    return count


def replace_bugs(bugs: list[Bug]) -> int:
    clear_bugs()
    return upsert_bugs(bugs)


def start_sync() -> int:
    with _connect() as db:
        cursor = db.execute(
            "INSERT INTO sync_log (started_at, status) VALUES (?, 'running')",
            (time.time(),),
        )
        db.commit()
        return cursor.lastrowid


def finish_sync(log_id: int, bugs_synced: int, error: str | None = None) -> None:
    with _connect() as db:
        db.execute(
            "UPDATE sync_log"
            " SET finished_at = ?, status = ?, bugs_synced = ?, error = ?"
            " WHERE id = ?",
            (time.time(), "error" if error else "success", bugs_synced, error, log_id),
        )
        db.commit()


def get_last_sync() -> dict[str, Any] | None:
    with _connect() as db:
        row = db.execute("SELECT * FROM sync_log ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None


def get_sync_logs(limit: int = 20) -> list[dict[str, Any]]:
    with _connect() as db:
        rows = db.execute(
            "SELECT * FROM sync_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def save_judgement(
    bug_id: str,
    bug_title: str,
    bug_description: str,
    bug_source: str,
    verdict: str,
    confidence: float,
    summary: str,
    concerns: list[str],
    raw_output: str,
) -> int:
    with _connect() as db:
        cursor = db.execute(
            "INSERT INTO judgements"
            " (bug_id, bug_title, bug_description, bug_source,"
            " verdict, confidence, summary, concerns, raw_output, judged_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                bug_id,
                bug_title,
                bug_description,
                bug_source,
                verdict,
                confidence,
                summary,
                ", ".join(concerns) if concerns else "",
                raw_output,
                time.time(),
            ),
        )
        db.commit()
        return cursor.lastrowid


def get_judgements(bug_id: str, limit: int = 10) -> list[dict[str, Any]]:
    with _connect() as db:
        rows = db.execute(
            "SELECT * FROM judgements WHERE bug_id = ? ORDER BY judged_at DESC LIMIT ?",
            (bug_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]
