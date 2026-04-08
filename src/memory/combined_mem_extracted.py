from src.memory.combined_mem import CombinedMem
from src.memory.short_mem_extracted import ShortMemExtracted


class CombinedMemExtracted(CombinedMem):
    """带摘要的短期 + 长期记忆组合策略"""

    def __init__(self):
        super().__init__()
        self.short_mem = ShortMemExtracted()
