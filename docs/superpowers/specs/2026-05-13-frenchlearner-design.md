# FrenchLearner — AI 法语学习 CLI 工具 · 设计文档

## 概述

FrenchLearner 是一个基于 DeepSeek API 的交互式法语学习 CLI 工具。用户启动后获得一篇随机生成的法语段落，可通过自然语言 + 斜杠命令自由提问、标记生词、请求语法讲解，学习结束后自动归档。

**三阶段使用逻辑**：开始学习（推送文本）→ AI 对话（提问/标注/语法）→ 结束归档。

---

## 技术栈

| 组件 | 选择 |
|------|------|
| 语言 | Python 3.11+ |
| CLI 交互 | `prompt_toolkit`（REPL + tab 补全 + 历史） |
| AI 客户端 | `openai` SDK（DeepSeek 兼容接口） |
| 数据库 | SQLite（`sqlite3` stdlib） |
| 配置 | YAML（`pyyaml`） |
| 包管理 | `uv` / `pyproject.toml` |

---

## 项目结构

```
frenchlearner/
├── frenchlearner/
│   ├── __init__.py
│   ├── cli.py              # 入口 + 斜杠命令分发
│   ├── config.py           # 配置加载（YAML + 环境变量替换）
│   ├── generator.py        # 内容生成器 — 调用 DeepSeek 生成法语段落
│   ├── dialogue.py         # 对话处理器 — 上下文管理 + DeepSeek 对话
│   ├── vocab.py            # 生词管理器 — SQLite CRUD
│   ├── archive.py          # 归档模块 — 会话存储 + Markdown 导出
│   ├── db.py               # 数据库初始化 / 迁移
│   └── prompts/
│       ├── generate.txt    # 文本生成的 system prompt
│       └── dialogue.txt    # 对话模式的 system prompt
├── data/                   # 运行时数据（.gitignored）
│   ├── frenchlearner.db    # SQLite
│   └── sessions/           # Markdown 归档
├── config.example.yaml
├── pyproject.toml
└── README.md
```

---

## 交互设计

启动命令：`french`（直接进入交互模式）。

```
🎓 FrenchLearner | Niveau: A2
─────────────────────────────────

📖 [生成的法语段落]

>  自然语言输入            ← 结合当前文本向 AI 提问
```

### 斜杠命令

| 命令 | 效果 |
|------|------|
| `/vocab add <词>` | 标记生词（tab 自动补全文本中出现的词） |
| `/vocab list` | 显示当前会话已标记生词 |
| `/vocab remove <词>` | 取消标记 |
| `/grammar <主题>` | 请 AI 针对某语法点展开讲解 |
| `/next` | 换一篇新文本（同一会话继续） |
| `/level <A1/A2/B1/B2/C1>` | 调整难度 |
| `/done` 或 Ctrl+D | 结束会话并归档 |

### Tab 补全

- 斜杠命令名补全（`/v<TAB>` → `/vocab`）
- 子命令补全（`/vocab <TAB>` → `add` / `list` / `remove`）
- `/vocab add` 后补全当前文本中出现的单词

### 子命令（管理操作，非交互）

```bash
french vocab list              # 所有生词列表
french vocab export --json     # 导出词汇表
french vocab stats             # 词汇统计
french sessions                # 历史会话列表
french session show <id>       # 查看某次会话
```

---

## 数据模型

### SQLite 表结构

**sessions** — 学习会话

| 列 | 类型 | 说明 |
|----|------|------|
| id | TEXT PK | UUID |
| level | TEXT | CEFR 级别（A1/B1/C2...） |
| text | TEXT | 原始法语段落 |
| title | TEXT | 段落标题/摘要 |
| status | TEXT | active / archived |
| word_count | INTEGER | |
| created_at | TEXT | ISO 8601 |
| closed_at | TEXT | ISO 8601 |

**vocabulary** — 生词本

