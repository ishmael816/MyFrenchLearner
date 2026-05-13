# frenchlearner/generator.py
import re
import time
import sys
from dataclasses import dataclass
from openai import OpenAI, APIError, APIConnectionError
from frenchlearner.prompts import load_prompt

LEVEL_DESCRIPTIONS = {
    "A1": "初级。使用最基础的词汇（约 100-200 词），句子简短（3-5 个单词），时态仅用现在时。",
    "A2": "初上级。词汇量约 300-500 词，可使用简单复合句，加入最近将来时 (futur proche)。",
    "B1": "中级。词汇量约 500-800 词，可使用复合过去时 (passé composé) 和未完成过去时 (imparfait)。",
    "B2": "中上级。词汇量约 800-1200 词，可加入条件式 (conditionnel)、虚拟式 (subjonctif) 的简单用法。",
    "C1": "高级。词汇量 1500+ 词，可使用所有时态和语式，文本长度增加至 300-400 词。",
}


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
