import redis
from utils.config_loader import agent_conf
from utils.logger import logger

_redis = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis(
            host=agent_conf["redis_host"],
            port=int(agent_conf["redis_port"]),
            password=agent_conf["redis_password"] or None,
            decode_responses=True,
        )
        try:
            _redis.ping()
        except redis.ConnectionError:
            _redis = None
            logger.error("[Redis] 连接失败，请确认 Redis 已启动")
            raise
    return _redis
