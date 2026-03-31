from abc import ABCMeta, abstractmethod
from src.agents import message_dto, MessageDTO


class BaseMem(metaclass=ABCMeta):
    @abstractmethod
    def get_mem(self, q: str) -> list[MessageDTO]:
        """根据用户的 query 获取相关记忆列表，返回 MessageDTO 列表。"""

    @abstractmethod
    def update_mem(self, q: str, ans: str) -> None:
        """将本轮对话 (q, ans) 持久化/更新到记忆中。"""
