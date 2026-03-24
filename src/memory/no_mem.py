from src.memory.base_mem import BaseMem


class NoMem(BaseMem):
    """无记忆策略：始终返回空记忆，更新操作为空操作。"""

    def get_mem(self, q: str) -> list:
        return []

    def update_mem(self, q: str, ans: str) -> None:
        return
