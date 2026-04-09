import os

from dotenv import load_dotenv
from openai import OpenAI

from src.agents.message_dto import MessageDTO
from src.agents.message_enum import Message
from src.memory.base_mem import BaseMem

load_dotenv()


class Agent:
    def __init__(self, mem_module: BaseMem):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.mem = mem_module

    def chat(self, q: str) -> str:
        messages = self._build_messages(q, self.mem.get_mem(q))
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
        )
        ans = response.choices[0].message.content or ""
        self.mem.update_mem(q, ans)
        return ans

    def _build_messages(self, q: str, mem: list[MessageDTO]) -> list[dict]:
        messages: list[dict] = [
            {"role": "system", "content": Message.SYSTEM_PROMPT.value}
        ]
        for item in mem:
            messages.append({"role": item.role.value, "content": item.content})
        messages.append({"role": "user", "content": q})
        return messages
