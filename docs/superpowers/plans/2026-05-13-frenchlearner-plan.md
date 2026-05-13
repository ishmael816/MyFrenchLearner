# FrenchLearner 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建基于 DeepSeek API 的交互式法语学习 CLI 工具，三阶段流程：推送阅读文本 → AI 对话交互 → 结束归档。

**Architecture:** 模块化 Python CLI，prompt_toolkit 驱动交互式 REPL，openai SDK 对接 DeepSeek，SQLite 持久化，Markdown 导出归档。

**Tech Stack:** Python 3.11+, prompt_toolkit, openai SDK (DeepSeek 兼容), SQLite(stdlib), pyyaml, uv

---

### Task 1: 项目脚手架

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `config.example.yaml`
- Create: `frenchlearner/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[project]
name = "frenchlearner"
version = "0.1.0"
description = "AI-powered French learning CLI tool"
requires-python = ">=3.11"
dependencies = [
    "openai>=1.0",
    "prompt-toolkit>=3.0",
    "pyyaml>=6.0",
]

[project.scripts]
french = "frenchlearner.cli:main"

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-mock>=3.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: 创建 .gitignore**

```
__pycache__/
*.pyc
data/
config.yaml
*.egg-info/
.pytest_cache/
```

- [ ] **Step 3: 创建 config.example.yaml**

```yaml
api:
  base_url: "https://api.deepseek.com/v1"
  api_key: "${DEEPSEEK_API_KEY}"
  model: "deepseek-chat"

default_level: A2

limits:
  max_history_turns: 20
  max_text_length: 1500

storage:
  db_path: "data/frenchlearner.db"
  session_dir: "data/sessions"

display:
  text_width: 80
  emphasize_new_words: true
```

- [ ] **Step 4: 创建 `__init__.py` 文件**

```python
# frenchlearner/__init__.py
"""FrenchLearner - AI-powered French learning CLI tool."""
__version__ = "0.1.0"
```

```python
# tests/__init__.py
```

- [ ] **Step 5: 安装依赖并验证**

Run: `uv sync`
Expected: 所有依赖安装成功，`uv run french` 报错 "module 'frenchlearner.cli' has no attribute 'main'"（cli.py 尚未创建）

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore config.example.yaml frenchlearner/__init__.py tests/__init__.py
git commit -m "feat: scaffold FrenchLearner project"
```

---

### Task 2: 配置模块（config.py）

**Files:**
- Create: `frenchlearner/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_config.py
import os
import tempfile
import pytest
from frenchlearner.config import Config, get_config


class TestConfig:
    def test_loads_yaml_config(self):
        """基本 YAML 加载"""
        yaml_content = """
default_level: B1
limits:
  max_history_turns: 10
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            path = f.name
        try:
            cfg = Config.from_yaml(path)
            assert cfg.default_level == "B1"
            assert cfg.limits["max_history_turns"] == 10
        finally:
            os.unlink(path)

    def test_resolves_env_var_in_config(self):
        """${ENV_VAR} 环境变量替换"""
        os.environ["TEST_KEY"] = "sk-test-123"
        yaml_content = """
api:
  api_key: "${TEST_KEY}"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            path = f.name
        try:
            cfg = Config.from_yaml(path)
            assert cfg.api["api_key"] == "sk-test-123"
        finally:
            os.unlink(path)

    def test_missing_env_var_raises(self):
        """未设置的环境变量抛异常"""
        yaml_content = """
api:
  api_key: "${NONEXISTENT_VAR_XYZ}"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            path = f.name
        try:
            with pytest.raises(ValueError, match="NONEXISTENT_VAR_XYZ"):
                Config.from_yaml(path)
        finally:
            os.unlink(path)

    def test_default_values(self):
        """空配置使用默认值"""
        cfg = Config({})
        assert cfg.default_level == "A2"
        assert cfg.api["model"] == "deepseek-chat"
        assert cfg.limits["max_history_turns"] == 20

    def test_get_config_singleton(self):
        """get_config 返回单例"""
        cfg1 = get_config()
        cfg2 = get_config()
        assert cfg1 is cfg2
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/test_config.py -v`
Expected: 所有测试 FAIL（模块不存在）

