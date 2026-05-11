"""
JWT 认证依赖注入模块
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from utils.config_loader import agent_conf
from storage.redis_client import get_redis
from utils.logger import logger

security = HTTPBearer()

JWT_SECRET = agent_conf["jwt_secret"]
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET 未配置！请在 .env 文件中设置 JWT_SECRET=<随机密钥>"
    )
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 365


def create_access_token(user_id: int) -> str:
    """登录成功后签发 JWT，携带唯一 jti 用于吊销"""
    payload = {
        "user_id": user_id,
        "jti": uuid.uuid4().hex,
        "exp": datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def revoke_token(token: str):
    """将 token 加入 Redis 黑名单，直到其自然过期"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            now = datetime.now(timezone.utc).timestamp()
            ttl = int(exp - now)
            if ttl > 0:
                r = get_redis()
                r.setex(f"token:revoked:{jti}", ttl, "1")
    except JWTError:
        pass


def _is_token_revoked(jti: str) -> bool:
    try:
        return get_redis().exists(f"token:revoked:{jti}") > 0
    except Exception:
        logger.warning("[JWT] Redis 不可用，跳过黑名单校验")
        return False


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        if jti and _is_token_revoked(jti):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌已失效")
        user_id: int | None = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效")
        return user_id
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效")
