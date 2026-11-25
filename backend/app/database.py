import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .config import get_settings


class DatabaseError(RuntimeError):
    """Database failure with a message that is safe to expose in server logs."""


def _backend(url: str) -> str:
    if url.startswith("sqlite:///"):
        return "sqlite"
    if url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
        return "postgres"
    raise ValueError("DATABASE_URL must use sqlite:/// or postgresql://")


def _sqlite_path(url: str) -> str:
    path = url[len("sqlite:///"):]
    if not path or path == ":memory:":
        raise ValueError("DATABASE_URL must point to a file-backed SQLite database")
    return path


def _postgres_dsn(url: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    elif url.startswith("postgresql+psycopg://"):
        url = "postgresql://" + url[len("postgresql+psycopg://"):]

    parts = urlsplit(url)
    if not parts.hostname or not parts.path.strip("/"):
        raise ValueError("DATABASE_URL must include a PostgreSQL host and database name")
    query = parse_qsl(parts.query, keep_blank_values=True)
    ssl_modes = [value.lower() for key, value in query if key.lower() == "sslmode"]
    if ssl_modes and any(mode not in {"require", "verify-ca", "verify-full"} for mode in ssl_modes):
        raise ValueError("PostgreSQL DATABASE_URL must require SSL")
    if not ssl_modes:
        query.append(("sslmode", "require"))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class _Connection:
    """Small DB-API adapter shared by the existing SQLite SQL and psycopg."""

    def __init__(self, raw: Any, backend: str) -> None:
        self._raw = raw
        self._backend = backend

    def execute(self, sql: str, parameters: tuple[Any, ...] = ()) -> Any:
        if self._backend == "postgres":
            sql = sql.replace("?", "%s")
        try:
            return self._raw.execute(sql, parameters)
        except Exception:
            raise DatabaseError("database query failed") from None

    def commit(self) -> None:
        try:
            self._raw.commit()
        except Exception:
            raise DatabaseError("database commit failed") from None

    def rollback(self) -> None:
        try:
            self._raw.rollback()
        except Exception:
            raise DatabaseError("database rollback failed") from None

    def close(self) -> None:
        self._raw.close()

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        try:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
        finally:
            self.close()


def connect() -> _Connection:
    url = get_settings().database_url.strip()
    backend = _backend(url)
    try:
        if backend == "sqlite":
            path = _sqlite_path(url)
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            raw = sqlite3.connect(path, timeout=10)
            raw.row_factory = sqlite3.Row
        else:
            import psycopg
            from psycopg.rows import dict_row

            raw = psycopg.connect(_postgres_dsn(url), row_factory=dict_row, connect_timeout=10)
        return _Connection(raw, backend)
    except Exception:
        # Driver exceptions may contain the connection string; never propagate
        # them into application logs or HTTP error traces.
        raise DatabaseError("database connection failed") from None


def init_db() -> None:
    backend = _backend(get_settings().database_url.strip())
    id_type = "INTEGER PRIMARY KEY AUTOINCREMENT" if backend == "sqlite" else "BIGSERIAL PRIMARY KEY"
    try:
        with connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
            db.execute(f"""CREATE TABLE IF NOT EXISTS messages (
                id {id_type},
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id)")
            db.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?) ON CONFLICT(version) DO NOTHING",
                (1, datetime.now(timezone.utc).isoformat()),
            )
    except DatabaseError:
        raise
    except Exception:
        raise DatabaseError("database schema initialization failed") from None


def db_reachable() -> bool:
    try:
        with connect() as db:
            db.execute("SELECT 1")
        return True
    except (DatabaseError, ValueError):
        return False


@contextmanager
def transaction() -> Iterator[_Connection]:
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
        rows = db.execute(
            "SELECT role, content, metadata FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    return [
        {
            "role": row["role"],
            "content": row["content"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
        }
        for row in rows
    ]


def store_exchange(session_id: str, user_message: str, assistant_message: str, metadata: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with transaction() as db:
        db.execute(
            "INSERT INTO messages(session_id, role, content, metadata, created_at) VALUES (?, 'user', ?, NULL, ?)",
            (session_id, user_message, now),
        )
        db.execute(
            "INSERT INTO messages(session_id, role, content, metadata, created_at) VALUES (?, 'assistant', ?, ?, ?)",
            (session_id, assistant_message, json.dumps(metadata), now),
        )
