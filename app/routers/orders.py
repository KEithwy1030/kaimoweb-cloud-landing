"""
订单相关API路由
处理订单创建、查询、支付等
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import secrets

from app.database import get_db
from app.models import Order, Plan, User, Subscription
from app.schemas import (
    OrderCreate, OrderResponse, OrderDetailResponse, ApiResponse
)
from app.auth import get_current_user, get_current_admin
from app.config import settings


router = APIRouter(prefix="/api/orders", tags=["订单"])


def generate_order_number() -> str:
    """生成订单号"""
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M%S")
    random_str = secrets.token_hex(4).upper()
    return f"{timestamp}{random_str}"


@router.post("", response_model=ApiResponse, summary="创建订单")
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建订单

    - **plan_id**: 套餐ID
    """
    # 检查套餐是否存在
    plan = db.query(Plan).filter(Plan.id == order_data.plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": 2001,
                "message": "套餐不存在",
                "data": None
            }
        )

    if not plan.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 2002,
                "message": "套餐已下架",
                "data": None
            }
        )

    # 检查用户是否有未支付的订单
    pending_order = db.query(Order).filter(
        Order.user_id == current_user.id,
        Order.plan_id == plan.id,
        Order.status == "pending"
    ).first()

    if pending_order:
        return ApiResponse(
            code=0,
            message="订单创建成功",
            data={
                "order_id": pending_order.id,
                "order_number": pending_order.order_number,
                "amount": float(pending_order.amount),
                "status": pending_order.status,
                "plan": {
                    "id": plan.id,
                    "name": plan.name,
                    "traffic_gb": plan.traffic_gb,
                    "period": plan.period
                }
            }
        )

    # 创建订单
    order_number = generate_order_number()
    new_order = Order(
        order_number=order_number,
        user_id=current_user.id,
        plan_id=plan.id,
        amount=plan.price,
        status="pending",
        period=plan.period
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    return ApiResponse(
        code=0,
        message="订单创建成功",
        data={
            "order_id": new_order.id,
            "order_number": new_order.order_number,
            "amount": float(new_order.amount),
            "status": new_order.status,
            "plan": {
                "id": plan.id,
                "name": plan.name,
                "traffic_gb": plan.traffic_gb,
                "period": plan.period
            }
        }
    )


@router.get("", response_model=ApiResponse, summary="获取我的订单列表")
def get_orders(
    page: int = 1,
    page_size: int = 20,
    status_filter: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的订单列表

    - **page**: 页码，从1开始
    - **page_size**: 每页数量
    - **status_filter**: 状态过滤（pending, paid, cancelled, completed）
    """
    query = db.query(Order).filter(Order.user_id == current_user.id)

    if status_filter:
        query = query.filter(Order.status == status_filter)

    # 计算总数
    total = query.count()

    # 分页查询
    offset = (page - 1) * page_size
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(page_size).all()

    return ApiResponse(
        code=0,
        message="success",
        data={
            "orders": [
                {
                    "id": order.id,
                    "order_number": order.order_number,
                    "amount": float(order.amount),
                    "status": order.status,
                    "period": order.period,
                    "created_at": order.created_at.isoformat(),
                    "paid_at": order.paid_at.isoformat() if order.paid_at else None
                }
                for order in orders
            ],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.get("/{order_id}", response_model=ApiResponse, summary="获取订单详情")
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取订单详情

    - **order_id**: 订单ID
    """
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": 3001,
                "message": "订单不存在",
                "data": None
            }
        )

    plan = db.query(Plan).filter(Plan.id == order.plan_id).first()

    return ApiResponse(
        code=0,
        message="success",
        data={
            "id": order.id,
            "order_number": order.order_number,
            "amount": float(order.amount),
            "status": order.status,
            "period": order.period,
            "created_at": order.created_at.isoformat(),
            "paid_at": order.paid_at.isoformat() if order.paid_at else None,
            "plan": {
                "id": plan.id,
                "name": plan.name,
                "traffic_gb": plan.traffic_gb,
                "price": float(plan.price),
                "period": plan.period
            } if plan else None
        }
    )


