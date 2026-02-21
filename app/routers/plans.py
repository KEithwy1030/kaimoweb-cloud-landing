"""
套餐相关API路由
处理套餐列表、套餐详情查询等
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Plan
from app.schemas import PlanResponse, PlanListResponse, ApiResponse
from app.auth import get_current_user, get_current_admin


router = APIRouter(prefix="/api/plans", tags=["套餐"])


@router.get("", response_model=ApiResponse, summary="获取套餐列表")
def get_plans(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    获取套餐列表

    - **active_only**: 是否只返回上架的套餐，默认true
    """
    query = db.query(Plan).order_by(Plan.sort_order, Plan.id)

    if active_only:
        query = query.filter(Plan.is_active == True)

    plans = query.all()

    return ApiResponse(
        code=0,
        message="success",
        data={
            "plans": [
                {
                    "id": plan.id,
                    "name": plan.name,
                    "traffic_gb": plan.traffic_gb,
                    "price": float(plan.price),
                    "period": plan.period,
                    "is_unlimited_speed": plan.is_unlimited_speed,
                    "is_active": plan.is_active,
                    "sort_order": plan.sort_order,
                    "created_at": plan.created_at.isoformat()
                }
                for plan in plans
            ],
            "total": len(plans)
        }
    )


@router.get("/{plan_id}", response_model=ApiResponse, summary="获取套餐详情")
def get_plan(
    plan_id: int,
    db: Session = Depends(get_db)
):
    """
    获取套餐详情

    - **plan_id**: 套餐ID
    """
    plan = db.query(Plan).filter(Plan.id == plan_id).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": 2001,
                "message": "套餐不存在",
                "data": None
            }
        )

    return ApiResponse(
        code=0,
        message="success",
        data={
            "id": plan.id,
            "name": plan.name,
            "traffic_gb": plan.traffic_gb,
            "price": float(plan.price),
            "period": plan.period,
            "is_unlimited_speed": plan.is_unlimited_speed,
            "is_active": plan.is_active,
            "sort_order": plan.sort_order,
            "created_at": plan.created_at.isoformat()
        }
    )


@router.post("/admin", response_model=ApiResponse, summary="创建套餐（管理员）")
def create_plan(
    name: str,
    traffic_gb: int,
    price: float,
    period: str,
    is_unlimited_speed: bool = True,
    sort_order: int = 0,
    db: Session = Depends(get_db),
    admin: Plan = Depends(get_current_admin)
):
    """
    创建新套餐（管理员功能）

    - **name**: 套餐名称
    - **traffic_gb**: 流量额度（GB）
    - **price**: 价格
    - **period**: 周期（onetime, 1month, 3month, 6month, 1year）
    - **is_unlimited_speed**: 是否不限速
    - **sort_order**: 排序
    """
    new_plan = Plan(
        name=name,
        traffic_gb=traffic_gb,
        price=price,
        period=period,
        is_unlimited_speed=is_unlimited_speed,
        sort_order=sort_order
    )
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)

    return ApiResponse(
        code=0,
        message="套餐创建成功",
        data={
            "id": new_plan.id,
            "name": new_plan.name
        }
    )


@router.put("/admin/{plan_id}", response_model=ApiResponse, summary="更新套餐（管理员）")
def update_plan(
    plan_id: int,
    name: str = None,
    traffic_gb: int = None,
    price: float = None,
    period: str = None,
    is_unlimited_speed: bool = None,
    is_active: bool = None,
    sort_order: int = None,
    db: Session = Depends(get_db),
    admin: Plan = Depends(get_current_admin)
):
    """
    更新套餐信息（管理员功能）

    - **plan_id**: 套餐ID
    """
    plan = db.query(Plan).filter(Plan.id == plan_id).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": 2001,
                "message": "套餐不存在",
                "data": None
            }
        )

    # 更新字段
    if name is not None:
        plan.name = name
    if traffic_gb is not None:
        plan.traffic_gb = traffic_gb
    if price is not None:
        plan.price = price
    if period is not None:
        plan.period = period
    if is_unlimited_speed is not None:
        plan.is_unlimited_speed = is_unlimited_speed
    if is_active is not None:
        plan.is_active = is_active
    if sort_order is not None:
        plan.sort_order = sort_order

    db.commit()
    db.refresh(plan)

    return ApiResponse(
        code=0,
        message="套餐更新成功",
        data={
            "id": plan.id,
            "name": plan.name
        }
    )


@router.delete("/admin/{plan_id}", response_model=ApiResponse, summary="删除套餐（管理员）")
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    admin: Plan = Depends(get_current_admin)
):
    """
    删除套餐（管理员功能）

    - **plan_id**: 套餐ID
    """
    plan = db.query(Plan).filter(Plan.id == plan_id).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": 2001,
                "message": "套餐不存在",
                "data": None
            }
        )

    db.delete(plan)
    db.commit()

    return ApiResponse(
        code=0,
        message="套餐删除成功",
        data=None
    )
