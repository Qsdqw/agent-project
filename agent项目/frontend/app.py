"""
Streamlit 前端 — 登录/注册 + 聊天界面

知识速查：
- st.session_state: Streamlit 的"内存缓存"，刷新页面时保留数据
  类比：一个字典，App 关了数据就没了
- JWT(Bearer Token) 流程：
  1. 登录成功 → 后端返回 token
  2. 前端把 token 存到 session_state
  3. 每次调 API 时在请求头带上 "Authorization: Bearer <token>"
  4. 后端解析 token → 知道是谁 → 返回对应数据
- 为什么要用 Authorization header 而不是 URL 参数？
  1. URL 参数会被浏览器历史、日志记录，不安全
  2. HTTP 头是标准的认证方式，所有 HTTP 客户端都支持
"""
import streamlit as st
import requests

API_BASE = "http://localhost:8000"
REQUEST_TIMEOUT = 5  # 请求超时秒数


# ── API 调用工具函数 ───────────────────────────

def _headers() -> dict:
    """封装认证请求头：从 session_state 取 token，拼成 Authorization header"""
    token = st.session_state.get("auth_token", "")
    return {"Authorization": f"Bearer {token}"}


def api_register(username: str, password: str) -> dict:
    try:
        r = requests.post(f"{API_BASE}/api/auth/register",
                          json={"username": username, "password": password},
                          timeout=REQUEST_TIMEOUT)
        return r.json() if r.status_code == 200 else {"error": r.json().get("detail", "注册失败")}
    except requests.RequestException:
        return {"error": "无法连接服务器，请确认后端已启动"}


def api_login(username: str, password: str) -> dict:
    try:
        r = requests.post(f"{API_BASE}/api/auth/login",
                          json={"username": username, "password": password},
                          timeout=REQUEST_TIMEOUT)
        return r.json() if r.status_code == 200 else {"error": r.json().get("detail", "登录失败")}
    except requests.RequestException:
        return {"error": "无法连接服务器，请确认后端已启动"}


