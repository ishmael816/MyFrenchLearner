# tests/test_db.py
import sqlite3
import os
import tempfile
from frenchlearner.db import init_db, get_connection


class TestDB:
    def test_init_db_creates_tables(self):
        """init_db 创建三张表"""
        db_path = os.path.join(tempfile.mkdtemp(), "test.db")
        try:
            init_db(db_path)
            conn = get_connection(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            assert "sessions" in tables
            assert "vocabulary" in tables
            assert "dialogue_log" in tables
            conn.close()
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_sessions_table_schema(self):
        """sessions 表结构正确"""
        db_path = os.path.join(tempfile.mkdtemp(), "test.db")
        try:
            init_db(db_path)
            conn = get_connection(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(sessions)")
            cols = {row[1]: row[2] for row in cursor.fetchall()}
            assert cols["id"] == "TEXT"
            assert cols["level"] == "TEXT"
            assert cols["text"] == "TEXT"
            assert cols["status"] == "TEXT"
            conn.close()
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_vocabulary_unique_constraint(self):
        """lemma + translation 唯一约束"""
        db_path = os.path.join(tempfile.mkdtemp(), "test.db")
        try:
            init_db(db_path)
            conn = get_connection(db_path)
            # Create a session first
            conn.execute(
                "INSERT INTO sessions (id, text, created_at) VALUES (?,?,?)",
                ("s1", "test text", "2024-01-01"),
            )
            conn.execute(
                "INSERT INTO sessions (id, text, created_at) VALUES (?,?,?)",
                ("s2", "test text", "2024-01-01"),
            )
            conn.commit()

            conn.execute(
                "INSERT INTO vocabulary (word, lemma, translation, session_id, created_at) VALUES (?,?,?,?,?)",
                ("se promène", "se promener", "散步", "s1", "2024-01-01"),
            )
            conn.commit()
            try:
                conn.execute(
                    "INSERT INTO vocabulary (word, lemma, translation, session_id, created_at) VALUES (?,?,?,?,?)",
                    ("se promener", "se promener", "散步", "s1", "2024-01-02"),
                )
                conn.commit()
                assert False, "应抛出 IntegrityError"
            except sqlite3.IntegrityError:
                pass
            conn.close()
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_idempotent_init(self):
        """多次 init_db 不报错"""
        db_path = os.path.join(tempfile.mkdtemp(), "test.db")
        try:
            init_db(db_path)
            init_db(db_path)
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
