"""FastAPI 后端 — Agent 核心 API"""
import time
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent.react_agent import ReactAgent
from storage.session import (
    create_session, get_all_sessions, delete_session,
    save_message, get_messages, update_session_title
)
from storage.mysql import init_db
from storage.auth import delete_inactive_users
from api.deps import get_current_user
from api.router import router as auth_router

app = FastAPI(title="智扫通智能客服 API")

# 注册认证路由（/api/auth/register, /api/auth/login）
app.include_router(auth_router)

# agent_pool 结构：{session_id: (agent, last_access_timestamp)}
agent_pool: dict[str, tuple[ReactAgent, float]] = {}
MAX_AGENTS = 100       # 最多缓存 100 个 Agent 实例
AGENT_TTL = 1800       # 30 分钟未使用自动回收


def _evict_expired_agents(now: float):
    """清理超过 TTL 的 Agent 实例，释放内存"""
    expired = [k for k, v in agent_pool.items() if now - v[1] > AGENT_TTL]
    for k in expired:
        agent_pool.pop(k, None)


def get_or_create_agent(session_id: str, thread_id: str, history: list[dict]) -> ReactAgent:
    now = time.time()
    _evict_expired_agents(now)

    if session_id not in agent_pool:
        # 超出容量上限，淘汰最久未用的
        if len(agent_pool) >= MAX_AGENTS:
            oldest = min(agent_pool, key=lambda k: agent_pool[k][1])
            agent_pool.pop(oldest)
        agent = ReactAgent()
        if history:
            agent.restore_from_messages(history, thread_id)
        agent_pool[session_id] = (agent, now)
    else:
        # 刷新最后访问时间
        agent_pool[session_id] = (agent_pool[session_id][0], now)

    return agent_pool[session_id][0]


# ── Pydantic 模型 ──────────────────────────────

class SessionCreate(BaseModel):
    title: str = "新会话"


class SessionInfo(BaseModel):
    id: str
    thread_id: str
    title: str
    created_at: str
    updated_at: str


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    message: str = Field(..., description="用户消息")


# ── 启动事件 ────────────────────────────────────

@app.on_event("startup")
def startup():
    init_db()
    # 每次启动清理超过一年未登录的用户（CASCADE 自动删除其会话和消息）
    delete_inactive_users(inactive_days=365)


# ── 会话管理端点 ────────────────────────────────

@app.get("/api/sessions")
def list_sessions(user_id: int = Depends(get_current_user)) -> list[SessionInfo]:
    sessions = get_all_sessions(user_id)
    return [
        SessionInfo(
            id=s["id"],
            thread_id=s["thread_id"],
            title=s["title"],
            created_at=str(s["created_at"]),
            updated_at=str(s["updated_at"]),
        )
        for s in sessions
    ]


@app.post("/api/sessions")
def new_session(body: SessionCreate, user_id: int = Depends(get_current_user)):
    thread_id = str(uuid4())
    session_id = create_session(user_id=user_id, thread_id=thread_id, title=body.title)
    return {"session_id": session_id, "thread_id": thread_id}


@app.delete("/api/sessions/{session_id}")
def remove_session(session_id: str, user_id: int = Depends(get_current_user)):
    delete_session(session_id, user_id=user_id)  # user_id 校验：仅能删自己的会话
    agent_pool.pop(session_id, None)
    return {"ok": True}


@app.get("/api/sessions/{session_id}/messages")
def session_messages(session_id: str, user_id: int = Depends(get_current_user)):
    return get_messages(session_id)


# ── 聊天端点 ────────────────────────────────────

@app.post("/api/chat/stream")
def chat_stream(body: ChatRequest, user_id: int = Depends(get_current_user)):
    session_id = body.session_id
    history = get_messages(session_id)

    sessions = get_all_sessions(user_id)
    thread_id = None
    for s in sessions:
        if s["id"] == session_id:
            thread_id = s["thread_id"]
            break
    if not thread_id:
        raise HTTPException(status_code=404, detail="会话不存在")

    agent = get_or_create_agent(session_id, thread_id, history)

    save_message(session_id, "user", body.message)
    if len(history) == 0:
        update_session_title(session_id, body.message)

    def generate():
        full_response = []
        for token in agent.execute_stream(body.message, thread_id=thread_id):
            full_response.append(token)
            yield token
        save_message(session_id, "assistant", "".join(full_response))

    return StreamingResponse(
        generate(),
        media_type="text/plain; charset=utf-8"
    )


# ── 健康检查 ────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "active_agents": len(agent_pool)}
