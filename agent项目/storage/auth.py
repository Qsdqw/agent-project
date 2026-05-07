from storage.mysql import get_connection
from utils.logger import logger


def create_user(username: str, password_hash: str) -> int | None:
    """注册新用户，返回 user_id，重名返回 None"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, password_hash),
            )
            return cur.lastrowid
    except Exception as e:
        logger.error(f"[auth] 注册失败: {e}")
        return None
    finally:
        conn.close()


def get_user_by_username(username: str) -> dict | None:
    """根据用户名查用户，返回 {id, username, password_hash} 或 None"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, password_hash FROM users WHERE username = %s",
                (username,),
            )
            return cur.fetchone()
    except Exception as e:
        logger.error(f"[auth] 查询用户失败: {e}")
        return None
    finally:
        conn.close()


def update_last_login(user_id: int):
    """登录成功后更新时间戳，用于判断超过一年未登录的账号"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET last_login_at = NOW() WHERE id = %s",
                (user_id,),
            )
    except Exception as e:
        logger.error(f"[auth] 更新 last_login 失败: {e}")
    finally:
        conn.close()


def delete_inactive_users(inactive_days: int = 365) -> int:
    """删除超过 inactive_days 天未登录的用户，返回删除数量"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) as cnt FROM users WHERE last_login_at < DATE_SUB(NOW(), INTERVAL %s DAY)",
                (inactive_days,),
            )
            count = cur.fetchone()["cnt"]
            if count > 0:
                cur.execute(
                    "DELETE FROM users WHERE last_login_at < DATE_SUB(NOW(), INTERVAL %s DAY)",
                    (inactive_days,),
                )
                logger.info(f"[auth] 清理 {count} 个超 {inactive_days} 天未登录的用户（CASCADE 同时删除其会话和消息）")
            return count
    except Exception as e:
        logger.error(f"[auth] 清理未登录用户失败: {e}")
        return 0
    finally:
        conn.close()
