"""
首页相关API路由
处理首页数据展示
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta

from app.database import get_db
from app.models import Subscription, Plan, User, Order, TrafficLog
from app.schemas import ApiResponse
from app.auth import get_current_user


router = APIRouter(prefix="/api/dashboard", tags=["首页"])


@router.get("", response_model=ApiResponse, summary="获取首页数据")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取首页数据，包括：
    - 钱包余额
    - 总流量/剩余流量
    - 可用佣金
    - 我的订阅信息
    """
    # 获取用户基本信息
    balance = float(current_user.balance) if current_user.balance else 0
    commission = float(current_user.commission) if current_user.commission else 0
    pending_commission = float(current_user.pending_commission) if current_user.pending_commission else 0

    # 获取最新活跃订阅
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True
    ).order_by(Subscription.created_at.desc()).first()

    traffic_total = 0
    traffic_used = 0
    traffic_remaining = 0
    traffic_percent = 0
    subscription_data = None

    if subscription:
        plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()

        # 检查订阅是否过期
        is_expired = subscription.is_expired()
        is_active = subscription.is_active and not is_expired

        traffic_total = subscription.traffic_total_gb
        traffic_used = round(subscription.traffic_used_gb, 2)
        traffic_remaining = round(subscription.traffic_remaining_gb, 2)

        # 计算流量使用百分比
        if traffic_total > 0:
            traffic_percent = int((traffic_used / traffic_total) * 100)
            traffic_percent = min(traffic_percent, 100)

        # 订阅描述
        description = ""
        if subscription.expires_at:
            description = f"该订阅将于 {subscription.expires_at.strftime('%Y-%m-%d')} 过期，或流量用完为止"
        else:
            description = "该订阅长期有效！"

        subscription_data = {
            "id": subscription.id,
            "plan_name": plan.name if plan else "未知套餐",
            "plan_id": subscription.plan_id,
            "is_active": is_active,
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
            "description": description,
            "token": subscription.token
        }

    return ApiResponse(
        code=0,
        message="success",
        data={
            "balance": balance,
            "traffic_total": traffic_total,
            "traffic_used": traffic_used,
            "traffic_remaining": traffic_remaining,
            "traffic_percent": traffic_percent,
            "commission": commission,
            "pending_commission": pending_commission,
            "subscription": subscription_data
        }
    )


@router.get("/stats", response_model=ApiResponse, summary="获取统计数据")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户的统计数据，包括：
    - 总订单数
    - 总消费金额
    - 订阅数量
    - 最近流量记录
    """
    # 统计订单
    total_orders = db.query(Order).filter(
        Order.user_id == current_user.id
    ).count()

    # 统计已支付订单总额
    paid_orders = db.query(Order).filter(
        Order.user_id == current_user.id,
        Order.status.in_(["paid", "completed"])
    ).all()
    total_spent = sum(float(order.amount) for order in paid_orders)

    # 统计订阅
    active_subscriptions = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True
    ).count()

    # 最近流量记录
    start_date = datetime.utcnow() - timedelta(days=7)
    recent_traffic = db.query(TrafficLog).join(Subscription).filter(
        Subscription.user_id == current_user.id,
        TrafficLog.recorded_at >= start_date.date()
    ).order_by(TrafficLog.recorded_at.desc()).limit(10).all()

    traffic_records = []
    for log in recent_traffic:
        def bytes_to_gb(bytes_val):
            return round(bytes_val / (1024**3), 2)

        traffic_records.append({
            "upload_gb": bytes_to_gb(log.upload_bytes),
            "download_gb": bytes_to_gb(log.download_bytes),
            "total_gb": bytes_to_gb(log.total_bytes),
            "recorded_at": log.recorded_at.isoformat()
        })

    return ApiResponse(
        code=0,
        message="success",
        data={
            "total_orders": total_orders,
            "total_spent": round(total_spent, 2),
            "active_subscriptions": active_subscriptions,
            "recent_traffic": traffic_records
        }
    )


@router.get("/refresh", response_model=ApiResponse, summary="刷新订阅信息")
def refresh_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    刷新当前用户的订阅信息
    从X-ui获取最新流量数据（如果已对接）
    """
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True
    ).order_by(Subscription.created_at.desc()).first()

    if not subscription:
        return ApiResponse(
            code=0,
            message="success",
            data={
                "message": "暂无活跃订阅"
            }
        )

    # 如果已对接X-ui，可以在这里获取最新流量数据
    # from app.xui_client import get_xui_client
    # xui_client = get_xui_client()
    # traffic_data = xui_client.get_user_traffic(subscription.xui_email)
    # if traffic_data:
    #     subscription.traffic_used_gb = traffic_data.get("total_gb", 0)
    #     subscription.traffic_remaining_gb = max(0, subscription.traffic_total_gb - subscription.traffic_used_gb)
    #     db.commit()

    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()
    is_expired = subscription.is_expired()

    return ApiResponse(
        code=0,
        message="success",
        data={
            "plan_name": plan.name if plan else "未知套餐",
            "traffic_total_gb": subscription.traffic_total_gb,
            "traffic_used_gb": round(subscription.traffic_used_gb, 2),
            "traffic_remaining_gb": round(subscription.traffic_remaining_gb, 2),
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
            "is_active": subscription.is_active and not is_expired,
            "updated_at": subscription.updated_at.isoformat()
        }
    )


# 管理员统计数据
@router.get("/admin/stats", response_model=ApiResponse, summary="获取管理员统计数据")
def get_admin_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user)
):
    """
    获取管理员统计数据
    需要管理员权限
    """
    from app.auth import is_admin
    if not is_admin(db, admin):
        return ApiResponse(
            code=1006,
            message="权限不足",
            data=None
        )

    # 统计用户数
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()

    # 统计订单数
    total_orders = db.query(Order).count()
    paid_orders = db.query(Order).filter(Order.status.in_(["paid", "completed"])).count()
    total_revenue = db.query(func.sum(Order.amount)).filter(
        Order.status.in_(["paid", "completed"])
    ).scalar() or 0

    # 统计订阅数
    total_subscriptions = db.query(Subscription).count()
    active_subscriptions = db.query(Subscription).filter(
        Subscription.is_active == True
    ).count()

    # 今日新增用户
    today = datetime.utcnow().date()
    today_users = db.query(User).filter(
        func.date(User.created_at) == today
    ).count()

    # 今日订单
    today_orders = db.query(Order).filter(
        func.date(Order.created_at) == today
    ).count()

    # 今日收入
    today_revenue = db.query(func.sum(Order.amount)).filter(
        func.date(Order.created_at) == today,
        Order.status.in_(["paid", "completed"])
    ).scalar() or 0

    return ApiResponse(
        code=0,
        message="success",
        data={
            "users": {
                "total": total_users,
                "active": active_users,
                "today_new": today_users
            },
            "orders": {
                "total": total_orders,
                "paid": paid_orders,
                "today": today_orders
            },
            "subscriptions": {
                "total": total_subscriptions,
                "active": active_subscriptions
            },
            "revenue": {
                "total": float(total_revenue),
                "today": float(today_revenue)
            }
        }
    )