def api_list_sessions() -> list[dict]:
    r = requests.get(f"{API_BASE}/api/sessions", headers=_headers(), timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def api_create_session() -> dict:
    r = requests.post(f"{API_BASE}/api/sessions", json={"title": "新会话"}, headers=_headers(), timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def api_delete_session(session_id: str):
    r = requests.delete(f"{API_BASE}/api/sessions/{session_id}", headers=_headers(), timeout=REQUEST_TIMEOUT)
    r.raise_for_status()


def api_chat_stream(session_id: str, message: str):
    r = requests.post(
        f"{API_BASE}/api/chat/stream",
        json={"session_id": session_id, "message": message},
        headers=_headers(),
        stream=True,
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
        if chunk:
            yield chunk


def switch_to_session(session_id: str, thread_id: str, history: list[dict]):
    st.session_state["session_id"] = session_id
    st.session_state["thread_id"] = thread_id
    st.session_state["message"] = history


# ── 登录 / 注册页面 ─────────────────────────────

def render_auth_page():
    """未登录时显示的选择页：登录 / 注册切换"""
    st.title("智扫通机器人智能客服")

    tab_login, tab_register = st.tabs(["登录", "注册"])

    with tab_login:
        with st.form("login_form"):
            st.text_input("用户名", key="login_username")
            st.text_input("密码", type="password", key="login_password")
            if st.form_submit_button("登录", use_container_width=True):
                result = api_login(st.session_state.login_username,
                                   st.session_state.login_password)
                if "error" in result:
                    st.error(result["error"])
                else:
                    # 登录成功：保存 token → 加载会话列表
                    st.session_state["auth_token"] = result["token"]
                    st.session_state["username"] = result["username"]
                    st.rerun()

    with tab_register:
        with st.form("register_form"):
            st.text_input("用户名", key="reg_username")
            st.text_input("密码", type="password", key="reg_password")
            st.text_input("确认密码", type="password", key="reg_password2")
            if st.form_submit_button("注册", use_container_width=True):
                if st.session_state.reg_password != st.session_state.reg_password2:
                    st.error("两次密码不一致")
                elif len(st.session_state.reg_password) < 4:
                    st.error("密码至少 4 位")
                else:
                    result = api_register(st.session_state.reg_username,
                                          st.session_state.reg_password)
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        # 注册成功自动登录
                        st.session_state["auth_token"] = result["token"]
                        st.session_state["username"] = result["username"]
                        st.rerun()


# ── 聊天主页面 ──────────────────────────────────

def render_chat_page():
    """登录后显示的完整聊天界面"""
    # 确保有当前会话
    if "session_id" not in st.session_state:
        sessions = api_list_sessions()
        if sessions:
            s = sessions[0]
            r = requests.get(f"{API_BASE}/api/sessions/{s['id']}/messages", headers=_headers())
            history = r.json() if r.status_code == 200 else []
            switch_to_session(s["id"], s["thread_id"], history)
        else:
            info = api_create_session()
            switch_to_session(info["session_id"], info["thread_id"], [])

    # ── 侧边栏 ────────────────────────

    with st.sidebar:
        st.write(f"当前用户：**{st.session_state.get('username', '')}**")

        if st.button("＋ 新会话", use_container_width=True):
            info = api_create_session()
            switch_to_session(info["session_id"], info["thread_id"], [])
            st.rerun()

        st.divider()

        sessions = api_list_sessions()
        current_sid = st.session_state["session_id"]

        for s in sessions:
            is_active = s["id"] == current_sid
            col_title, col_del = st.columns([4, 1])

            with col_title:
                label = f"{s['title']}\n{s['updated_at'][:16].replace('T', ' ')}"
                if st.button(label, key=f"sess_{s['id']}",
                             disabled=is_active, use_container_width=True):
                    r = requests.get(f"{API_BASE}/api/sessions/{s['id']}/messages", headers=_headers())
                    history = r.json() if r.status_code == 200 else []
                    switch_to_session(s["id"], s["thread_id"], history)
                    st.rerun()

            with col_del:
                if st.button("🗑", key=f"del_{s['id']}"):
                    api_delete_session(s["id"])
                    if is_active:
                        remaining = api_list_sessions()
                        if remaining:
                            switch_to_session(remaining[0]["id"], remaining[0]["thread_id"], [])
                        else:
                            info = api_create_session()
                            switch_to_session(info["session_id"], info["thread_id"], [])
                    st.rerun()

        st.divider()

        if st.button("退出登录", use_container_width=True):
            # 清掉所有登录态信息
            for key in ["auth_token", "username", "session_id", "thread_id", "message"]:
                st.session_state.pop(key, None)
            st.rerun()

    # ── 主聊天区 ────────────────────────

    st.title("智扫通机器人智能客服")
    st.divider()

    for message in st.session_state["message"]:
        st.chat_message(message["role"]).write(message["content"])

    prompt = st.chat_input()
    if prompt:
        session_id = st.session_state["session_id"]

        st.chat_message("user").write(prompt)
        st.session_state["message"].append({"role": "user", "content": prompt})

        with st.spinner("智能客服思考中"):
            res_stream = api_chat_stream(session_id, prompt)
            full_response = []

            def accumulate(generator):
                for token in generator:
                    full_response.append(token)
                    yield token

            st.chat_message("assistant").write_stream(accumulate(res_stream))
            if full_response:
                content = "".join(full_response)
                st.session_state["message"].append({"role": "assistant", "content": content})
                st.rerun()


# ── 入口：根据是否登录选择页面 ───────────────────

# 检查后端是否在线
try:
    requests.get(f"{API_BASE}/api/health", timeout=3)
except requests.RequestException:
    st.error("无法连接后端服务，请先启动 FastAPI：`uvicorn api.main:app --port 8000`")
    st.stop()

if "auth_token" not in st.session_state:
    render_auth_page()
else:
    render_chat_page()
