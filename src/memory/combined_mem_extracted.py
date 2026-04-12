from src.memory.combined_mem import CombinedMem
from src.memory.short_mem_extracted import ShortMemExtracted


class CombinedMemExtracted(CombinedMem):
    """带摘要的短期 + 长期记忆组合策略"""

    def __init__(self, session_id: str | None = None):
        super().__init__(session_id=session_id)
        self.short_mem = ShortMemExtracted()