- [ ] **Step 3: 实现 Config 类**

```python
# frenchlearner/config.py
import os
import re
from pathlib import Path
from dataclasses import dataclass, field
import yaml


@dataclass
class Config:
    _data: dict

    # -- 加载入口 --
    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        resolved = cls._resolve_env(raw)
        return cls(resolved)

    # -- 环境变量替换 --
    @staticmethod
    def _resolve_env(obj):
        if isinstance(obj, str):
            m = re.fullmatch(r"\$\{(\w+)\}", obj)
            if m:
                var = m.group(1)
                val = os.environ.get(var)
                if val is None:
                    raise ValueError(f"环境变量 ${var} 未设置")
                return val
            return obj
        elif isinstance(obj, dict):
            return {k: Config._resolve_env(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [Config._resolve_env(v) for v in obj]
        return obj

    # -- 属性访问 --
    def __getattr__(self, name: str):
        if name in self._data:
            val = self._data[name]
            if isinstance(val, dict):
                return Config(val)
            return val
        raise AttributeError(f"未知配置项: {name}")

    def __getitem__(self, key: str):
        val = self._data.get(key)
        if isinstance(val, dict):
            return Config(val)
        return val

    # -- 默认值链 --
    @property
    def default_level(self) -> str:
        return self._data.get("default_level", "A2")

    @property
    def api(self):
        val = self._data.get("api", {})
        defaults = {"model": "deepseek-chat", "base_url": "https://api.deepseek.com/v1"}
        return Config({**defaults, **val})

    @property
    def limits(self):
        val = self._data.get("limits", {})
        defaults = {"max_history_turns": 20, "max_text_length": 1500}
        return Config({**defaults, **val})

    @property
    def storage(self):
        val = self._data.get("storage", {})
        defaults = {"db_path": "data/frenchlearner.db", "session_dir": "data/sessions"}
        return Config({**defaults, **val})

    @property
    def display(self):
        val = self._data.get("display", {})
        defaults = {"text_width": 80, "emphasize_new_words": True}
        return Config({**defaults, **val})


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        config_path = Path("config.yaml")
        if not config_path.exists():
            config_path = Path("config.example.yaml")
        _config = Config.from_yaml(str(config_path))
    return _config
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/test_config.py -v`
Expected: 所有测试 PASS

- [ ] **Step 5: Commit**

```bash
git add frenchlearner/config.py tests/test_config.py
git commit -m "feat: add config module with YAML + env var resolution"
```

---

### Task 3: 数据库模块（db.py）

