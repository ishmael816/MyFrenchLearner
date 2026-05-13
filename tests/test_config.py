import os
import tempfile
import pytest
from frenchlearner.config import Config, get_config
import frenchlearner.config as config_module


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the global config singleton before each test"""
    config_module._config = None
    yield
    config_module._config = None


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

    def test_missing_env_var_returns_empty(self):
        """未设置的环境变量返回空字符串"""
        yaml_content = """
api:
  api_key: "${NONEXISTENT_VAR_XYZ}"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            path = f.name
        try:
            cfg = Config.from_yaml(path)
            assert cfg.api["api_key"] == ""  # 未设置时返回空字符串
        finally:
            os.unlink(path)

    def test_default_values(self):
        """空配置使用默认值"""
        cfg = Config({})
        assert cfg.default_level == "A2"
        assert cfg.api["model"] == "deepseek-chat"
        assert cfg.limits["max_history_turns"] == 20

    def test_get_config_singleton(self, tmp_path):
        """get_config 返回单例"""
        # Create a temporary config file without env vars
        yaml_content = """
default_level: A2
api:
  model: "deepseek-chat"
limits:
  max_history_turns: 20
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)

        # Temporarily change to the tmp_path directory
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            config_module._config = None  # Reset singleton
            cfg1 = get_config()
            cfg2 = get_config()
            assert cfg1 is cfg2
        finally:
            os.chdir(old_cwd)
