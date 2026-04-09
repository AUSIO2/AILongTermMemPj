import os
import uuid
import logging

import chromadb

from src.agents.message_dto import MessageDTO, Role
from src.memory.base_mem import BaseMem
from src.memory.constant import LONG_MEM_N

logger = logging.getLogger("AILongTermMem")


class LongMem(BaseMem):
    """长期记忆策略：使用向量数据库存储与检索对话记录。"""

    def __init__(self) -> None:
        os.makedirs("./memorystore", exist_ok=True)
        self.client = chromadb.PersistentClient(path="./memorystore")
        self.collection = self.client.get_or_create_collection(name="long_mem")

    def get_mem(self, q: str) -> list[MessageDTO]:
        """从长期记忆中检索最相关的消息。"""
        if self.collection.count() == 0:
            return []

        results = self.collection.query(query_texts=[q], n_results=LONG_MEM_N)
        if not results or not results["documents"]:
            return []

        messages = [MessageDTO.model_validate_json(doc) for doc in results["documents"][0]]
        if messages:
            logger.info("  [向量搜索] 根据提问 '%s' 检索出 %d 条相关的长期记忆", q, len(messages))
        return messages

    def update_mem(self, q: str, ans: str) -> None:
        """将本轮对话写入向量数据库。"""
        user_msg = MessageDTO(role=Role.USER, content=q)
        assist_msg = MessageDTO(role=Role.ASSISTANT, content=ans)
        self.collection.add(
            documents=[user_msg.model_dump_json(), assist_msg.model_dump_json()],
            ids=[uuid.uuid4().hex, uuid.uuid4().hex],
            metadatas=[
                {"role": Role.USER.value, "type": "q"},
                {"role": Role.ASSISTANT.value, "type": "a"},
            ],
        )

    def clear_mem(self) -> None:
        """清空当前长期记忆集合。"""
        self.client.delete_collection(name="long_mem")
        self.collection = self.client.get_or_create_collection(name="long_mem")
