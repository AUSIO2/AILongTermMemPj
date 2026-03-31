from src.agents import MessageDTO, Role
from src.memory.base_mem import BaseMem
from src.memory.constant import *
import chromadb
import uuid

class LongMem(BaseMem):
    """长期记忆策略（占位实现，待补充具体逻辑）。"""
    def __init__(self) -> None:
        self.collection_name = f"long_mem"
        import os
        os.makedirs("./memorystore", exist_ok=True)
        self.client = chromadb.PersistentClient(path="./memorystore")
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception as e:
            print(e)
            pass
        self.collection = self.client.create_collection(name=self.collection_name)

    def get_mem(self, q: str) -> list[MessageDTO]:
        """从长期记忆中检索最相关的消息"""
        if self.collection.count() == 0:
            return []

        translated_result:list[MessageDTO] = []
        results = self.collection.query(
            query_texts= [q],
            n_results =  LONG_MEM_N
        )
        if results and results['documents']:
            docs = results['documents'][0]
            for doc in docs:
                msg = MessageDTO.model_validate_json(doc)
                translated_result.append(msg)
        return translated_result

    def update_mem(self, q: str, ans: str) -> None:
        """向量数据库的add"""
        user_msg = MessageDTO(role=Role.USER, content=q)
        assist_msg = MessageDTO(role=Role.USER, content=ans)
        docs = [
            user_msg.model_dump_json(),
            assist_msg.model_dump_json()
        ]
        id = [uuid.uuid4().hex,uuid.uuid4().hex]
        meta = [
            {"role": Role.USER.value,"type":"q"},
            {"role": Role.ASSISTANT.value,"type":"a"},
        ]
        self.collection.add(
            documents = docs,
            ids= id,
            metadatas = meta
        )
        return
