"""
支付相关API路由
处理支付页面、支付提交、审核等
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
import base64
from typing import Optional

from app.database import get_db
from app.models import Order, Plan, User
from app.schemas import ApiResponse, PaymentProofSubmit
from app.auth import get_current_user, get_current_admin
from app.config import settings


router = APIRouter(prefix="/api/payment", tags=["支付"])


# 支付二维码配置 (Base64编码的图片)
# TODO: 将实际的二维码图片放在 static/images/ 目录下
ALIPAY_QR_CODE = None  # 将在下面的路由中返回图片路径
WECHAT_QR_CODE = None


@router.get("/qr-codes", response_model=ApiResponse, summary="获取支付二维码")
def get_payment_qr_codes(
    db: Session = Depends(get_db)
):
    """
    获取支付宝和微信的收款二维码

    返回二维码图片的Base64编码或URL
    """
    return ApiResponse(
        code=0,
        message="success",
        data={
            "alipay": {
                "url": "/static/images/alipay_qr.png",
                "alt": "支付宝收款码"
            },
            "wechat": {
                "url": "/static/images/wechat_qr.png",
                "alt": "微信收款码"
            },
            "amount_hint": "请备注订单号后6位",
            "contact": settings.ADMIN_CONTACT
        }
    )


@router.get("/order/{order_id}", response_model=ApiResponse, summary="获取支付订单信息")
def get_payment_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取订单的支付信息，包括金额、二维码等
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

    if order.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 3003,
                "message": "订单已完成",
                "data": None
            }
        )

    plan = db.query(Plan).filter(Plan.id == order.plan_id).first()

    return ApiResponse(
        code=0,
        message="success",
        data={
            "order_id": order.id,
            "order_number": order.order_number,
            "amount": float(order.amount),
            "status": order.status,
            "plan_name": plan.name if plan else "",
            "plan_traffic": plan.traffic_gb if plan else 0,
            "plan_period": plan.period if plan else "",
            "qr_codes": {
                "alipay": "/static/images/alipay_qr.png",
                "wechat": "/static/images/wechat_qr.png"
            },
            "payment_hint": f"请支付 {float(order.amount)} 元，备注订单号后6位: {order.order_number[-6:]}",
            "contact": settings.ADMIN_CONTACT
        }
    )

@router.post("/hupijiao-pay/{order_id}", response_model=ApiResponse, summary="发起虎皮椒支付")
async def hupijiao_pay_init(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    通过 Cloudflare Worker 中转发起虎皮椒支付
    """
    import httpx
    
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == current_user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    plan = db.query(Plan).filter(Plan.id == order.plan_id).first()
    
    # 调用 Cloudflare Worker
    worker_url = "https://kaimoweb-pay-api.keith-wyong.workers.dev/pay"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(worker_url, json={
                "orderId": order.order_number,
                "amount": float(order.amount),
                "planId": plan.name if plan else "VPN订阅"
            })
            result = resp.json()
            return ApiResponse(code=0, message="success", data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"支付网关连接失败: {str(e)}")

