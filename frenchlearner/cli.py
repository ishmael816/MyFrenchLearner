# frenchlearner/cli.py
import argparse
import datetime
import json
import os
import re
import sys
import uuid

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

from frenchlearner.config import get_config
from frenchlearner.db import init_db, get_connection
from frenchlearner.generator import TextGenerator
from frenchlearner.dialogue import DialogueHandler, ConversationContext
from frenchlearner.vocab import VocabManager
from frenchlearner.archive import Archiver


STYLE = Style.from_dict({
    "prompt": "bold green",
})

LEVELS = ["A1", "A2", "B1", "B2", "C1"]
COMMANDS = ["vocab", "grammar", "next", "level", "done", "help"]


class FrenchCompleter(Completer):
    """支持斜杠命令 + 文本词补全的补全器"""
    def __init__(self):
        self.text_words: list[str] = []

    def set_text_words(self, words: list[str]):
        self.text_words = words

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.lstrip()
        if not text.startswith("/"):
            return

        cmd_text = text[1:]
        parts = cmd_text.split()

        if len(parts) == 1:
            for cmd in COMMANDS:
                if cmd.startswith(parts[0]):
                    yield Completion(cmd, start_position=-len(parts[0]))
        elif len(parts) >= 2 and parts[0] == "vocab":
            sub = parts[1] if len(parts) > 1 else ""
            if len(parts) == 2:
                for subcmd in ["add", "list", "remove"]:
                    if subcmd.startswith(sub):
                        yield Completion(subcmd, start_position=-len(sub))
            elif len(parts) >= 3 and parts[1] in ("add",):
                word_start = parts[2] if len(parts) > 2 else ""
                for w in self.text_words:
                    if w.lower().startswith(word_start.lower()):
                        yield Completion(w, start_position=-len(word_start))


def _extract_words(text: str) -> list[str]:
    """从文本中提取单词用于补全"""
    words = re.findall(r"[A-Za-zÀ-ÿ']{2,}", text)
    seen = set()
    unique = []
    for w in words:
        if w.lower() not in seen:
            seen.add(w.lower())
            unique.append(w)
    return unique


def _init_session(cfg, generator, conn) -> dict:
    level = cfg.default_level
    print(f"\n🎓 FrenchLearner | Niveau: {level}")
    print("─" * cfg.display["text_width"])
    print("\n⏳ Génération du texte en cours...\n")

    gt = generator.generate(level)

    session_id = str(uuid.uuid4())
    now = datetime.datetime.now().isoformat()
    conn.execute(
        "INSERT INTO sessions (id, level, text, title, word_count, created_at) VALUES (?,?,?,?,?,?)",
        (session_id, level, gt.text, gt.title, len(gt.text.split()), now),
    )
    conn.commit()

    print(f"📖 {gt.text}\n")
    print(f"📝 {gt.summary}\n")
    print("─" * cfg.display["text_width"])

    return {
        "id": session_id,
        "level": level,
        "text": gt.text,
        "title": gt.title,
    }


def _handle_command(cmd_line: str, ctx: ConversationContext, handler: DialogueHandler,
                    generator: TextGenerator, vocab_mgr: VocabManager, archiver: Archiver,
                    session: dict, cfg) -> bool:
    """处理斜杠命令。返回 True 继续，False 退出。"""
    parts = cmd_line[1:].split()
    if not parts:
        return True

    cmd = parts[0].lower()

    if cmd == "done":
        _do_done(archiver, session, ctx)
        return False

    elif cmd == "vocab":
        _do_vocab(parts, ctx, vocab_mgr, session)
    elif cmd == "grammar":
        topic = " ".join(parts[1:]) if len(parts) > 1 else ""
        if not topic:
            print("用法: /grammar <语法主题>")
            return True
        question = f"请讲解一下法语语法：{topic}"
        reply = handler.ask(ctx, question)
        print(f"\n🤖 {reply}\n")
    elif cmd == "next":
        level = session["level"]
        print("\n⏳ 生成新文本...\n")
        gt = generator.generate(level)
        session["text"] = gt.text
        session["title"] = gt.title
        ctx.text = gt.text
        ctx.title = gt.title
        print(f"📖 {gt.text}\n")
    elif cmd == "level":
        if len(parts) < 2 or parts[1].upper() not in LEVELS:
            print(f"级别: {', '.join(LEVELS)}")
            return True
        session["level"] = parts[1].upper()
        ctx.level = session["level"]
        print(f"✅ 级别已切换为 {session['level']}")
    elif cmd == "help":
        print("""
/vocab add <词>    标记生词
/vocab list        当前会话生词
/vocab remove <词> 取消标记
/grammar <主题>    语法讲解
/next              换一篇新文本
/level <级别>      切换难度 (A1/B1/C1...)
/done              结束学习并归档
/help              显示此帮助
Ctrl+D             退出
""")
    return True


def _do_vocab(parts, ctx, vocab_mgr, session):
    if len(parts) < 2:
        print("用法: /vocab add|list|remove [词]")
        return
    sub = parts[1].lower()
    if sub == "add":
        if len(parts) < 3:
            print("用法: /vocab add <词>")
            return
        word = parts[2]
        vocab_mgr.add(session["id"], word, "", level=session["level"])
        ctx.add_vocab(word, "")
        print(f"✅ 已记录: {word}")
    elif sub == "list":
        words = vocab_mgr.list_by_session(session["id"])
        if not words:
            print("（暂无标记生词）")
        else:
            for w in words:
                print(f"  • {w['word']}")
    elif sub == "remove":
        if len(parts) < 3:
            print("用法: /vocab remove <词>")
            return
        word = parts[2]
        vocab_mgr.remove(session["id"], word)
        ctx.remove_vocab(word)
        print(f"✅ 已移除: {word}")
    else:
        print(f"未知子命令: {sub}")