@router.post("/{order_id}/pay", response_model=ApiResponse, summary="支付订单")
def pay_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    支付订单（模拟支付）

    支付成功后会自动在X-UI创建用户并创建订阅

    - **order_id**: 订单ID
    """
    from app.xui_client import xui_client
    from app.config import settings

    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": 3001,
                "message": "订单不存在",
                "data": None
            }
        )

    if order.status == "paid" or order.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 3003,
                "message": "订单已支付",
                "data": None
            }
        )

    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 3002,
                "message": "订单状态错误",
                "data": None
            }
        )

    # 检查套餐是否有效
    plan = db.query(Plan).filter(Plan.id == order.plan_id).first()
    if not plan or not plan.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 2002,
                "message": "套餐已下架",
                "data": None
            }
        )

    # 模拟支付成功，更新订单状态
    order.status = "paid"
    order.paid_at = datetime.utcnow()

    # 计算过期时间
    expires_at = None
    expiry_days = 30  # 默认30天
    if plan.period != "onetime":
        period_days = {
            "1month": 30,
            "3month": 90,
            "6month": 180,
            "1year": 365
        }
        expiry_days = period_days.get(plan.period, 30)
        expires_at = datetime.utcnow() + datetime.timedelta(days=expiry_days)

    # 生成X-UI邮箱标识 (使用用户ID和时间戳确保唯一)
    xui_email = f"user_{current_user.id}_{int(datetime.utcnow().timestamp())}"

    # 在X-UI中创建客户端
    xui_result = None
    xui_uuid = None

    try:
        xui_result = xui_client.add_client(
            inbound_id=settings.XUI_INBOUND_ID,
            email=xui_email,
            traffic_gb=plan.traffic_gb,
            expiry_days=expiry_days
        )
        if xui_result:
            xui_uuid = xui_result.get("uuid")
    except Exception as e:
        # X-UI创建失败，记录日志但继续流程
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"X-UI创建客户端失败: {str(e)}")

    # 生成订阅Token (使用UUID确保唯一)
    import uuid
    subscription_token = secrets.token_hex(32)

    # 创建订阅记录
    subscription = Subscription(
        user_id=current_user.id,
        plan_id=plan.id,
        order_id=order.id,
        token=subscription_token,
        xui_email=xui_email,
        xui_uuid=xui_uuid,
        traffic_total_gb=plan.traffic_gb,
        traffic_used_gb=0,
        traffic_remaining_gb=plan.traffic_gb,
        expires_at=expires_at,
        is_active=True
    )
    db.add(subscription)

    # 取消该用户的其他订阅（更换套餐会覆盖当前套餐）
    existing_subscriptions = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.id != subscription.id,
        Subscription.is_active == True
    ).all()

    for sub in existing_subscriptions:
        sub.is_active = False

    order.status = "completed"
    db.commit()
    db.refresh(subscription)

    # 生成订阅链接和连接URL
    subscription_url = xui_client.generate_subscription_url(subscription_token)
    vless_url = None
    if xui_uuid:
        vless_url = xui_client.generate_vless_url(
            uuid=xui_uuid,
            server=settings.XUI_BASE_URL.replace("http://", ""),
            port=443,
            email=xui_email
        )

    return ApiResponse(
        code=0,
        message="支付成功，VPN已开通",
        data={
            "order_id": order.id,
            "order_number": order.order_number,
            "amount": float(order.amount),
            "status": order.status,
            "subscription": {
                "id": subscription.id,
                "token": subscription.token,
                "subscription_url": subscription_url,
                "vless_url": vless_url,
                "xui_email": xui_email,
                "xui_uuid": xui_uuid,
                "traffic_total_gb": subscription.traffic_total_gb,
                "traffic_remaining_gb": subscription.traffic_remaining_gb,
                "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
                "server": settings.XUI_BASE_URL.replace("http://", ""),
                "port": 443,
                "protocol": "vless"
            }
        }
    )


@router.get("/admin/all", response_model=ApiResponse, summary="获取所有订单（管理员）")
def get_all_orders(
    page: int = 1,
    page_size: int = 20,
    status_filter: str = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    获取所有订单列表（管理员功能）

    - **page**: 页码
    - **page_size**: 每页数量
    - **status_filter**: 状态过滤
    """
    query = db.query(Order)

    if status_filter:
        query = query.filter(Order.status == status_filter)

    total = query.count()
    offset = (page - 1) * page_size
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(page_size).all()

    return ApiResponse(
        code=0,
        message="success",
        data={
            "orders": [
                {
                    "id": order.id,
                    "order_number": order.order_number,
                    "user_id": order.user_id,
                    "amount": float(order.amount),
                    "status": order.status,
                    "period": order.period,
                    "created_at": order.created_at.isoformat(),
                    "paid_at": order.paid_at.isoformat() if order.paid_at else None
                }
                for order in orders
            ],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )
