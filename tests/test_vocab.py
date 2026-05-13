# tests/test_vocab.py
import datetime
import os
import tempfile
from frenchlearner.db import init_db, get_connection
from frenchlearner.vocab import VocabManager


class TestVocabManager:
    def setup_method(self):
        self.db_path = os.path.join(tempfile.mkdtemp(), "test.db")
        init_db(self.db_path)
        self.vm = VocabManager(self.db_path)
        self.now = datetime.datetime.now().isoformat()
        conn = get_connection(self.db_path)
        conn.execute(
            "INSERT INTO sessions (id, level, text, title, created_at) VALUES (?,?,?,?,?)",
            ("s1", "A2", "Bonjour le monde.", "Test", self.now),
        )
        conn.commit()
        conn.close()

    def test_add_vocab(self):
        self.vm.add("s1", "se promène", "散步")
        words = self.vm.list_by_session("s1")
        assert len(words) == 1
        assert words[0]["word"] == "se promène"
        assert words[0]["lemma"] == "se promene"
        assert words[0]["translation"] == "散步"

    def test_add_duplicate_ignored(self):
        self.vm.add("s1", "manger", "吃")
        self.vm.add("s1", "manger", "吃")
        words = self.vm.list_by_session("s1")
        assert len(words) == 1

    def test_remove_vocab(self):
        self.vm.add("s1", "parler", "说话")
        self.vm.add("s1", "manger", "吃")
        self.vm.remove("s1", "parler")
        words = self.vm.list_by_session("s1")
        assert len(words) == 1
        assert words[0]["word"] == "manger"

    def test_list_all(self):
        self.vm.add("s1", "parler", "说话")
        self.vm.add("s1", "manger", "吃")
        all_words = self.vm.list_all()
        assert len(all_words) == 2

    def test_export_json(self):
        self.vm.add("s1", "parler", "说话", note="动词")
        data = self.vm.export_json()
        assert len(data) == 1
        assert data[0]["word"] == "parler"
        assert data[0]["note"] == "动词"

    def test_stats(self):
        self.vm.add("s1", "parler", "说话")
        self.vm.add("s1", "manger", "吃")
        self.vm.add("s1", "dormir", "睡觉")
        stats = self.vm.stats()
        assert stats["total"] == 3
