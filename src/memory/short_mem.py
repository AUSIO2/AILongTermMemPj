from src.memory.base_mem import BaseMem
from src.agents.message_dto import MessageDTO,Role
import tiktoken

from src.memory.constant import MAX_CONTEXT_WINDOW,SECOND_WATER_LEVEL,MODEL



class ShortMem(BaseMem):
    """短期记忆策略。"""
    def __init__(self):
        self.mem :list[MessageDTO] = []
        self.enc = tiktoken.encoding_for_model(MODEL)

    def get_mem(self, q: str) -> list[MessageDTO]:
        return self.mem

    def update_mem(self, q: str, ans: str) -> None:
        self.mem.append(MessageDTO(role=Role.USER, content=q))
        self.mem.append(MessageDTO(role=Role.ASSISTANT, content=ans))

        total_tokens = self._count_tokens()
        if total_tokens > MAX_CONTEXT_WINDOW * SECOND_WATER_LEVEL:
            self._compress_mem()

    def _count_tokens(self) -> int:
        """计算当前 mem 中所有消息的总 token 数。"""
        return sum(len(self.enc.encode(m.content)) for m in self.mem)

    def _compress_mem(self) -> None:
        """当总 token 超过第二水位线时，删除最早的记忆直到回到第二水位之下"""
        threshold_2 = MAX_CONTEXT_WINDOW * SECOND_WATER_LEVEL
        while self.mem and self._count_tokens() > threshold_2:
            self.mem.pop(0)
