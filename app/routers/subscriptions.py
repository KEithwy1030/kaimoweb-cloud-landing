"""
订阅相关API路由
处理订阅查询、订阅链接获取等
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import secrets

from app.database import get_db
from app.models import Subscription, Plan, User, TrafficLog
from app.schemas import ApiResponse, SubscriptionDetailResponse, SubscriptionLinkResponse
from app.auth import get_current_user
from app.config import settings


router = APIRouter(prefix="/api/subscriptions", tags=["订阅"])


@router.get("", response_model=ApiResponse, summary="获取我的订阅列表")
def get_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的所有订阅
    """
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).order_by(Subscription.created_at.desc()).all()

    result = []
    for sub in subscriptions:
        plan = db.query(Plan).filter(Plan.id == sub.plan_id).first()

        # 检查订阅是否过期
        is_expired = sub.is_expired()

        result.append({
            "id": sub.id,
            "plan_name": plan.name if plan else "未知套餐",
            "traffic_total_gb": sub.traffic_total_gb,
            "traffic_used_gb": round(sub.traffic_used_gb, 2),
            "traffic_remaining_gb": round(sub.traffic_remaining_gb, 2),
            "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
            "is_active": sub.is_active and not is_expired,
            "created_at": sub.created_at.isoformat(),
            "token": sub.token
        })

    return ApiResponse(
        code=0,
        message="success",
        data={
            "subscriptions": result,
            "total": len(result)
        }
    )


@router.get("/link", response_model=ApiResponse, summary="获取订阅链接")
def get_subscription_link(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的订阅链接
    如果有多个活跃订阅，返回最新的一个
    """
    from app.xui_client import xui_client

    # 获取最新的活跃订阅
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True
    ).order_by(Subscription.created_at.desc()).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": 4001,
                "message": "订阅不存在",
                "data": None
            }
        )

    # 检查是否过期
    if subscription.is_expired():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 4002,
                "message": "订阅已过期",
                "data": None
            }
        )

    # 生成订阅链接 (使用新的格式)
    subscription_url = xui_client.generate_subscription_url(subscription.token)

    # 生成VLESS URL
    vless_url = None
    if subscription.xui_uuid:
        vless_url = xui_client.generate_vless_url(
            uuid=subscription.xui_uuid,
            server=settings.XUI_BASE_URL.replace("http://", ""),
            port=443,
            email=subscription.xui_email or "vpn-user"
        )

    return ApiResponse(
        code=0,
        message="success",
        data={
            "subscription_url": subscription_url,
            "vless_url": vless_url,
            "token": subscription.token,
            "server": settings.XUI_BASE_URL.replace("http://", ""),
            "port": 443,
            "protocol": "vless",
            "xui_email": subscription.xui_email,
            "xui_uuid": subscription.xui_uuid
        }
    )


@router.get("/active", response_model=ApiResponse, summary="获取当前活跃订阅详情")
def get_active_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的活跃订阅详情（含VLESS连接信息）
    """
    from app.xui_client import xui_client

    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True
    ).order_by(Subscription.created_at.desc()).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": 4001,
                "message": "订阅不存在",
                "data": None
            }
        )

    # 检查是否过期
    is_expired = subscription.is_expired()
    if is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 4002,
                "message": "订阅已过期",
                "data": None
            }
        )

    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()

    # 生成订阅链接和VLESS URL
    subscription_url = xui_client.generate_subscription_url(subscription.token)
    vless_url = None
    if subscription.xui_uuid:
        vless_url = xui_client.generate_vless_url(
            uuid=subscription.xui_uuid,
            server=settings.XUI_BASE_URL.replace("http://", ""),
            port=443,
            email=subscription.xui_email or "vpn-user"
        )

    return ApiResponse(
        code=0,
        message="success",
        data={
            "id": subscription.id,
            "plan": {
                "id": plan.id,
                "name": plan.name,
                "traffic_gb": plan.traffic_gb,
                "period": plan.period
            } if plan else None,
            "subscription_url": subscription_url,
            "vless_url": vless_url,
            "connection_info": {
                "server": settings.XUI_BASE_URL.replace("http://", ""),
                "port": 443,
                "protocol": "vless",
                "uuid": subscription.xui_uuid,
                "email": subscription.xui_email
            },
            "traffic_total_gb": subscription.traffic_total_gb,
            "traffic_used_gb": round(subscription.traffic_used_gb, 2),
            "traffic_remaining_gb": round(subscription.traffic_remaining_gb, 2),
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
            "created_at": subscription.created_at.isoformat()
        }
    )


@router.get("/{subscription_id}", response_model=ApiResponse, summary="获取订阅详情")
def get_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取订阅详情

    - **subscription_id**: 订阅ID
    """
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == current_user.id
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": 4001,
                "message": "订阅不存在",
                "data": None
            }
        )

    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()

    # 检查订阅是否过期
    is_expired = subscription.is_expired()

    return ApiResponse(
        code=0,
        message="success",
        data={
            "id": subscription.id,
            "plan": {
                "id": plan.id,
                "name": plan.name,
                "traffic_gb": plan.traffic_gb,
                "price": float(plan.price),
                "period": plan.period
            } if plan else None,
            "token": subscription.token,
            "traffic_total_gb": subscription.traffic_total_gb,
            "traffic_used_gb": round(subscription.traffic_used_gb, 2),
            "traffic_remaining_gb": round(subscription.traffic_remaining_gb, 2),
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
            "is_active": subscription.is_active and not is_expired,
            "created_at": subscription.created_at.isoformat(),
            "updated_at": subscription.updated_at.isoformat()
        }
    )


@router.get("/{subscription_id}/link", response_model=ApiResponse, summary="获取指定订阅的链接")
def get_subscription_link_by_id(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取指定订阅的链接

    - **subscription_id**: 订阅ID
    """
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == current_user.id
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": 4001,
                "message": "订阅不存在",
                "data": None
            }
        )

    if subscription.is_expired():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 4002,
                "message": "订阅已过期",
                "data": None
            }
        )

    subscription_url = settings.subscription_url_template.format(token=subscription.token)

    return ApiResponse(
        code=0,
        message="success",
        data={
            "subscription_url": subscription_url,
            "token": subscription.token
        }
    )


@router.get("/{subscription_id}/traffic", response_model=ApiResponse, summary="获取订阅流量记录")
def get_subscription_traffic(
    subscription_id: int,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取订阅的流量使用记录

    - **subscription_id**: 订阅ID
    - **days**: 查询最近多少天的记录，默认30天
    """
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == current_user.id
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": 4001,
                "message": "订阅不存在",
                "data": None
            }
        )

    from datetime import timedelta
    start_date = datetime.utcnow() - timedelta(days=days)

    logs = db.query(TrafficLog).filter(
        TrafficLog.subscription_id == subscription_id,
        TrafficLog.recorded_at >= start_date.date()
    ).order_by(TrafficLog.recorded_at.desc()).all()

    result = []
    for log in logs:
        # 转换为可读格式
        def bytes_to_gb(bytes_val):
            return round(bytes_val / (1024**3), 2)

        result.append({
            "id": log.id,
            "upload_gb": bytes_to_gb(log.upload_bytes),
            "download_gb": bytes_to_gb(log.download_bytes),
            "total_gb": bytes_to_gb(log.total_bytes),
            "rate_multiplier": float(log.rate_multiplier),
            "recorded_at": log.recorded_at.isoformat(),
            "created_at": log.created_at.isoformat()
        })

    return ApiResponse(
        code=0,
        message="success",
        data={
            "logs": result,
            "total": len(result)
        }
    )