| 列 | 类型 | 说明 |
|----|------|------|
| id | INTEGER PK | |
| word | TEXT | 原文形式（如 "se promène"） |
| lemma | TEXT | 词元（如 "se promener"，用于去重） |
| translation | TEXT | 中文释义 |
| note | TEXT | 用户备注 |
| session_id | TEXT FK → sessions.id | |
| level | TEXT | |
| review_count | INTEGER DEFAULT 0 | |
| created_at | TEXT | |

UNIQUE(lemma, translation) — 同一词元 + 释义不重复。

**dialogue_log** — 对话记录

| 列 | 类型 | 说明 |
|----|------|------|
| id | INTEGER PK | |
| session_id | TEXT FK → sessions.id | |
| role | TEXT | user / assistant |
| content | TEXT | |
| created_at | TEXT | |

### Markdown 归档格式

每会话一个文件，保存到 `data/sessions/YYYY-MM-DD-HHMM.md`：

```markdown
# Session 2026-05-13 A2 — Marie au parc

## Texte
> [原始法语段落]

## Vocabulaire
| Mot | Traduction | Note |
|-----|-----------|------|
| se promener | 散步 | |
| le banc | 长椅 | 公园里的那种 |

## Dialogue (résumé)
- [对话摘要：关键问答]

---
Généré le 2026-05-13 14:30
```

---

## Prompt 工程

### 文本生成器（`prompts/generate.txt`）

- 根据 CEFR 级别控制词汇量、句长、语法复杂度
- A1-A2：附中文摘要；B1+：逐渐减少辅助
- 输出结构化标签 `<text>`, `<title>`, `<summary>` 便于解析
- 要求生成自然法语，避免教科书式例句

### 对话处理器（`prompts/dialogue.txt`）

- system prompt 注入：当前文本全文 + 用户已标记生词列表
- 角色：法语老师，用中文回答
- 策略：不翻译全文，用户问什么解释什么
- 语法讲解：简洁 + 1-2 个例句 + 对比中文差异
- 生词说明：给出原形 / 词性 / 释义 / 例句

### 上下文管理

```
[system prompt] + [当前文本] + [已标记生词] + [最近 N 轮对话]
```

N 默认 20，超限时压缩早期历史为摘要。每次 API 请求前拼接完整上下文。

---

## 配置（`config.example.yaml`）

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

- `api_key` 支持 `${ENV_VAR}` 替换
- 无硬编码密钥

---

## 模块职责

### `cli.py`
- 入口点，解析 `french [subcommand]`
- 无子命令时进入交互 REPL
- 分发斜杠命令到对应模块
- 管理 session 生命周期（创建 → active → 归档）

### `config.py`
- 加载 YAML 配置，替换环境变量
- 提供 `get_config()` 单一入口

### `generator.py`
- 调用 DeepSeek API，发送 `generate.txt` prompt
- 解析结构化响应（`<text>`, `<title>`, `<summary>`）
- 返回 `GeneratedText` dataclass

### `dialogue.py`
- 维护 `ConversationContext`（system prompt + 文本 + 生词 + 历史）
- `ask()` — 发送用户消息，返回 AI 回复
- `set_level()`, `new_text()`, `add_vocab()` — 更新上下文
- Token 预算管理（超限时摘要压缩）

### `vocab.py`
- `add()`, `remove()`, `list_by_session()` — CRUD
- `list_all()`, `export_json()`, `stats()` — 管理查询
- 接收 session_id，所有操作绑定会话

### `archive.py`
- `archive_session()` — 标记会话为 archived，写入 closed_at
- `export_markdown()` — 生成 Markdown 文件
- `generate_summary()` — 通过 AI 生成对话摘要（用于 Markdown）

### `db.py`
- `init_db()` — 建表（首次运行自动调用）
- 使用 `sqlite3.Row` 以字典形式返回结果

---

## 错误处理

- API 调用失败：重试 1 次，仍失败则提示用户 + 不中断会话
- 网络断开：捕获异常，提示检查网络或 API key
- 数据库错误：捕获并提示，保证 CLI 不崩溃
- 空响应：DeepSeek 返回空内容时重新请求

---

## 未来扩展（非 MVP）

- 间隔重复复习系统（SRS）
- Anki / CSV 导出
- 学习进度统计
- 语音朗读（TTS）
- 学习计划建议
