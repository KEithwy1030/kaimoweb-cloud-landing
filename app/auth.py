"""
认证模块
处理用户密码加密、JWT Token生成和验证
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User, Admin


# HTTP Bearer认证
security = HTTPBearer()


# ==================== 密码处理 ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    :param plain_password: 明文密码
    :param hashed_password: 哈希密码
    :return: 密码是否匹配
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """
    获取密码哈希值
    :param password: 明文密码
    :return: 哈希后的密码
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


# ==================== Token处理 ====================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建JWT访问令牌
    :param data: 要编码的数据
    :param expires_delta: 过期时间增量
    :return: JWT Token
    """
    to_encode = data.copy()
    # Ensure 'sub' is a string (required by JWT)
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码JWT访问令牌
    :param token: JWT Token
    :return: 解码后的数据，如果失败返回None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


# ==================== 用户认证依赖 ====================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    获取当前登录用户（依赖注入）
    :param credentials: HTTP Bearer凭证
    :param db: 数据库会话
    :return: 当前用户对象
    :raises HTTPException: 如果Token无效或用户不存在
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": 1005,
            "message": "Token无效或已过期",
            "data": None
        }
    )
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception
    # Convert sub back to integer for database query
    try:
        user_id: int = int(user_id_str)
    except (ValueError, TypeError):
        raise credentials_exception
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": 1006,
                "message": "用户已被禁用",
                "data": None
            }
        )
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    获取当前活跃用户
    :param current_user: 当前用户
    :return: 活跃用户对象
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    return current_user


# ==================== 管理员认证依赖 ====================

def get_current_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    获取当前管理员用户
    :param current_user: 当前用户
    :param db: 数据库会话
    :return: 管理员用户对象
    :raises HTTPException: 如果用户不是管理员
    """
    admin = db.query(Admin).filter(Admin.user_id == current_user.id).first()
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": 1006,
                "message": "权限不足，需要管理员权限",
                "data": None
            }
        )
    return current_user


# ==================== 辅助函数 ====================

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    验证用户登录
    :param db: 数据库会话
    :param email: 用户邮箱
    :param password: 用户密码
    :return: 验证成功返回用户对象，失败返回None
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def is_admin(db: Session, user: User) -> bool:
    """
    检查用户是否为管理员
    :param db: 数据库会话
    :param user: 用户对象
    :return: 是否为管理员
    """
    admin = db.query(Admin).filter(Admin.user_id == user.id).first()
    return admin is not None
