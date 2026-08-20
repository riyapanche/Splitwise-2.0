import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "splitwise.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                person_name TEXT NOT NULL,
                UNIQUE(group_id, person_name)
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                description TEXT,
                amount REAL NOT NULL,
                paid_by TEXT NOT NULL,
                date TEXT NOT NULL,
                source TEXT NOT NULL CHECK(source IN ('manual', 'scan'))
            );

            CREATE TABLE IF NOT EXISTS transaction_assignees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
                person_name TEXT NOT NULL,
                amount REAL NOT NULL,
                UNIQUE(transaction_id, person_name)
            );

            CREATE TABLE IF NOT EXISTS transaction_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
                item_name TEXT NOT NULL,
                item_price REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS transaction_item_splits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL REFERENCES transaction_items(id) ON DELETE CASCADE,
                person_name TEXT NOT NULL,
                amount REAL NOT NULL,
                UNIQUE(item_id, person_name)
            );

            CREATE INDEX IF NOT EXISTS idx_transactions_group_date
            ON transactions(group_id, date);
            """
        )
        conn.commit()
    finally:
        conn.close()


def seed_sample_data() -> None:
    conn = get_connection()
    try:
        group_count = conn.execute("SELECT COUNT(*) AS count FROM groups").fetchone()["count"]
        if group_count:
            return

        conn.execute("INSERT INTO groups (name) VALUES (?)", ("Trip to Chicago",))
        group_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.executemany(
            "INSERT INTO group_members (group_id, person_name) VALUES (?, ?)",
            [(group_id, "Alice"), (group_id, "Bob"), (group_id, "Cara")],
        )

        conn.execute(
            "INSERT INTO groups (name) VALUES (?)",
            ("Apartment Expenses",),
        )
        group_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.executemany(
            "INSERT INTO group_members (group_id, person_name) VALUES (?, ?)",
            [(group_id, "Drew"), (group_id, "Eli")],
        )
        conn.commit()
    finally:
        conn.close()
