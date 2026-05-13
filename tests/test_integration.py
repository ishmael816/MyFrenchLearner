# tests/test_integration.py
import datetime
import os
import tempfile
from pathlib import Path
from frenchlearner.db import init_db, get_connection
from frenchlearner.vocab import VocabManager
from frenchlearner.archive import Archiver


class TestFullFlow:
    """端到端集成测试"""

    def test_full_session_flow(self):
        """完整学习流程：生成 → 对话 → 标记生词 → 归档"""
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "test.db")
        session_dir = os.path.join(tmpdir, "sessions")

        init_db(db_path)
        vocab_mgr = VocabManager(db_path)
        archiver = Archiver(db_path, session_dir)

        # 模拟 session
        session_id = "test-session-1"
        now = datetime.datetime.now().isoformat()
        conn = get_connection(db_path)
        conn.execute(
            "INSERT INTO sessions (id, level, text, title, created_at) VALUES (?,?,?,?,?)",
            (session_id, "A2", "Marie se promène dans le parc.", "在公园", now),
        )
        conn.commit()
        conn.close()

        # 标记生词
        vocab_mgr.add(session_id, "se promène", "散步")
        vocab_mgr.add(session_id, "le parc", "公园")

        words = vocab_mgr.list_by_session(session_id)
        assert len(words) == 2
        assert words[0]["word"] in ["se promène", "le parc"]
        assert words[0]["translation"] in ["散步", "公园"]

        # 归档
        archiver.archive_session(session_id)
        path = archiver.export_markdown(session_id)

        assert os.path.exists(path)
        content = Path(path).read_text(encoding="utf-8")
        assert "Marie se promène" in content
        assert "散步" in content
        assert "公园" in content

    def test_vocab_deduplication(self):
        """同一词同 session 内去重，但跨 session 独立"""
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "test.db")
        init_db(db_path)
        vm = VocabManager(db_path)

        now = datetime.datetime.now().isoformat()
        conn = get_connection(db_path)
        conn.execute(
            "INSERT INTO sessions (id, level, text, title, created_at) VALUES (?,?,?,?,?)",
            ("s1", "A2", ".", ".", now),
        )
        conn.execute(
            "INSERT INTO sessions (id, level, text, title, created_at) VALUES (?,?,?,?,?)",
            ("s2", "B1", ".", ".", now),
        )
        conn.commit()
        conn.close()

        vm.add("s1", "manger", "吃")
        vm.add("s1", "manger", "吃")  # 同 session 内去重
        vm.add("s2", "manger", "吃")  # 跨 session 独立，各自保存

        assert len(vm.list_by_session("s1")) == 1
        assert len(vm.list_by_session("s2")) == 1
        assert len(vm.list_all()) == 2  # 跨 session 各自一条

    def test_dialogue_archive_integration(self):
        """对话记录集成到归档"""
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "test.db")
        session_dir = os.path.join(tmpdir, "sessions")

        init_db(db_path)
        archiver = Archiver(db_path, session_dir)

        # 创建会话和对话记录
        session_id = "test-dialogue-1"
        now = datetime.datetime.now().isoformat()
        conn = get_connection(db_path)
        conn.execute(
            "INSERT INTO sessions (id, level, text, title, created_at) VALUES (?,?,?,?,?)",
            (session_id, "B1", "Il fait beau aujourd'hui.", "天气", now),
        )
        conn.execute(
            "INSERT INTO dialogue_log (session_id, role, content, created_at) VALUES (?,?,?,?)",
            (session_id, "user", "Il fait beau 是什么意思？", now),
        )
        conn.execute(
            "INSERT INTO dialogue_log (session_id, role, content, created_at) VALUES (?,?,?,?)",
            (session_id, "assistant", "天气很好的意思。", now),
        )
        conn.commit()
        conn.close()

        # 导出为 Markdown
        path = archiver.export_markdown(session_id)

        assert os.path.exists(path)
        content = Path(path).read_text(encoding="utf-8")
        assert "Il fait beau" in content
        assert "天气" in content
        assert "Il fait beau 是什么意思？" in content
        assert "天气很好的意思。" in content

    def test_multiple_sessions_isolated_vocabs(self):
        """多个会话的生词隔离"""
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "test.db")
        init_db(db_path)
        vm = VocabManager(db_path)

        now = datetime.datetime.now().isoformat()
        conn = get_connection(db_path)
        conn.execute(
            "INSERT INTO sessions (id, level, text, title, created_at) VALUES (?,?,?,?,?)",
            ("session1", "A2", "Text 1", "Title 1", now),
        )
        conn.execute(
            "INSERT INTO sessions (id, level, text, title, created_at) VALUES (?,?,?,?,?)",
            ("session2", "B1", "Text 2", "Title 2", now),
        )
        conn.commit()
        conn.close()

        # 为两个会话添加生词
        vm.add("session1", "chat", "猫")
        vm.add("session1", "chien", "狗")
        vm.add("session2", "maison", "房子")
        vm.add("session2", "jardin", "花园")

        # 验证隔离
        s1_words = vm.list_by_session("session1")
        s2_words = vm.list_by_session("session2")

        assert len(s1_words) == 2
        assert len(s2_words) == 2

        s1_word_list = [w["word"] for w in s1_words]
        s2_word_list = [w["word"] for w in s2_words]

        assert "chat" in s1_word_list
        assert "chien" in s1_word_list
        assert "maison" in s2_word_list
        assert "jardin" in s2_word_list

        # 全量查询验证
        all_words = vm.list_all()
        assert len(all_words) == 4
