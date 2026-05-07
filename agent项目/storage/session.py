from uuid import uuid4

from storage.mysql import get_connection
from utils.logger import logger


def create_session(user_id: int, thread_id: str = None, title: str = "新会话") -> str:
    session_id = str(uuid4())
    if thread_id is None:
        thread_id = str(uuid4())
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (id, thread_id, user_id, title) VALUES (%s, %s, %s, %s)",
                (session_id, thread_id, user_id, title)
            )
        logger.info(f"[Session] 创建会话: {session_id}")
        return session_id
    finally:
        conn.close()


def get_all_sessions(user_id: int) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, thread_id, title, created_at, updated_at FROM sessions WHERE user_id = %s ORDER BY updated_at DESC",
                (user_id,)
            )
            return cur.fetchall()
    finally:
        conn.close()


def delete_session(session_id: str, user_id: int):
    """删除会话（仅当会话属于该用户时生效）"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM sessions WHERE id = %s AND user_id = %s",
                (session_id, user_id),
            )
        logger.info(f"[Session] 删除会话: {session_id}")
    finally:
        conn.close()


def save_message(session_id: str, role: str, content: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (%s, %s, %s)",
                (session_id, role, content)
            )
    finally:
        conn.close()


def get_messages(session_id: str) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role, content FROM messages WHERE session_id = %s ORDER BY id ASC",
                (session_id,)
            )
            return cur.fetchall()
    finally:
        conn.close()


def update_session_title(session_id: str, title: str):
    if len(title) > 50:
        title = title[:50]
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sessions SET title = %s WHERE id = %s",
                (title, session_id)
            )
    finally:
        conn.close()
