"""
JWT 认证依赖注入模块

知识速查：
- JWT(JSON Web Token): 由三部分组成 — Header.Payload.Signature
  - Header: 算法名字 {"alg":"HS256"}
  - Payload: 要存的数据 {"user_id":1,"exp":过期时间}
  - Signature: 用密钥对前两部分的签名，防止篡改
- Bearer Token: HTTP 请求头里的写法 "Authorization: Bearer <token>"
  - Bearer 英文意为"持有者"，表达式是：持有这个令牌就能代表身份
- Depends(依赖注入): FastAPI 的机制
  - 端点里写 user_id = Depends(get_current_user)
  - FastAPI 调用端点前会自动执行 get_current_user，返回值注入到端点参数
"""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from utils.config_loader import agent_conf

# HTTPBearer: 从请求头提取 "Authorization: Bearer <token>"
# 用户不传 Authorization 头时自动返回 401
security = HTTPBearer()

JWT_SECRET = agent_conf["jwt_secret"]
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET 未配置！请在 .env 文件中设置 JWT_SECRET=<随机密钥>"
    )
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 365  # Token 有效期 1 年，与账号注销策略一致


def create_access_token(user_id: int) -> str:
    """登录成功后签发 JWT，有效期 365 天"""
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """
    解析请求中的 JWT，返回 user_id。

    用法：在端点参数里写 user_id: int = Depends(get_current_user)
    未登录用户请求时会收到 401 Unauthorized
    """
    # credentials.credentials 就是从 "Bearer xxx" 里取出的 xxx 部分
    token = credentials.credentials
    try:
        # 验证签名 + 解析出 payload
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id: int | None = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效")
        return user_id
    except JWTError:
        # JWTError 包含：签名不对、过期、Payload 被篡改 等所有情况
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效")