**Files:**
- Create: `frenchlearner/db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: 编写失败测试**

```python
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
            conn.execute(
                "INSERT INTO vocabulary (word, lemma, translation, session_id) VALUES (?,?,?,?)",
                ("se promène", "se promener", "散步", "s1"),
            )
            conn.commit()
            with conn:
                pass
            conn.execute(
                "INSERT INTO vocabulary (word, lemma, translation, session_id) VALUES (?,?,?,?)",
                ("se promener", "se promener", "散步", "s2"),
            )
            conn.commit()  # 应抛出 IntegrityError
            assert False, "应抛出 IntegrityError"
        except sqlite3.IntegrityError:
            pass  # 预期
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_idempotent_init(self):
        """多次 init_db 不报错"""
        db_path = os.path.join(tempfile.mkdtemp(), "test.db")
        try:
            init_db(db_path)
            init_db(db_path)  # 第二次调用不抛异常
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/test_db.py -v`
Expected: 所有测试 FAIL

- [ ] **Step 3: 实现数据库模块**

```python
# frenchlearner/db.py
import sqlite3
import os
from pathlib import Path

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
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/test_db.py -v`
Expected: 所有测试 PASS

- [ ] **Step 5: Commit**

```bash
git add frenchlearner/db.py tests/test_db.py
git commit -m "feat: add database module with schema and init"
```

---

### Task 4: 生词模块（vocab.py）

**Files:**
- Create: `frenchlearner/vocab.py`
- Create: `tests/test_vocab.py`

- [ ] **Step 1: 编写测试**

```python
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
        # 创建测试 session
        conn = get_connection(self.db_path)
        conn.execute(
            "INSERT INTO sessions (id, level, text, title, created_at) VALUES (?,?,?,?,?)",
            ("s1", "A2", "Bonjour le monde.", "Test", self.now),
        )
        conn.commit()
        conn.close()

    def test_add_vocab(self):
        """添加生词"""
        self.vm.add("s1", "se promène", "散步")
        words = self.vm.list_by_session("s1")
        assert len(words) == 1
        assert words[0]["word"] == "se promène"
        assert words[0]["lemma"] == "se promener"
        assert words[0]["translation"] == "散步"

    def test_add_duplicate_ignored(self):
        """重复添加不报错"""
        self.vm.add("s1", "manger", "吃")
        self.vm.add("s1", "manger", "吃")  # 不应抛异常
        words = self.vm.list_by_session("s1")
        assert len(words) == 1

    def test_remove_vocab(self):
        """删除生词"""
        self.vm.add("s1", "parler", "说话")
        self.vm.add("s1", "manger", "吃")
        self.vm.remove("s1", "parler")
        words = self.vm.list_by_session("s1")
        assert len(words) == 1
        assert words[0]["word"] == "manger"

    def test_list_all(self):
        """列出所有生词"""
        self.vm.add("s1", "parler", "说话")
        self.vm.add("s1", "manger", "吃")
        all_words = self.vm.list_all()
        assert len(all_words) == 2

    def test_export_json(self):
        """导出 JSON"""
        self.vm.add("s1", "parler", "说话", note="动词")
        data = self.vm.export_json()
        assert len(data) == 1
        assert data[0]["word"] == "parler"
        assert data[0]["note"] == "动词"

    def test_stats(self):
        """统计信息"""
        self.vm.add("s1", "parler", "说话")
        self.vm.add("s1", "manger", "吃")
        self.vm.add("s1", "dormir", "睡觉")
        stats = self.vm.stats()
        assert stats["total"] == 3
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/test_vocab.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 VocabManager**

```python
# frenchlearner/vocab.py
import datetime
import json
from frenchlearner.db import get_connection


def _to_lemma(word: str) -> str:
    """简单词元化：去重音、转小写、去 se/s'/me/te 等自反代词前缀"""
    w = word.strip().lower()
    # 去掉前置自反代词
    for prefix in ("se ", "s'", "me ", "m'", "te ", "t'"):
        if w.startswith(prefix):
            w = w[len(prefix):]
            break
    # 还原基本拼写（简化版，不引入完整形态分析）
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
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/test_vocab.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frenchlearner/vocab.py tests/test_vocab.py
git commit -m "feat: add vocabulary manager with CRUD and stats"
```

---

### Task 5: Prompt 模板

**Files:**
- Create: `frenchlearner/prompts/generate.txt`
- Create: `frenchlearner/prompts/__init__.py`

- [ ] **Step 1: 创建 generate.txt prompt 模板**

```python
# frenchlearner/prompts/__init__.py
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent

def load_prompt(name: str) -> str:
    """加载 prompt 模板文件"""
    path = _PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt 模板不存在: {name}")
    return path.read_text(encoding="utf-8")
```

内容（`frenchlearner/prompts/generate.txt`）：

```
你是一位资深的法语教材编写者。请根据以下要求生成一段法语阅读文本。

## 难度级别
{level}

## 要求
- 生成一段自然、地道的法语段落，语体日常化，避免教科书式例句
- {level_specific}
- 只输出**纯法语段落**，不要包含翻译、解析或任何中文内容

## 输出格式
请严格按照以下标签格式输出：

<title>简要中文标题</title>
<text>法语段落全文</text>
<summary>中文内容摘要（2-3句话，帮助理解文本大意）</summary>
```

