# frenchlearner/archive.py
import datetime
import os
from pathlib import Path
from frenchlearner.db import get_connection


class Archiver:
    def __init__(self, db_path: str, session_dir: str):
        self.db_path = db_path
        self.session_dir = session_dir

    def archive_session(self, session_id: str) -> None:
        conn = get_connection(self.db_path)
        try:
            now = datetime.datetime.now().isoformat()
            conn.execute(
                "UPDATE sessions SET status = 'archived', closed_at = ? WHERE id = ?",
                (now, session_id),
            )
            conn.commit()
        finally:
            conn.close()

    def export_markdown(self, session_id: str) -> str:
        conn = get_connection(self.db_path)
        try:
            session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if not session:
                raise ValueError(f"会话不存在: {session_id}")

            vocab_rows = conn.execute(
                "SELECT word, translation, note FROM vocabulary WHERE session_id = ? ORDER BY created_at",
                (session_id,),
            ).fetchall()

            dialogue_rows = conn.execute(
                "SELECT role, content FROM dialogue_log WHERE session_id = ? ORDER BY created_at",
                (session_id,),
            ).fetchall()

            md = self._build_markdown(dict(session), [dict(r) for r in vocab_rows], [dict(r) for r in dialogue_rows])

            os.makedirs(self.session_dir, exist_ok=True)
            ts = datetime.datetime.fromisoformat(session["created_at"]).strftime("%Y-%m-%d-%H%M")
            filename = f"{ts}-{session['id'][:8]}.md"
            path = os.path.join(self.session_dir, filename)
            Path(path).write_text(md, encoding="utf-8")
            return path
        finally:
            conn.close()

    def _build_markdown(self, session: dict, vocab: list[dict], dialogue: list[dict]) -> str:
        level = session.get("level", "?")
        title = session.get("title", "Sans titre")
        text = session.get("text", "")

        lines = [
            f"# Session {session['created_at'][:10]} {level} — {title}",
            "",
            "## Texte",
            "> " + text.replace("\n", "\n> "),
            "",
            "## Vocabulaire",
        ]
        if vocab:
            lines.append("| Mot | Traduction | Note |")
            lines.append("|-----|-----------|------|")
            for v in vocab:
                lines.append(f"| {v['word']} | {v['translation']} | {v.get('note', '')} |")
        else:
            lines.append("（无标记生词）")

        lines.append("")
        lines.append("## Dialogue")
        for d in dialogue:
            role_label = "🧑" if d["role"] == "user" else "🤖"
            lines.append(f"- **{role_label}**: {d['content']}")

        lines.append("")
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        lines.append(f"---\n*Généré le {now}*")
        return "\n".join(lines)