def fulfill_order(order: Order, db: Session):
    """
    完成订单的业务逻辑：计算过期时间、创建X-UI客户端、创建订阅
    """
    from app.xui_client import xui_client
    from app.models import Subscription, Plan, User
    import secrets

    if order.status == "completed":
        return None

    plan = db.query(Plan).filter(Plan.id == order.plan_id).first()
    user = db.query(User).filter(User.id == order.user_id).first()

    # 更新订单状态
    order.status = "paid"
    order.paid_at = datetime.utcnow()

    # 计算过期时间
    expires_at = None
    expiry_days = 30
    if plan.period != "onetime":
        period_days = {
            "1month": 30,
            "3month": 90,
            "6month": 180,
            "1year": 365
        }
        expiry_days = period_days.get(plan.period, 30)
        expires_at = datetime.utcnow() + timedelta(days=expiry_days)

    # 生成X-UI邮箱标识
    xui_email = f"user_{user.id}_{int(datetime.utcnow().timestamp())}"

    # 在X-UI中创建客户端
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
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"X-UI创建客户端失败: {str(e)}")

    # 创建订阅
    subscription_token = secrets.token_hex(32)
    subscription = Subscription(
        user_id=user.id,
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

    # 取消其他订阅
    db.query(Subscription).filter(
        Subscription.user_id == user.id,
        Subscription.id != subscription.id,
        Subscription.is_active == True
    ).update({"is_active": False})

    order.status = "completed"
    db.commit()
    db.refresh(subscription)
    return subscription

@router.post("/hupijiao-callback", include_in_schema=False)
async def hupijiao_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    由 Cloudflare Worker 转发的虎皮椒支付回调
    """
    try:
        data = await request.json()
    except Exception:
        return {"status": "error", "message": "invalid json"}
        
    order_number = data.get("trade_order_id")
    status_val = data.get("status")

    if status_val == "OD" or status_val == "success": # 虎皮椒成功状态
        order = db.query(Order).filter(Order.order_number == order_number).first()
        if order and order.status != "completed":
            fulfill_order(order, db)
            return "success" # 虎皮椒回调要求返回 success 字符串
            
    return "error"


@router.post("/submit-proof", response_model=ApiResponse, summary="提交支付凭证")
def submit_payment_proof(
    proof: PaymentProofSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    提交支付凭证，等待管理员审核

    - **proof**: 提交的凭证数据
    """
    if proof.payment_method not in ["alipay", "wechat"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 4001,
                "message": "无效的支付方式",
                "data": None
            }
        )

    order = db.query(Order).filter(
        Order.id == proof.order_id,
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

    if order.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 3003,
                "message": "订单已完成",
                "data": None
            }
        )

    # 更新订单状态为待审核
    order.status = "verifying"
    order.transaction_id = proof.transaction_id
    order.remark = proof.remark

    db.commit()

    return ApiResponse(
        code=0,
        message="支付凭证已提交，等待管理员审核",
        data={
            "order_id": order.id,
            "status": order.status
        }
    )


