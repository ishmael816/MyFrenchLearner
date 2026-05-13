# tests/test_archive.py
import datetime
import os
import tempfile
from pathlib import Path
from frenchlearner.db import init_db, get_connection
from frenchlearner.archive import Archiver


class TestArchiver:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.session_dir = os.path.join(self.tmpdir, "sessions")
        init_db(self.db_path)
        self.archiver = Archiver(self.db_path, self.session_dir)
        self.now = datetime.datetime.now().isoformat()
        conn = get_connection(self.db_path)
        conn.execute(
            "INSERT INTO sessions (id, level, text, title, created_at) VALUES (?,?,?,?,?)",
            ("s1", "A2", "Bonjour le monde.", "问候", self.now),
        )
        conn.execute(
            "INSERT INTO vocabulary (word, lemma, translation, session_id, level, created_at) VALUES (?,?,?,?,?,?)",
            ("Bonjour", "bonjour", "你好", "s1", "A2", self.now),
        )
        conn.execute(
            "INSERT INTO dialogue_log (session_id, role, content, created_at) VALUES (?,?,?,?)",
            ("s1", "user", "Bonjour 是什么意思？", self.now),
        )
        conn.commit()
        conn.close()

    def test_archive_session_updates_status(self):
        self.archiver.archive_session("s1")
        conn = get_connection(self.db_path)
        row = conn.execute("SELECT status, closed_at FROM sessions WHERE id=?", ("s1",)).fetchone()
        assert row["status"] == "archived"
        assert row["closed_at"] is not None
        conn.close()

    def test_export_markdown_creates_file(self):
        path = self.archiver.export_markdown("s1")
        assert os.path.exists(path)
        content = Path(path).read_text(encoding="utf-8")
        assert "问候" in content
        assert "Bonjour le monde" in content

    def test_export_markdown_contains_vocab(self):
        path = self.archiver.export_markdown("s1")
        content = Path(path).read_text(encoding="utf-8")
        assert "Bonjour" in content
        assert "你好" in content

    def test_export_markdown_contains_dialogue(self):
        path = self.archiver.export_markdown("s1")
        content = Path(path).read_text(encoding="utf-8")
        assert "Bonjour 是什么意思？" in content
