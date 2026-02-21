"""
认证相关API路由
处理用户注册、登录、获取当前用户信息等
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import (
    UserRegister, UserLogin, UserResponse, UserWithTokenResponse, ApiResponse
)
from app.auth import (
    get_password_hash, verify_password, authenticate_user,
    create_access_token, get_current_user
)
from app.config import settings


router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=ApiResponse, summary="用户注册")
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    用户注册接口

    - **email**: 用户邮箱（唯一）
    - **password**: 用户密码（至少6位）
    """
    # 检查邮箱是否已存在
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 1002,
                "message": "用户已存在",
                "data": None
            }
        )

    # 创建新用户
    password_hash = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=password_hash
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 生成Token
    token_data = {"sub": new_user.id}
    access_token = create_access_token(token_data)

    return ApiResponse(
        code=0,
        message="注册成功",
        data={
            "user_id": new_user.id,
            "email": new_user.email,
            "token": access_token
        }
    )


@router.post("/login", response_model=ApiResponse, summary="用户登录")
def login(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    用户登录接口

    - **email**: 用户邮箱
    - **password**: 用户密码
    """
    # 验证用户
    user = authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": 1004,
                "message": "邮箱或密码错误",
                "data": None
            }
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": 1006,
                "message": "用户已被禁用",
                "data": None
            }
        )

    # 生成Token
    token_data = {"sub": user.id}
    access_token = create_access_token(token_data)

    return ApiResponse(
        code=0,
        message="登录成功",
        data={
            "user_id": user.id,
            "email": user.email,
            "token": access_token,
            "balance": float(user.balance),
            "commission": float(user.commission)
        }
    )


@router.get("/me", response_model=ApiResponse, summary="获取当前用户信息")
def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录用户的信息

    需要在请求头中携带Token: Authorization: Bearer {token}
    """
    return ApiResponse(
        code=0,
        message="success",
        data={
            "user_id": current_user.id,
            "email": current_user.email,
            "balance": float(current_user.balance),
            "commission": float(current_user.commission),
            "pending_commission": float(current_user.pending_commission),
            "is_active": current_user.is_active,
            "created_at": current_user.created_at.isoformat()
        }
    )
