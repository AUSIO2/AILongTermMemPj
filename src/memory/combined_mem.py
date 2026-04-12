from src.agents.message_dto import MessageDTO, Role
from src.memory.base_mem import BaseMem
from src.memory.short_mem import ShortMem
from src.memory.long_mem import LongMem
from src.agents.message_enum import Message

class CombinedMem(BaseMem):
    """短期 + 长期记忆组合策略"""
    def __init__(self, session_id: str | None = None):
        self.short_mem = ShortMem()
        self.long_mem = LongMem(session_id=session_id)

    def get_mem(self, q: str) -> list[MessageDTO]:
        long_memessages = self.long_mem.get_mem(q)
        short_memessages = self.short_mem.get_mem(q)
        
        combined = []
        # 将长期记忆组装成带有系统提示的记忆上下文
        if long_memessages:
            context_str = "\n".join([f"{m.role.value}: {m.content}" for m in long_memessages])
            combined.append(MessageDTO(
                role=Role.SYSTEM,
                content=f"{Message.LONG_MEM_CONTEXT.value}\n{context_str}"
            ))
            
        combined.extend(short_memessages)
        return combined

    def update_mem(self, q: str, ans: str) -> None:
        self.short_mem.update_mem(q, ans)
        self.long_mem.update_mem(q, ans)
