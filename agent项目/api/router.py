"""
注册 / 登录 API 端点

知识速查：
- bcrypt(哈希算法):
  不是加密！哈希是单向的，不能解密。验证密码时是"把用户输入的密码再哈希一次，对比两次哈希值是否相同"
  bcrypt 专门为密码设计，特点：
  1. 自带盐值(Salt) — 同一密码两次哈希结果不同，防止彩虹表攻击
  2. 慢 — 故意计算量大，暴力破解成本高
- passlib: Python 的密码哈希库，封装了 bcrypt 等算法，接口简单
- JWT 在登录时签发，客户端保存，后续请求带上
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import bcrypt
from api.deps import create_access_token
from storage.auth import create_user, get_user_by_username, update_last_login

router = APIRouter(prefix="/api/auth", tags=["认证"])


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=4, max_length=100, description="密码")


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


@router.post("/register")
def register(body: RegisterRequest):
    """
    注册流程：
    1. 查用户名是否已被占用
    2. 用 bcrypt 把密码哈希（不是加密！哈希后无法反向解出原密码）
    3. 把用户名 + 哈希值存入 users 表
    """
    # 检查用户名是否已存在
    existing = get_user_by_username(body.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已被注册",
        )

    # bcrypt.hashpw() 做了什么：
    # - bcrypt.gensalt() 生成随机盐值(Salt)
    # - hashpw() 将盐值 + 密码一起哈希
    # - 返回的字节串自带盐值信息（同一密码两次结果不同）
    password_hash = bcrypt.hashpw(
        body.password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    user_id = create_user(body.username, password_hash)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败，请稍后重试",
        )

    # 注册成功，更新 last_login_at，签发 JWT
    update_last_login(user_id)
    token = create_access_token(user_id)
    return {"ok": True, "user_id": user_id, "username": body.username, "token": token}


@router.post("/login")
def login(body: LoginRequest):
    """
    登录流程：
    1. 查用户是否存在
    2. 用 bcrypt.verify() 验证密码 — 把用户输入密码哈希后和数据库里的哈希值对比
    3. 匹配成功 → 签发 JWT，返回给客户端
    """
    user = get_user_by_username(body.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # bcrypt.checkpw() 做了什么：
    # - 从数据库存储的哈希值中提取盐值
    # - 用同一盐值对用户输入的密码哈希
    # - 对比结果是否一致
    if not bcrypt.checkpw(
        body.password.encode("utf-8"), user["password_hash"].encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    update_last_login(user["id"])
    token = create_access_token(user["id"])
    return {"ok": True, "user_id": user["id"], "username": user["username"], "token": token}
