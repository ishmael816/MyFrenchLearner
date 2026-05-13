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
