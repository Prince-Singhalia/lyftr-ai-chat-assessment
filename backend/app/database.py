import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from .config import get_settings


def database_path() -> str:
    url = get_settings().database_url
    if url.startswith("sqlite:////"):
        return url[len("sqlite:////") - 1 :]
    if url.startswith("sqlite:///"):
        return url[len("sqlite:///") :]
    return url


def connect() -> sqlite3.Connection:
    path = database_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT,
            created_at TEXT NOT NULL
        )""")
        db.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id)")


def db_reachable() -> bool:
    try:
        with connect() as db:
            db.execute("SELECT 1")
        return True
    except (OSError, sqlite3.Error):
        return False


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    db = connect()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def fetch_messages(session_id: str) -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("SELECT role, content, metadata FROM messages WHERE session_id = ? ORDER BY id", (session_id,)).fetchall()
    return [{"role": row["role"], "content": row["content"], "metadata": json.loads(row["metadata"]) if row["metadata"] else None} for row in rows]


def store_exchange(session_id: str, user_message: str, assistant_message: str, metadata: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with transaction() as db:
        db.execute("INSERT INTO messages(session_id, role, content, metadata, created_at) VALUES (?, 'user', ?, NULL, ?)", (session_id, user_message, now))
        db.execute("INSERT INTO messages(session_id, role, content, metadata, created_at) VALUES (?, 'assistant', ?, ?, ?)", (session_id, assistant_message, json.dumps(metadata), now))

