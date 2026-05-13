# frenchlearner/db.py
import sqlite3
import os

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    level       TEXT NOT NULL DEFAULT 'A2',
    text        TEXT NOT NULL,
    title       TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'active',
    word_count  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    closed_at   TEXT
);

CREATE TABLE IF NOT EXISTS vocabulary (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    word         TEXT NOT NULL,
    lemma        TEXT NOT NULL,
    translation  TEXT NOT NULL DEFAULT '',
    note         TEXT NOT NULL DEFAULT '',
    session_id   TEXT NOT NULL,
    level        TEXT NOT NULL DEFAULT 'A2',
    review_count INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    UNIQUE(lemma, translation)
);

CREATE TABLE IF NOT EXISTS dialogue_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role       TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
