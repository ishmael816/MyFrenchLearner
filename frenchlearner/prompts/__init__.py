# frenchlearner/prompts/__init__.py
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent

def load_prompt(name: str) -> str:
    """加载 prompt 模板文件"""
    path = _PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt 模板不存在: {name}")
    return path.read_text(encoding="utf-8")