@router.get("/pending", response_model=ApiResponse, summary="获取待审核订单列表（管理员）")
def get_pending_payments(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    获取待审核的支付订单列表（管理员功能）
    """
    # 查询待审核和待支付的订单
    query = db.query(Order).filter(
        Order.status.in_(["pending", "verifying"])
    )

    total = query.count()
    offset = (page - 1) * page_size
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(page_size).all()

    # 获取关联的用户和套餐信息
    result_orders = []
    for order in orders:
        user = db.query(User).filter(User.id == order.user_id).first()
        plan = db.query(Plan).filter(Plan.id == order.plan_id).first()
        result_orders.append({
            "id": order.id,
            "order_number": order.order_number,
            "user_email": user.email if user else "",
            "plan_name": plan.name if plan else "",
            "amount": float(order.amount),
            "status": order.status,
            "transaction_id": order.transaction_id,
            "created_at": order.created_at.isoformat()
        })

    return ApiResponse(
        code=0,
        message="success",
        data={
            "orders": result_orders,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.post("/admin/{order_id}/approve", response_model=ApiResponse, summary="审核通过（管理员）")
def approve_payment(
    order_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    管理员审核通过支付，自动开通VPN

    - **order_id**: 订单ID
    """
    from app.xui_client import xui_client

    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": 3001,
                "message": "订单不存在",
                "data": None
            }
        )

    if order.status in ["paid", "completed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 3003,
                "message": "订单已处理",
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

    # 获取用户信息
    user = db.query(User).filter(User.id == order.user_id).first()

    # 计算过期时间
    subscription = fulfill_order(order, db)
    
    from app.xui_client import xui_client
    xui_email = subscription.xui_email
    xui_uuid = subscription.xui_uuid
    subscription_token = subscription.token

    # 生成订阅链接
    subscription_url = xui_client.generate_subscription_url(subscription_token)
    vless_url = None
    if xui_uuid:
        vless_url = xui_client.generate_vless_url(
            uuid=xui_uuid,
            server=settings.XUI_BASE_URL.replace("http://", "").split(":")[0],
            port=443,
            email=xui_email
        )

    return ApiResponse(
        code=0,
        message="审核通过，VPN已开通",
        data={
            "order_id": order.id,
            "subscription": {
                "id": subscription.id,
                "subscription_url": subscription_url,
                "vless_url": vless_url,
                "xui_email": xui_email
            }
        }
    )


@router.post("/admin/{order_id}/reject", response_model=ApiResponse, summary="审核拒绝（管理员）")
def reject_payment(
    order_id: int,
    reason: str = "",
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    管理员拒绝支付申请

    - **order_id**: 订单ID
    - **reason**: 拒绝原因
    """
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": 3001,
                "message": "订单不存在",
                "data": None
            }
        )

    if order.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 3003,
                "message": "订单已完成，无法拒绝",
                "data": None
            }
        )

    # 将订单状态改回待支付
    order.status = "pending"
    db.commit()

    return ApiResponse(
        code=0,
        message="已拒绝支付申请",
        data={
            "order_id": order.id,
            "reason": reason
        }
    )


@router.get("/status/{order_id}", response_model=ApiResponse, summary="查询支付状态")
def get_payment_status(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    查询订单支付状态（用于前端轮询）
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

    status_map = {
        "pending": "待支付",
        "verifying": "待审核",
        "paid": "已支付",
        "completed": "已完成",
        "cancelled": "已取消"
    }

    data = {
        "order_id": order.id,
        "status": order.status,
        "status_text": status_map.get(order.status, order.status),
        "paid_at": order.paid_at.isoformat() if order.paid_at else None
    }

    if order.status == "completed":
        from app.models import Subscription
        from app.xui_client import xui_client
        sub = db.query(Subscription).filter(Subscription.order_id == order.id).first()
        if sub:
            data["subscription"] = {
                "id": sub.id,
                "subscription_url": xui_client.generate_subscription_url(sub.token),
                "vless_url": xui_client.generate_vless_url(
                    uuid=sub.xui_uuid,
                    server=settings.XUI_BASE_URL.replace("http://", "").split(":")[0],
                    port=443,
                    email=sub.xui_email
                ) if sub.xui_uuid else None
            }

    return ApiResponse(
        code=0,
        message="success",
        data=data
    )
@router.post("/instant-pay/{order_id}", response_model=ApiResponse, summary="模拟即时支付成功")
def instant_pay(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    模拟支付成功并立即开通（测试用）
    """
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    if order.status == "completed":
        return ApiResponse(code=0, message="订单已完成", data={"status": "completed"})

    # 直接调用 approve_payment 的内部逻辑
    # 为了简化，我们在这里重复一部分逻辑或直接修改状态
    plan = db.query(Plan).filter(Plan.id == order.plan_id).first()
    
    # 修改订单状态
    order.status = "paid"
    order.paid_at = datetime.utcnow()
    db.commit()

    # 调用审核通过接口逻辑 (由于 approve_payment 已经是 API 路由，我们手动执行其核心逻辑)
    # 因为 FastAPI 内部调用带 Depends 的函数较复杂，我们这里做一个简化逻辑触发
    # 实际上，既然是模拟，我们可以直接在后台标记完成后返回
    
    # 真正的做法应该是调用 app.routers.payment.approve_payment，但由于 context 限制，
    # 我们直接在这里完成订阅创建（核心逻辑复制）
    
    from app.xui_client import xui_client
    import secrets

    # 完成订单
    subscription = fulfill_order(order, db)

    from app.xui_client import xui_client
    xui_email = subscription.xui_email
    xui_uuid = subscription.xui_uuid
    subscription_token = subscription.token

    # 生成返回数据
    subscription_url = xui_client.generate_subscription_url(subscription_token)
    vless_url = None
    if xui_uuid:
        vless_url = xui_client.generate_vless_url(
            uuid=xui_uuid,
            server=settings.XUI_BASE_URL.replace("http://", "").split(":")[0],
            port=443,
            email=xui_email
        )

    return ApiResponse(
        code=0,
        message="支付成功并已自动开通！",
        data={
            "order_id": order.id,
            "status": "completed",
            "subscription": {
                "id": subscription.id,
                "subscription_url": subscription_url,
                "vless_url": vless_url,
                "xui_email": xui_email
            }
        }
    )