- [ ] **Step 2: 创建 dialogue.txt prompt 模板**

内容（`frenchlearner/prompts/dialogue.txt`）：

```
你是一位耐心且专业的法语教师。你的学生母语是中文，正在学习法语。

## 当前阅读文本
<text>
{text}
</text>

## 学生已标记的生词
{vocab_list}

## 教学规则
1. 用中文回答学生的问题，不要在回答中翻译整段文本。
2. 学生问某个词的意思时，解释格式：**[原形] [词性]** — 中文释义，并给出 1 个例句。
3. 学生问语法时，简洁解释规则 + 1-2 个例句 + 对比中文差异。
4. 回答控制在 200 字以内（除非学生明确要求详细讲解）。
5. 自然地鼓励学生，但不要过度恭维。

## 学生问题
{question}
```

- [ ] **Step 3: 验证模板可加载**

Run: `uv run python -c "from frenchlearner.prompts import load_prompt; print(load_prompt('generate.txt')[:50])"`
Expected: 打印模板前 50 个字符

- [ ] **Step 4: Commit**

```bash
git add frenchlearner/prompts/
git commit -m "feat: add prompt templates for generation and dialogue"
```

---

### Task 6: 文本生成器（generator.py）

**Files:**
- Create: `frenchlearner/generator.py`
- Create: `tests/test_generator.py`

- [ ] **Step 1: 编写测试**

```python
# tests/test_generator.py
from unittest.mock import MagicMock, patch
from frenchlearner.generator import GeneratedText, TextGenerator


class TestTextGenerator:
    def test_generated_text_dataclass(self):
        """GeneratedText 数据类基本功能"""
        gt = GeneratedText(text="Bonjour.", title="问候", summary="一个简单的问候")
        assert gt.text == "Bonjour."
        assert gt.title == "问候"

    def test_parse_response_valid(self):
        """解析有效的结构化响应"""
        response = """<title>在公园</title>
<text>Marie se promène dans le parc.</text>
<summary>玛丽在公园散步，描述了一个晴朗的下午。</summary>"""
        gen = TextGenerator("sk-test", "http://fake", "model")
        result = gen._parse_response(response)
        assert result.title == "在公园"
        assert result.text == "Marie se promène dans le parc."
        assert "玛丽" in result.summary

    def test_generate_returns_text(self):
        """generate 返回 GeneratedText"""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content="<title>测试</title>\n<text>Bonjour le monde.</text>\n<summary>你好世界。</summary>"
                    )
                )
            ]
        )
        gen = TextGenerator("sk-test", "http://fake", "deepseek-chat")
        gen._client = mock_client
        result = gen.generate("A2")
        assert isinstance(result, GeneratedText)
        assert result.title == "测试"
        assert result.text == "Bonjour le monde."
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/test_generator.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 TextGenerator**

```python
# frenchlearner/generator.py
import re
import time
import sys
from dataclasses import dataclass
from openai import OpenAI, APIError, APIConnectionError
from frenchlearner.prompts import load_prompt


def _retry_api_call(fn, max_retries=1):
    """API 调用重试包装器。失败后重试 1 次，仍失败则抛出。"""
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except (APIError, APIConnectionError) as e:
            last_err = e
            if attempt < max_retries:
                print(f"⚠️ API 调用失败，正在重试... ({e})", file=sys.stderr)
                time.sleep(1)
    raise last_err

LEVEL_DESCRIPTIONS = {
    "A1": "初级。使用最基础的词汇（约 100-200 词），句子简短（3-5 个单词），时态仅用现在时。",
    "A2": "初上级。词汇量约 300-500 词，可使用简单复合句，加入最近将来时 (futur proche)。",
    "B1": "中级。词汇量约 500-800 词，可使用复合过去时 (passé composé) 和未完成过去时 (imparfait)。",
    "B2": "中上级。词汇量约 800-1200 词，可加入条件式 (conditionnel)、虚拟式 (subjonctif) 的简单用法。",
    "C1": "高级。词汇量 1500+ 词，可使用所有时态和语式，文本长度增加至 300-400 词。",
}


