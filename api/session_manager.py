import uuid
import logging
from dataclasses import dataclass, field

import src.memory as memory
from src.agents.Agent import Agent
from src.memory.long_mem import LongMem

logger = logging.getLogger("AILongTermMem")

_EXCLUDED = {"BaseMem"}

# 构造记忆模块时传入 Web 会话 id，使 LongMem / Combined* 在 Chroma metadata 中隔离
_SESSION_SCOPED = frozenset({"LongMem", "CombinedMem", "CombinedMemExtracted"})


def list_strategies() -> list[str]:
    return [name for name in memory.__all__ if name not in _EXCLUDED]


@dataclass
class Session:
    session_id: str
    strategy: str
    agent: Agent
    history: list[dict] = field(default_factory=list)


_sessions: dict[str, Session] = {}


def create_session(strategy_name: str) -> Session:
    available = list_strategies()
    if strategy_name not in available:
        raise ValueError(f"未知策略: {strategy_name}，可用策略: {available}")

    session_id = uuid.uuid4().hex
    mem_class = getattr(memory, strategy_name)
    if strategy_name in _SESSION_SCOPED:
        mem_mod = mem_class(session_id=session_id)
    else:
        mem_mod = mem_class()
    agent = Agent(mem_module=mem_mod)
    session = Session(session_id=session_id, strategy=strategy_name, agent=agent)
    _sessions[session_id] = session
    logger.info("新建会话 %s，策略: %s", session_id[:8], strategy_name)
    return session


def get_session(session_id: str) -> Session | None:
    return _sessions.get(session_id)


def delete_session(session_id: str) -> bool:
    if session_id in _sessions:
        del _sessions[session_id]
        logger.info("删除会话 %s", session_id[:8])
        return True
    return False


def chat(session_id: str, message: str) -> str:
    session = get_session(session_id)
    if session is None:
        raise KeyError(f"会话不存在: {session_id}")

    session.history.append({"role": "user", "content": message})
    reply = session.agent.chat(message)
    session.history.append({"role": "assistant", "content": reply})
    return reply


def get_history(session_id: str) -> list[dict]:
    session = get_session(session_id)
    if session is None:
        raise KeyError(f"会话不存在: {session_id}")
    return session.history


def _long_mem_for_session(session_id: str) -> LongMem:
    session = get_session(session_id)
    if session is None:
        raise KeyError(f"会话不存在: {session_id}")
    mem = session.agent.mem
    if isinstance(mem, LongMem):
        return mem
    if hasattr(mem, "long_mem") and isinstance(mem.long_mem, LongMem):
        return mem.long_mem
    raise ValueError("当前会话未使用长期记忆（请选择 LongMem 或 Combined* 策略）")


def list_long_mem_items(session_id: str) -> list[dict]:
    return _long_mem_for_session(session_id).list_mem_items()


def delete_long_mem_item(session_id: str, item_id: str) -> None:
    lm = _long_mem_for_session(session_id)
    if not lm.delete_mem_item(item_id):
        raise KeyError(f"长期记忆条目不存在或无权删除: {item_id}")


def clear_long_memory() -> None:
    """清空 long_mem 集合中全部会话的长期记忆，并刷新已打开 Agent 内的 collection 引用。"""
    from src.memory.long_mem import nuclear_reset_long_mem_collection

    roots = [s.agent.mem for s in _sessions.values()]
    nuclear_reset_long_mem_collection(roots)
    logger.info("已清空长期记忆集合并重建 long_mem（所有 Web 会话的长期向量已删除）")
