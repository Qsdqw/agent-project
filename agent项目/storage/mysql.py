import pymysql
from utils.config_loader import agent_conf
from utils.logger import logger

_db_initialized = False


def get_connection():
    return pymysql.connect(
        host=agent_conf["mysql_host"],
        port=int(agent_conf["mysql_port"]),
        user=agent_conf["mysql_user"],
        password=agent_conf["mysql_password"],
        database=agent_conf["mysql_database"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


def init_db():
    global _db_initialized
    if _db_initialized:
        return

    db_name = agent_conf["mysql_database"]

    conn = pymysql.connect(
        host=agent_conf["mysql_host"],
        port=int(agent_conf["mysql_port"]),
        user=agent_conf["mysql_user"],
        password=agent_conf["mysql_password"],
        charset="utf8mb4",
        autocommit=True
    )
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARACTER SET utf8mb4")
    finally:
        conn.close()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password_hash VARCHAR(200) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_login_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id VARCHAR(36) PRIMARY KEY,
                    thread_id VARCHAR(36) NOT NULL,
                    user_id BIGINT NOT NULL,
                    title VARCHAR(200) DEFAULT '新会话',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(36) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)
            # 兼容旧表：users 缺少 last_login_at 列时自动补充
            cur.execute("""
                SELECT COUNT(*) as cnt FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'last_login_at'
            """, (db_name,))
            if cur.fetchone()["cnt"] == 0:
                cur.execute("ALTER TABLE users ADD COLUMN last_login_at DATETIME DEFAULT CURRENT_TIMESTAMP")
                logger.info("[DB] users 表已添加 last_login_at 列")

        _db_initialized = True
        logger.info("[DB] 数据库表初始化完成")
    except Exception as e:
        logger.error(f"[DB] 数据库初始化失败: {e}")
        raise e
    finally:
        conn.close()
