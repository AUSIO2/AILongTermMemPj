from abc import ABCMeta, abstractmethod


class BaseMem(metaclass=ABCMeta):
    @abstractmethod
    def get_mem(self, q: str) -> list:
        """根据用户的 query 获取相关记忆列表，返回 MessageDTO 列表。"""

    @abstractmethod
    def update_mem(self, q: str, ans: str) -> None:
        """将本轮对话 (q, ans) 持久化/更新到记忆中。"""
