"""
Pydantic模型定义
用于API请求/响应的数据验证和序列化
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# ==================== 通用响应模型 ====================

class ApiResponse(BaseModel):
    """API统一响应格式"""
    code: int = Field(default=0, description="状态码，0表示成功")
    message: str = Field(default="success", description="响应消息")
    data: Optional[dict] = Field(default=None, description="响应数据")


class ErrorDetail(BaseModel):
    """错误详情"""
    field: str
    message: str


# ==================== 用户相关模型 ====================

class UserRegister(BaseModel):
    """用户注册请求"""
    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(..., min_length=6, max_length=50, description="用户密码")


class UserLogin(BaseModel):
    """用户登录请求"""
    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(..., description="用户密码")


class UserResponse(BaseModel):
    """用户信息响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    balance: Decimal
    commission: Decimal
    pending_commission: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserWithTokenResponse(UserResponse):
    """用户登录响应（包含Token）"""
    token: str


# ==================== 套餐相关模型 ====================

class PlanResponse(BaseModel):
    """套餐信息响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    traffic_gb: int
    price: Decimal
    period: str
    is_unlimited_speed: bool
    is_active: bool
    sort_order: int
    created_at: datetime


class PlanListResponse(BaseModel):
    """套餐列表响应"""
    plans: List[PlanResponse]
    total: int


# ==================== 订单相关模型 ====================

class OrderCreate(BaseModel):
    """创建订单请求"""
    plan_id: int = Field(..., description="套餐ID")


class OrderResponse(BaseModel):
    """订单信息响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    user_id: int
    plan_id: int
    amount: Decimal
    status: str
    period: str
    created_at: datetime
    paid_at: Optional[datetime] = None

    # 关联数据
    plan: Optional[PlanResponse] = None


class OrderDetailResponse(OrderResponse):
    """订单详情响应（包含套餐信息）"""
    plan: PlanResponse


class OrderListResponse(BaseModel):
    """订单列表响应"""
    orders: List[OrderResponse]
    total: int
    page: int
    page_size: int


# ==================== 订阅相关模型 ====================

class SubscriptionResponse(BaseModel):
    """订阅信息响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    plan_id: int
    order_id: int
    token: str
    traffic_total_gb: int
    traffic_used_gb: float
    traffic_remaining_gb: float
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # 关联数据
    plan: Optional[PlanResponse] = None


class SubscriptionDetailResponse(SubscriptionResponse):
    """订阅详情响应（包含套餐信息）"""
    plan: PlanResponse


class SubscriptionLinkResponse(BaseModel):
    """订阅链接响应"""
    subscription_url: str
    qr_code: Optional[str] = None


# ==================== 流量相关模型 ====================

class TrafficLogResponse(BaseModel):
    """流量日志响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    subscription_id: int
    upload_bytes: int
    download_bytes: int
    total_bytes: int
    rate_multiplier: Decimal
    recorded_at: datetime
    created_at: datetime


class TrafficLogListResponse(BaseModel):
    """流量日志列表响应"""
    logs: List[TrafficLogResponse]
    total: int
    page: int
    page_size: int


# ==================== 首页相关模型 ====================

class DashboardResponse(BaseModel):
    """首页数据响应"""
    balance: Decimal
    traffic_total: int
    traffic_used: float
    traffic_remaining: float
    traffic_percent: int
    commission: Decimal
    pending_commission: Decimal
    subscription: Optional[SubscriptionDetailResponse] = None


# ==================== 管理后台相关模型 ====================

class PlanCreate(BaseModel):
    """创建套餐请求（管理员）"""
    name: str = Field(..., description="套餐名称")
    traffic_gb: int = Field(..., gt=0, description="流量额度（GB）")
    price: Decimal = Field(..., gt=0, description="价格")
    period: str = Field(..., description="周期：onetime, 1month, 3month, 6month, 1year")
    is_unlimited_speed: bool = Field(default=True, description="是否不限速")
    sort_order: int = Field(default=0, description="排序")


class PlanUpdate(BaseModel):
    """更新套餐请求（管理员）"""
    name: Optional[str] = None
    traffic_gb: Optional[int] = None
    price: Optional[Decimal] = None
    period: Optional[str] = None
    is_unlimited_speed: Optional[bool] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class AdminUserResponse(BaseModel):
    """管理员用户列表响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    balance: Decimal
    commission: Decimal
    is_active: bool
    created_at: datetime
    is_admin: bool


class AdminUserListResponse(BaseModel):
    """管理员用户列表响应"""
    users: List[AdminUserResponse]
    total: int
    page: int
    page_size: int


class AdminOrderListResponse(BaseModel):
    """管理员订单列表响应"""
    orders: List[OrderResponse]
    total: int
    page: int
    page_size: int


# ==================== 支付相关模型 ====================

class PayRequest(BaseModel):
    """支付请求"""
    order_id: int = Field(..., description="订单ID")


class PayResponse(BaseModel):
    """支付响应"""
    order_id: int
    order_number: str
    amount: Decimal
    status: str
    subscription: Optional[SubscriptionResponse] = None


class PaymentProofSubmit(BaseModel):
    """支付凭证提交"""
    order_id: int
    payment_method: str
    transaction_id: str
    remark: Optional[str] = None


# ==================== 分页请求模型 ====================

class PaginationRequest(BaseModel):
    """分页请求"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
