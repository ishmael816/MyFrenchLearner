# frenchlearner/vocab.py
import datetime
from frenchlearner.db import get_connection


def _to_lemma(word: str) -> str:
    """简单词元化：转小写、规范化口音符号"""
    import unicodedata
    w = word.strip().lower()
    # Normalize accents: é → e, è → e, ê → e, etc.
    w = ''.join(
        c for c in unicodedata.normalize('NFD', w)
        if unicodedata.category(c) != 'Mn'
    )
    return w


class VocabManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def add(self, session_id: str, word: str, translation: str, note: str = "", level: str = "A2") -> None:
        conn = get_connection(self.db_path)
        try:
            lemma = _to_lemma(word)
            now = datetime.datetime.now().isoformat()
            conn.execute(
                """INSERT OR IGNORE INTO vocabulary
                   (word, lemma, translation, note, session_id, level, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (word, lemma, translation, note, session_id, level, now),
            )
            conn.commit()
        finally:
            conn.close()

    def remove(self, session_id: str, word: str) -> None:
        conn = get_connection(self.db_path)
        try:
            conn.execute(
                "DELETE FROM vocabulary WHERE session_id = ? AND word = ?",
                (session_id, word),
            )
            conn.commit()
        finally:
            conn.close()

    def list_by_session(self, session_id: str) -> list[dict]:
        conn = get_connection(self.db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM vocabulary WHERE session_id = ? ORDER BY created_at",
                (session_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def list_all(self) -> list[dict]:
        conn = get_connection(self.db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM vocabulary ORDER BY created_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def export_json(self) -> list[dict]:
        conn = get_connection(self.db_path)
        try:
            rows = conn.execute(
                "SELECT word, lemma, translation, note, level, review_count, created_at FROM vocabulary ORDER BY created_at"
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def stats(self) -> dict:
        conn = get_connection(self.db_path)
        try:
            total = conn.execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0]
            by_level = {}
            for row in conn.execute("SELECT level, COUNT(*) as cnt FROM vocabulary GROUP BY level"):
                by_level[row["level"]] = row["cnt"]
            return {"total": total, "by_level": by_level}
        finally:
            conn.close()
