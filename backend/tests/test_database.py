import os
import sqlite3
import uuid

import pytest
from urllib.parse import parse_qs, urlsplit

from app import database
from app.config import get_settings
from app.main import create_app
from app.schemas import ChatRequest
from app.api.routes import chat, history


def test_sqlite_migration_is_idempotent_and_preserves_history(client):
    metadata = {"model": "test-model", "input_tokens": 12, "output_tokens": 4}
    database.store_exchange("persist-me", "question", "answer", metadata)

    database.init_db()

    assert database.fetch_messages("persist-me") == [
        {"role": "user", "content": "question", "metadata": None},
        {"role": "assistant", "content": "answer", "metadata": metadata},
    ]
    with database.connect() as db:
        assert db.execute("SELECT version FROM schema_migrations").fetchall()[0]["version"] == 1


def test_sqlite_history_remains_session_isolated(client):
    database.store_exchange("session-a", "a question", "a answer", {"input_tokens": 2})
    database.store_exchange("session-b", "b question", "b answer", {"input_tokens": 3})

    assert [item["content"] for item in database.fetch_messages("session-a")] == ["a question", "a answer"]
    assert [item["content"] for item in database.fetch_messages("session-b")] == ["b question", "b answer"]


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("postgresql://dbuser:placeholder@ep-example.neon.tech/chat?sslmode=require", "require"),
        ("postgres://dbuser:placeholder@ep-example.neon.tech/chat", "require"),
        ("postgresql+psycopg://dbuser:placeholder@ep-example.neon.tech/chat", "require"),
    ],
)
def test_postgres_url_normalization_requires_tls(url, expected):
    normalized = database._postgres_dsn(url)

    assert normalized.startswith("postgresql://")
    assert parse_qs(urlsplit(normalized).query)["sslmode"] == [expected]


@pytest.mark.parametrize("mode", ["disable", "allow", "prefer"])
def test_postgres_url_rejects_ssl_downgrade(mode):
    with pytest.raises(ValueError, match="must require SSL"):
        database._postgres_dsn(f"postgresql://u:p@db.example/chat?sslmode={mode}")


def test_postgres_adapter_translates_sql_placeholders_and_sanitizes_errors():
    class FakeConnection:
        query = None

        def execute(self, query, parameters):
            self.query = (query, parameters)
            return "cursor"

    raw = FakeConnection()
    connection = database._Connection(raw, "postgres")
    assert connection.execute("SELECT * FROM messages WHERE session_id = ?", ("s",)) == "cursor"
    assert raw.query == ("SELECT * FROM messages WHERE session_id = %s", ("s",))

    class LeakyErrorConnection:
        def execute(self, query, parameters):
            raise RuntimeError("postgresql://user:secret@host/db")

    with pytest.raises(database.DatabaseError) as error:
        database._Connection(LeakyErrorConnection(), "postgres").execute("SELECT 1")
    assert "secret" not in str(error.value)
    assert "postgresql://" not in str(error.value)


def test_database_connection_failure_is_safe_and_never_falls_back(monkeypatch):
    url = "postgresql://dbuser:placeholder@invalid.example/chat?sslmode=disable"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    try:
        assert database.db_reachable() is False
        with pytest.raises(database.DatabaseError, match="database connection failed") as error:
            database.connect()
        assert "invalid.example" not in str(error.value)
        assert "placeholder" not in str(error.value)
    finally:
        get_settings.cache_clear()


@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_DATABASE_URL"), reason="set TEST_POSTGRES_DATABASE_URL for PostgreSQL integration coverage")
def test_postgres_persistence_survives_reinitialization_and_isolates_sessions(monkeypatch):
    url = os.environ["TEST_POSTGRES_DATABASE_URL"]
    session_a = f"pytest-{uuid.uuid4()}-a"
    session_b = f"pytest-{uuid.uuid4()}-b"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    try:
        database.init_db()
        database.store_exchange(session_a, "postgres question", "postgres answer", {"input_tokens": 7, "output_tokens": 2})
        database.store_exchange(session_b, "other question", "other answer", {"input_tokens": 4, "output_tokens": 2})
        database.init_db()

        assert database.db_reachable()
        assert [row["content"] for row in database.fetch_messages(session_a)] == ["postgres question", "postgres answer"]
        assert [row["content"] for row in database.fetch_messages(session_b)] == ["other question", "other answer"]
        assert database.fetch_messages(session_a)[1]["metadata"]["input_tokens"] == 7

        calls = []
        app = create_app()

        def provider(messages, api_key, model=None):
            calls.append(messages)
            return {"choices": [{"message": {"content": "postgres cached response"}}], "usage": {"prompt_tokens": 8, "completion_tokens": 3}}

        app.state.gateway._call_litellm = provider
        request = type("Request", (), {"app": app})()
        first = chat(ChatRequest(session_id=session_a + "-cache", message="shared prompt"), request, None)
        second = chat(ChatRequest(session_id=session_b + "-cache", message="shared prompt"), request, None)
        assert first.metadata.resolution_source == "LIVE_INFERENCE"
        assert second.metadata.resolution_source == "LLM_CACHE"
        assert second.metadata.input_tokens == 8
        assert len(calls) == 1

        create_app()
        assert len(history(session_a).messages) == 2
        assert history(session_b).messages[1].metadata["output_tokens"] == 2
        assert [row["content"] for row in database.fetch_messages(session_a + "-cache")] == ["shared prompt", "postgres cached response"]
    finally:
        if database.db_reachable():
            with database.transaction() as db:
                db.execute(
                    "DELETE FROM messages WHERE session_id IN (?, ?, ?, ?)",
                    (session_a, session_b, session_a + "-cache", session_b + "-cache"),
                )
        get_settings.cache_clear()


@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_DATABASE_URL"), reason="set TEST_POSTGRES_DATABASE_URL for PostgreSQL integration coverage")
def test_sqlite_history_migrates_to_empty_postgres_without_changing_source(monkeypatch, tmp_path):
    from app.migrate_sqlite import migrate

    url = os.environ["TEST_POSTGRES_DATABASE_URL"]
    session_id = f"pytest-migration-{uuid.uuid4()}"
    sqlite_file = tmp_path / "source.db"
    with sqlite3.connect(sqlite_file) as source:
        source.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, metadata TEXT, created_at TEXT NOT NULL)")
        source.execute("INSERT INTO messages(session_id, role, content, metadata, created_at) VALUES (?, 'user', ?, NULL, ?)", (session_id, "before", "timestamp"))
        source.execute("INSERT INTO messages(session_id, role, content, metadata, created_at) VALUES (?, 'assistant', ?, ?, ?)", (session_id, "after", '{"input_tokens":5}', "timestamp"))

    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    try:
        assert migrate(sqlite_file) == 2
        assert [row["content"] for row in database.fetch_messages(session_id)] == ["before", "after"]
        assert database.fetch_messages(session_id)[1]["metadata"] == {"input_tokens": 5}
        with pytest.raises(ValueError, match="must be empty"):
            migrate(sqlite_file)
        with sqlite3.connect(sqlite_file) as source:
            assert source.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 2
    finally:
        if database.db_reachable():
            with database.transaction() as db:
                db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        get_settings.cache_clear()
