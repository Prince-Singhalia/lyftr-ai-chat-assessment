"""Copy the existing file-backed SQLite history into an empty PostgreSQL DB."""

import argparse
import sqlite3
from pathlib import Path
from . import database


def migrate(source_path: str | Path) -> int:
    source = Path(source_path)
    if not source.is_file():
        raise ValueError("SQLite source file does not exist")
    if database._backend(database.get_settings().database_url.strip()) != "postgres":
        raise ValueError("DATABASE_URL must point to PostgreSQL for this migration")

    database.init_db()
    source_db = sqlite3.connect(str(source))
    source_db.row_factory = sqlite3.Row
    try:
        try:
            rows = source_db.execute(
                "SELECT id, session_id, role, content, metadata, created_at FROM messages ORDER BY id"
            )
        except sqlite3.Error:
            raise ValueError("SQLite source does not contain the expected messages table") from None

        with database.transaction() as target:
            existing = target.execute("SELECT COUNT(*) AS count FROM messages").fetchone()["count"]
            if existing:
                raise ValueError("PostgreSQL messages table must be empty; no source data was copied")

            count = 0
            for row in rows:
                target.execute(
                    "INSERT INTO messages(id, session_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (row["id"], row["session_id"], row["role"], row["content"], row["metadata"], row["created_at"]),
                )
                count += 1

            target.execute(
                "SELECT setval(pg_get_serial_sequence('messages', 'id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM messages"
            )
        return count
    finally:
        source_db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy SQLite conversation history into PostgreSQL without modifying the source.")
    parser.add_argument("sqlite_file", help="Path to the existing SQLite database file")
    args = parser.parse_args()
    try:
        count = migrate(args.sqlite_file)
    except (ValueError, database.DatabaseError):
        parser.exit(1, "Migration failed. Check DATABASE_URL, source schema, and that the PostgreSQL messages table is empty.\n")
    print(f"Copied {count} message rows. The SQLite source file was left unchanged.")


if __name__ == "__main__":
    main()
