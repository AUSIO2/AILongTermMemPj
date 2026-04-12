import os
import uuid
import logging

import chromadb

from src.agents.message_dto import MessageDTO, Role
from src.memory.base_mem import BaseMem
from src.memory.constant import LONG_MEM_N

logger = logging.getLogger("AILongTermMem")

# 与 main.py 一致：数据落在「项目根/memorystore」，避免 uvicorn 等工作目录不同读到另一套目录
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# 未传入 session_id 时（如 CLI / 评测）共用同一逻辑桶，避免与 Web 各会话混淆时可改为按需求拆分
_GLOBAL_SESSION_TAG = "__global__"


def _memorystore_dir() -> str:
    override = os.getenv("MEMORYSTORE_PATH", "").strip()
    if override:
        return os.path.abspath(override)
    return os.path.join(_PROJECT_ROOT, "memorystore")


def nuclear_reset_long_mem_collection(agents_mem: list) -> None:
    """
    删除 long_mem 集合并重建，然后把所有已打开的 LongMem / CombinedMem.long_mem 绑到新 collection。
    供「清空全部长期记忆」类接口使用。
    """
    store = _memorystore_dir()
    os.makedirs(store, exist_ok=True)
    client = chromadb.PersistentClient(path=store)
    try:
        client.delete_collection(name="long_mem")
    except Exception:
        pass
    collection = client.get_or_create_collection(name="long_mem")

    def rebind(mem) -> None:
        if isinstance(mem, LongMem):
            mem.client = client
            mem.collection = collection
        elif hasattr(mem, "long_mem") and isinstance(mem.long_mem, LongMem):
            mem.long_mem.client = client
            mem.long_mem.collection = collection

    for root in agents_mem:
        rebind(root)


class LongMem(BaseMem):
    """长期记忆策略：使用向量数据库存储与检索对话记录。"""

    _logged_store: str | None = None

    def __init__(self, session_id: str | None = None) -> None:
        self._session_key = (session_id or _GLOBAL_SESSION_TAG).strip() or _GLOBAL_SESSION_TAG
        store = _memorystore_dir()
        os.makedirs(store, exist_ok=True)
        if LongMem._logged_store != store:
            logger.info("LongMem Chroma 持久化目录: %s", store)
            LongMem._logged_store = store
        self.client = chromadb.PersistentClient(path=store)
        self.collection = self.client.get_or_create_collection(name="long_mem")

    def get_mem(self, q: str) -> list[MessageDTO]:
        """从长期记忆中检索最相关的消息（仅本会话 session_id）。"""
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[q],
            n_results=LONG_MEM_N,
            where={"session_id": self._session_key},
        )
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
        sid = self._session_key
        self.collection.add(
            documents=[user_msg.model_dump_json(), assist_msg.model_dump_json()],
            ids=[uuid.uuid4().hex, uuid.uuid4().hex],
            metadatas=[
                {"role": Role.USER.value, "type": "q", "session_id": sid},
                {"role": Role.ASSISTANT.value, "type": "a", "session_id": sid},
            ],
        )

    def clear_mem(self) -> None:
        """清空本会话在 long_mem 中的向量记录（不影响其他 session_id）。"""
        try:
            self.collection.delete(where={"session_id": self._session_key})
        except Exception as e:
            logger.warning("按 session 清空长期记忆时出现异常（可能为旧数据无 session_id）: %s", e)

    def list_mem_items(self) -> list[dict]:
        """列出本会话在 Chroma 中的记录；每条对应一个 MessageDTO 文档。"""
        if self.collection.count() == 0:
            return []
        row = self.collection.get(
            where={"session_id": self._session_key},
            include=["documents", "metadatas"],
        )
        ids = row.get("ids") or []
        if not ids:
            return []
        docs = row.get("documents") or []
        metas = row.get("metadatas") or []
        out: list[dict] = []
        for i, doc_id in enumerate(ids):
            raw = docs[i] if i < len(docs) else ""
            meta = metas[i] if i < len(metas) else {}
            try:
                content = MessageDTO.model_validate_json(raw).content if raw else ""
            except Exception:
                content = raw[:500] if isinstance(raw, str) else ""
            out.append(
                {
                    "id": doc_id,
                    "role": meta.get("role"),
                    "type": meta.get("type"),
                    "content": content,
                }
            )
        return out

    def delete_mem_item(self, item_id: str) -> bool:
        """按 Chroma id 删除一条记录；仅当 metadata 中 session_id 与当前实例一致时生效。"""
        got = self.collection.get(ids=[item_id], include=["metadatas"])
        if not got.get("ids"):
            return False
        md_list = got.get("metadatas") or []
        md = md_list[0] if md_list else None
        if not md or md.get("session_id") != self._session_key:
            return False
        self.collection.delete(ids=[item_id])
        logger.info("已删除长期记忆条目 id=%s… session=%s", item_id[:12], self._session_key[:8])
        return True