@dataclass
class GeneratedText:
    text: str
    title: str
    summary: str


class TextGenerator:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def generate(self, level: str = "A2") -> GeneratedText:
        level_desc = LEVEL_DESCRIPTIONS.get(level, LEVEL_DESCRIPTIONS["A2"])
        prompt_template = load_prompt("generate.txt")
        system_prompt = prompt_template.format(level=level, level_specific=level_desc)

        def _call():
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "system", "content": system_prompt}],
                temperature=0.9,
                max_tokens=800,
            )
            return response

        response = _retry_api_call(_call)
        content = response.choices[0].message.content
        if not content:
            raise ValueError("DeepSeek 返回空响应")
        return self._parse_response(content)

    def _parse_response(self, content: str) -> GeneratedText:
        title = self._extract_tag(content, "title") or "Sans titre"
        text = self._extract_tag(content, "text") or content
        summary = self._extract_tag(content, "summary") or ""
        return GeneratedText(text=text.strip(), title=title.strip(), summary=summary.strip())

    @staticmethod
    def _extract_tag(content: str, tag: str) -> str | None:
        pattern = rf"<{tag}>(.*?)</{tag}>"
        m = re.search(pattern, content, re.DOTALL)
        return m.group(1).strip() if m else None
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/test_generator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frenchlearner/generator.py tests/test_generator.py
git commit -m "feat: add text generator with DeepSeek API integration"
```

---

### Task 7: 对话模块（dialogue.py）

**Files:**
- Create: `frenchlearner/dialogue.py`
- Create: `tests/test_dialogue.py`

- [ ] **Step 1: 编写测试**

```python
# tests/test_dialogue.py
from unittest.mock import MagicMock
from frenchlearner.dialogue import DialogueHandler, ConversationContext


class TestConversationContext:
    def test_new_context(self):
        ctx = ConversationContext(
            text="Bonjour le monde.",
            title="问候",
            level="A2",
        )
        assert ctx.text == "Bonjour le monde."
        assert ctx.level == "A2"
        assert ctx.history == []
        assert ctx.vocab_words == []

    def test_add_vocab(self):
        ctx = ConversationContext(text="Bonjour.", title="", level="A2")
        ctx.add_vocab("Bonjour", "你好")
        assert len(ctx.vocab_words) == 1
        assert ctx.vocab_words[0] == ("Bonjour", "你好")

    def test_remove_vocab(self):
        ctx = ConversationContext(text="Bonjour.", title="", level="A2")
        ctx.add_vocab("Bonjour", "你好")
        ctx.add_vocab("le", "定冠词")
        ctx.remove_vocab("Bonjour")
        assert len(ctx.vocab_words) == 1
        assert ctx.vocab_words[0] == ("le", "定冠词")

    def test_add_history_trims_oldest(self):
        ctx = ConversationContext(text=".", title="", level="A2", max_history=3)
        for i in range(5):
            ctx.add_history("user", f"msg{i}")
        assert len(ctx.history) == 3
        assert ctx.history[0]["content"] == "msg2"

    def test_format_vocab_list(self):
        ctx = ConversationContext(text=".", title="", level="A2")
        ctx.add_vocab("manger", "吃")
        ctx.add_vocab("dormir", "睡觉")
        result = ctx.format_vocab_list()
        assert "- manger → 吃" in result
        assert "- dormir → 睡觉" in result

    def test_empty_vocab_list(self):
        ctx = ConversationContext(text=".", title="", level="A2")
        assert "暂无标记生词" in ctx.format_vocab_list()


