import uuid
import logging
from dataclasses import dataclass, field

import src.memory as memory
from src.agents.Agent import Agent

logger = logging.getLogger("AILongTermMem")

_EXCLUDED = {"BaseMem"}


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

    mem_class = getattr(memory, strategy_name)
    agent = Agent(mem_module=mem_class())
    session_id = uuid.uuid4().hex
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


def clear_long_memory() -> None:
    """
    清空长期记忆集合。
    - 优先复用当前活跃会话中的 LongMem 实例
    - 若没有活跃实例，则临时创建一个 LongMem 执行清理
    """
    long_mem_cls = getattr(memory, "LongMem", None)
    if long_mem_cls is None:
        raise ValueError("未找到 LongMem 策略")

    for session in _sessions.values():
        if isinstance(session.agent.mem, long_mem_cls):
            session.agent.mem.clear_mem()
            logger.info("已通过活跃会话清空长期记忆")
            return

    # 没有活跃 LongMem 会话时，临时实例化后清空
    long_mem_cls().clear_mem()
    logger.info("已通过临时实例清空长期记忆")