def _do_done(archiver, session, ctx):
    print("\n📦 归档中...")
    archiver.archive_session(session["id"])
    path = archiver.export_markdown(session["id"])
    word_count = len(ctx.vocabulary)
    print(f"✅ 已归档: {session['title']}")
    print(f"📁 生词: {word_count} 个 | 文件: {path}")
    print(f"\n👋 À bientôt !\n")


def _save_dialogue_log(conn, session_id: str, role: str, content: str):
    now = datetime.datetime.now().isoformat()
    conn.execute(
        "INSERT INTO dialogue_log (session_id, role, content, created_at) VALUES (?,?,?,?)",
        (session_id, role, content, now),
    )
    conn.commit()


def run_interactive():
    cfg = get_config()

    api_key = cfg.api["api_key"]
    base_url = cfg.api["base_url"]
    model = cfg.api["model"]

    db_path = cfg.storage["db_path"]
    session_dir = cfg.storage["session_dir"]

    init_db(db_path)
    conn = get_connection(db_path)

    generator = TextGenerator(api_key, base_url, model)
    handler = DialogueHandler(api_key, base_url, model)
    vocab_mgr = VocabManager(db_path)
    archiver = Archiver(db_path, session_dir)

    completer = FrenchCompleter()

    try:
        session = _init_session(cfg, generator, conn)
        ctx = ConversationContext(
            text=session["text"],
            title=session["title"],
            level=session["level"],
            max_history=cfg.limits["max_history_turns"],
        )
        completer.set_text_words(_extract_words(session["text"]))

        hist_dir = os.path.dirname(db_path)
        os.makedirs(hist_dir, exist_ok=True)
        session_obj = PromptSession(
            history=FileHistory(os.path.join(hist_dir, ".french_history")),
            style=STYLE,
            completer=completer,
        )

        while True:
            try:
                user_input = session_obj.prompt([("class:prompt", "> ")]).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                _do_done(archiver, session, ctx)
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                _save_dialogue_log(conn, session["id"], "user", user_input)
                should_continue = _handle_command(
                    user_input, ctx, handler, generator,
                    vocab_mgr, archiver, session, cfg
                )
                if not should_continue:
                    break
            else:
                _save_dialogue_log(conn, session["id"], "user", user_input)
                print()
                try:
                    reply = handler.ask(ctx, user_input)
                    _save_dialogue_log(conn, session["id"], "assistant", reply)
                    print(f"🤖 {reply}\n")
                except Exception as e:
                    print(f"❌ AI 请求失败: {e}\n请检查网络连接或 API 配置。\n")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="FrenchLearner - AI 法语学习工具")
    sub = parser.add_subparsers(dest="command")

    vocab_parser = sub.add_parser("vocab", help="生词管理")
    vocab_parser.add_argument("action", choices=["list", "export", "stats"], default="list", nargs="?")
    vocab_parser.add_argument("--json", action="store_true", help="JSON 格式输出")

    sub.add_parser("sessions", help="列出历史会话")
    session_parser = sub.add_parser("session", help="查看会话")
    session_parser.add_argument("action", choices=["show"])
    session_parser.add_argument("id", help="会话 ID")

    args = parser.parse_args()
    cfg = get_config()
    init_db(cfg.storage["db_path"])

    if args.command == "vocab":
        vm = VocabManager(cfg.storage["db_path"])
        if args.action == "list":
            words = vm.list_all()
            if args.json:
                print(json.dumps(words, ensure_ascii=False, indent=2))
            else:
                for w in words:
                    print(f"{w['word']:20s} → {w['translation']}")
        elif args.action == "export":
            data = vm.export_json()
            print(json.dumps(data, ensure_ascii=False, indent=2))
        elif args.action == "stats":
            stats = vm.stats()
            print(f"总生词数: {stats['total']}")
            for lvl, cnt in stats.get("by_level", {}).items():
                print(f"  {lvl}: {cnt}")
    elif args.command == "sessions":
        conn = get_connection(cfg.storage["db_path"])
        try:
            rows = conn.execute(
                "SELECT id, level, title, status, created_at FROM sessions ORDER BY created_at DESC LIMIT 20"
            ).fetchall()
            for r in rows:
                status_icon = "📦" if r["status"] == "archived" else "🟢"
                print(f"{status_icon} {r['id'][:8]} {r['level']:3s} {r['created_at'][:10]} {r['title']}")
        finally:
            conn.close()
    elif args.command == "session" and args.action == "show":
        conn = get_connection(cfg.storage["db_path"])
        try:
            s = conn.execute("SELECT * FROM sessions WHERE id LIKE ?", (f"{args.id}%",)).fetchone()
            if not s:
                print(f"会话不存在: {args.id}")
                return
            print(f"📖 {s['title']}  [{s['level']}]")
            print(f"📅 {s['created_at']}")
            print(f"\n{s['text']}\n")
            dialogue = conn.execute(
                "SELECT role, content FROM dialogue_log WHERE session_id = ? ORDER BY created_at",
                (s["id"],),
            ).fetchall()
            for d in dialogue:
                role_icon = "🧑" if d["role"] == "user" else "🤖"
                print(f"{role_icon} {d['content']}")
        finally:
            conn.close()
    else:
        run_interactive()


if __name__ == "__main__":
    main()
