from src.memory.base_mem import BaseMem
from src.agents.message_dto import MessageDTO,Role
from src.agents.message_enum import Message
import os
import tiktoken

from src.memory.constant import MAX_CONTEXT_WINDOW, FIRST_WATER_LEVEL, SECOND_WATER_LEVEL,MODEL
from src.agents.agent import Agent
from src.memory.no_mem import NoMem


class ShortMem(BaseMem):
    """短期记忆策略。"""
    def __init__(self):
        self.mem :list[MessageDTO] = []
        self.enc = tiktoken.encoding_for_model(MODEL)

    def get_mem(self, q: str) -> list:
        return self.mem

    def update_mem(self, q: str, ans: str) -> None:
        self.mem.append(MessageDTO(role=Role.USER, content=q))
        self.mem.append(MessageDTO(role=Role.ASSISTANT, content=ans))

        total_tokens = self._count_tokens()
        if total_tokens > MAX_CONTEXT_WINDOW * SECOND_WATER_LEVEL:
            self._extract_mem()

    def _count_tokens(self) -> int:
        """计算当前 mem 中所有消息的总 token 数。"""
        return sum(len(self.enc.encode(m.content)) for m in self.mem)

    def _extract_mem(self) -> None:
        """当总 token 超过第二水位线时，把一二水位线之间的消息发给ai做摘要"""
        threshold_1 = MAX_CONTEXT_WINDOW * FIRST_WATER_LEVEL
        threshold_2 = MAX_CONTEXT_WINDOW * SECOND_WATER_LEVEL

        # 从头累加 token，找到一二水位线的下标
        accumulated = 0
        first_idx = None
        second_idx = None
        for i, msg in enumerate(self.mem):
            accumulated += len(self.enc.encode(msg.content))
            if first_idx is None and accumulated > threshold_1:
                first_idx = i
            if accumulated > threshold_2:
                second_idx = i
                break

        if first_idx is None or second_idx is None:
            return

        # 切片
        segment = self.mem[first_idx: second_idx + 1]
        conversation_text = "\n".join(
            f"{m.role.value}: {m.content}" for m in segment
        )

        # 用无记忆的 Agent 做摘要
        agent = Agent(mem_module=NoMem())
        summary = agent.chat(f"{Message.MEMORY_EXTRACT_CONTEXT}\n{conversation_text}")

        # 摘要插到最新位置
        summary_msg = MessageDTO(
            role=Role.SYSTEM,
            content=f"{Message.RESULT_CONTEXT}\n{summary}",
        )
        self.mem.append(summary_msg)
