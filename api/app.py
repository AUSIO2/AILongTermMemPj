import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api import session_manager as sm

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("AILongTermMem")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI Long-Term Memory API 启动")
    yield
    logger.info("AI Long-Term Memory API 关闭")


app = FastAPI(title="AI Long-Term Memory API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- 请求/响应模型 ----------

class CreateSessionRequest(BaseModel):
    strategy: str


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str


class SessionInfo(BaseModel):
    session_id: str
    strategy: str


class LongMemItem(BaseModel):
    id: str
    role: str | None = None
    type: str | None = None
    content: str


# ---------- 路由 ----------

@app.get("/api/strategies", response_model=list[str])
def get_strategies():
    """返回可用记忆策略列表"""
    return sm.list_strategies()


@app.post("/api/sessions", response_model=SessionInfo)
def create_session(req: CreateSessionRequest):
    """新建对话会话"""
    try:
        session = sm.create_session(req.strategy)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SessionInfo(session_id=session.session_id, strategy=session.strategy)


@app.post("/api/sessions/{session_id}/chat", response_model=ChatResponse)
def chat(session_id: str, req: ChatRequest):
    """发送消息并获取回复"""
    try:
        reply = sm.chat(session_id, req.message)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("chat error: %s", e)
        raise HTTPException(status_code=500, detail=f"Agent 处理失败: {e}")
    return ChatResponse(session_id=session_id, reply=reply)


@app.get("/api/sessions/{session_id}/history")
def get_history(session_id: str):
    """获取会话历史消息"""
    try:
        return sm.get_history(session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    """清除会话"""
    deleted = sm.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
    return {"detail": "会话已删除"}


@app.get("/api/sessions/{session_id}/memory/long", response_model=list[LongMemItem])
def list_long_mem_items(session_id: str):
    """列出该 Web 会话在 Chroma 中的长期记忆条目（每条为一条用户或助手消息向量）。"""
    try:
        items = sm.list_long_mem_items(session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return [LongMemItem(**x) for x in items]


@app.delete("/api/sessions/{session_id}/memory/long/{item_id}")
def delete_long_mem_item(session_id: str, item_id: str):
    """按 Chroma 文档 id 删除一条长期记忆（仅能删属于该 session_id 的条目）。"""
    try:
        sm.delete_long_mem_item(session_id, item_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"detail": "长期记忆条目已删除", "id": item_id}


@app.post("/api/memory/long/clear")
def clear_long_memory():
    """清空长期记忆库（long_mem 集合）。"""
    try:
        sm.clear_long_memory()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("clear_long_memory error: %s", e)
        raise HTTPException(status_code=500, detail=f"清空长期记忆失败: {e}")
    return {"detail": "长期记忆已清空"}
