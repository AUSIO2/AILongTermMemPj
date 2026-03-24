from src.memory.base_mem import BaseMem


class ShortMem(BaseMem):
    """短期记忆策略（占位实现，待补充具体逻辑）。"""

    def get_mem(self, q: str) -> list:
        return []

    def update_mem(self, q: str, ans: str) -> None:
        return
