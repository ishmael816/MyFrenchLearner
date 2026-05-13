# tests/test_generator.py
from unittest.mock import MagicMock
from frenchlearner.generator import GeneratedText, TextGenerator


class TestTextGenerator:
    def test_generated_text_dataclass(self):
        gt = GeneratedText(text="Bonjour.", title="问候", summary="一个简单的问候")
        assert gt.text == "Bonjour."
        assert gt.title == "问候"

    def test_parse_response_valid(self):
        response = """<title>在公园</title>
<text>Marie se promène dans le parc.</text>
<summary>玛丽在公园散步，描述了一个晴朗的下午。</summary>"""
        gen = TextGenerator("sk-test", "http://fake", "model")
        result = gen._parse_response(response)
        assert result.title == "在公园"
        assert result.text == "Marie se promène dans le parc."
        assert "玛丽" in result.summary

    def test_generate_returns_text(self):
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
