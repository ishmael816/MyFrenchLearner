import os
import re
from pathlib import Path
import yaml


class Config:
    def __init__(self, data: dict):
        self._data = data

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
                    return ""  # 未设置环境变量时返回空字符串，由调用方处理
                return val
            return obj
        elif isinstance(obj, dict):
            return {k: Config._resolve_env(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [Config._resolve_env(v) for v in obj]
        return obj

    # -- 属性访问 --
    def __getattr__(self, name: str):
        if name.startswith("_"):
            return object.__getattribute__(self, name)
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
        pkg_dir = Path(__file__).parent
        project_root = pkg_dir.parent

        # 搜索顺序：CWD → 项目根目录（开发模式）→ 包内置
        search_paths = [
            Path("config.yaml"),
            project_root / "config.yaml",
            Path("config.example.yaml"),
            project_root / "config.example.yaml",
            pkg_dir / "config.example.yaml",
        ]
        config_path = None
        for p in search_paths:
            if p.exists():
                config_path = p
                break

        if config_path is None:
            raise FileNotFoundError("未找到 config.yaml 或 config.example.yaml")

        _config = Config.from_yaml(str(config_path))
    return _config