class TestDialogueHandler:
    def test_ask_returns_response(self):
        ctx = ConversationContext(text="Bonjour.", title="", level="A2")
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="你好，Bonjour 是法语问候语。"))]
        )
        handler = DialogueHandler("sk-test", "http://fake", "deepseek-chat")
        handler._client = mock_client
        reply = handler.ask(ctx, "Bonjour 是什么意思？")
        assert "Bonjour" in reply
        assert len(ctx.history) == 2  # user + assistant
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/test_dialogue.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 DialogueHandler**

```python
# frenchlearner/dialogue.py
from dataclasses import dataclass, field
from openai import OpenAI, APIError, APIConnectionError
from frenchlearner.prompts import load_prompt
from frenchlearner.generator import _retry_api_call


@dataclass
class ConversationContext:
    text: str
    title: str
    level: str
    max_history: int = 20
    vocabulary: dict[str, tuple[str, str]] = field(default_factory=dict)  # word -> (word, translation)
    history: list[dict] = field(default_factory=list)

    @property
    def vocab_words(self) -> list[tuple[str, str]]:
        return list(self.vocabulary.values())

    def add_vocab(self, word: str, translation: str) -> None:
        self.vocabulary[word] = (word, translation)

    def remove_vocab(self, word: str) -> None:
        self.vocabulary.pop(word, None)

    def add_history(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def format_vocab_list(self) -> str:
        if not self.vocabulary:
            return "（暂无标记生词）"
        lines = [f"- {w} → {t}" for w, t in self.vocabulary.values()]
        return "\n".join(lines)


class DialogueHandler:
    def __init__(self, api_key: str, base_url: str, model: str):
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def ask(self, ctx: ConversationContext, question: str) -> str:
        ctx.add_history("user", question)

        prompt_template = load_prompt("dialogue.txt")
        system_content = prompt_template.format(
            text=ctx.text,
            vocab_list=ctx.format_vocab_list(),
            question=question,
        )

        messages = [{"role": "system", "content": system_content}]
        messages.extend(ctx.history)

        def _call():
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.7,
                max_tokens=600,
            )
            return response

        response = _retry_api_call(_call)
        reply = response.choices[0].message.content or "（AI 未返回内容，请重试）"
        ctx.add_history("assistant", reply)
        return reply
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/test_dialogue.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frenchlearner/dialogue.py tests/test_dialogue.py
git commit -m "feat: add dialogue handler with conversation context"
```

---

### Task 8: 归档模块（archive.py）

**Files:**
- Create: `frenchlearner/archive.py`
- Create: `tests/test_archive.py`

- [ ] **Step 1: 编写测试**

```python
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
        """归档更新 session 状态"""
        self.archiver.archive_session("s1")
        conn = get_connection(self.db_path)
        row = conn.execute("SELECT status, closed_at FROM sessions WHERE id=?", ("s1",)).fetchone()
        assert row["status"] == "archived"
        assert row["closed_at"] is not None
        conn.close()

    def test_export_markdown_creates_file(self):
        """导出 Markdown 创建文件"""
        path = self.archiver.export_markdown("s1")
        assert os.path.exists(path)
        content = Path(path).read_text(encoding="utf-8")
        assert "问候" in content
        assert "Bonjour le monde" in content

    def test_export_markdown_contains_vocab(self):
        """Markdown 包含生词表"""
        path = self.archiver.export_markdown("s1")
        content = Path(path).read_text(encoding="utf-8")
        assert "Bonjour" in content
        assert "你好" in content

    def test_export_markdown_contains_dialogue(self):
        """Markdown 包含对话记录"""
        path = self.archiver.export_markdown("s1")
        content = Path(path).read_text(encoding="utf-8")
        assert "Bonjour 是什么意思？" in content
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/test_archive.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 Archiver**

```python
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
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/test_archive.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frenchlearner/archive.py tests/test_archive.py
git commit -m "feat: add archiver with markdown export"
```

---

### Task 9: CLI 入口（cli.py）

**Files:**
- Create: `frenchlearner/cli.py`

- [ ] **Step 1: 实现 CLI**

```python
# frenchlearner/cli.py
import argparse
import datetime
import json
import os
import sys
import uuid

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter, Completer, Completion
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
    "ai": "italic",
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

        # 去掉 / 前缀
        cmd_text = text[1:]
        parts = cmd_text.split()

        if len(parts) == 1:
            # 补全命令名
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
                # 补全文本中的词
                word_start = parts[2] if len(parts) > 2 else ""
                for w in self.text_words:
                    if w.lower().startswith(word_start.lower()):
                        yield Completion(w, start_position=-len(word_start))


