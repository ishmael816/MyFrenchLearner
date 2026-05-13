# frenchlearner/dialogue.py
from dataclasses import dataclass, field
from openai import OpenAI
from frenchlearner.prompts import load_prompt
from frenchlearner.generator import _retry_api_call


@dataclass
class ConversationContext:
    text: str
    title: str
    level: str
    max_history: int = 20
    vocabulary: dict[str, tuple[str, str]] = field(default_factory=dict)
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