def _extract_words(text: str) -> list[str]:
    """从文本中提取单词用于补全"""
    import re
    words = re.findall(r"[A-Za-zÀ-ÿ']{2,}", text)
    seen = set()
    unique = []
    for w in words:
        if w.lower() not in seen:
            seen.add(w.lower())
            unique.append(w)
    return unique


def _init_session(cfg, generator, conn) -> dict:
    """创建新 session，生成文本"""
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
    """处理斜杠命令。返回 True 表示继续，False 表示退出。"""
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
    vocab_parser.add_argument("action", choices=["list", "export", "stats"], default="list")
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
```

- [ ] **Step 2: 验证 CLI 启动**

Run: `uv run french --help`
Expected: 显示帮助信息（需要先 export DEEPSEEK_API_KEY）

- [ ] **Step 3: Commit**

```bash
git add frenchlearner/cli.py
git commit -m "feat: add CLI entry with interactive REPL and subcommands"
```

---

### Task 10: 集成测试与收尾

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: 编写集成测试**

```python
# tests/test_integration.py
import datetime
import os
import tempfile
from unittest.mock import MagicMock, patch
from frenchlearner.config import Config
from frenchlearner.db import init_db
from frenchlearner.generator import TextGenerator, GeneratedText
from frenchlearner.dialogue import DialogueHandler, ConversationContext
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
        import sqlite3
        conn = sqlite3.connect(db_path)
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

        # 归档
        archiver.archive_session(session_id)
        path = archiver.export_markdown(session_id)

        assert os.path.exists(path)
        content = open(path, encoding="utf-8").read()
        assert "Marie se promène" in content
        assert "散步" in content

    def test_vocab_deduplication(self):
        """同一词不同 session 的去重行为"""
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "test.db")
        init_db(db_path)
        vm = VocabManager(db_path)

        # 在两个 session 中添加同一个词
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO sessions (id, level, text, title, created_at) VALUES (?,?,?,?,?)",
            ("s1", "A2", ".", ".", datetime.datetime.now().isoformat()),
        )
        conn.execute(
            "INSERT INTO sessions (id, level, text, title, created_at) VALUES (?,?,?,?,?)",
            ("s2", "B1", ".", ".", datetime.datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

        vm.add("s1", "manger", "吃")
        vm.add("s2", "manger", "吃")  # 应被 IGNORE

        all_words = vm.list_all()
        assert len(all_words) == 1  # 去重
```

- [ ] **Step 2: 运行集成测试**

Run: `uv run pytest tests/test_integration.py -v`
Expected: PASS

- [ ] **Step 3: 运行全部测试**

Run: `uv run pytest tests/ -v`
Expected: 所有测试 PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration test for full session flow"
```

---

### Task 11: 最终验证

- [ ] **Step 1: 验证安装**

Run: `uv run pip install -e .`
Expected: 成功安装，`french` 命令可用

- [ ] **Step 2: 验证命令行子命令**

Run: `uv run french --help`
Expected: 显示帮助和子命令

Run: `uv run french vocab stats`
Expected: 显示统计（数据库自动初始化）

- [ ] **Step 3: 验证配置加载**

Run: `uv run python -c "from frenchlearner.config import get_config; c=get_config(); print(c.default_level)"`
Expected: 打印 "A2"

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "chore: final wiring and verification"
```
