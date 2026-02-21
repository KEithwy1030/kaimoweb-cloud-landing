"""
数据库模型定义
使用SQLAlchemy ORM定义所有数据库表结构
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey,
    Date, BigInteger, DECIMAL, Index
)
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func
from datetime import datetime


class Base(DeclarativeBase):
    """SQLAlchemy Base类 - 所有模型的基类"""
    pass


class TimestampMixin:
    """时间戳混合类，为模型提供创建和更新时间"""
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)


class User(Base, TimestampMixin):
    """用户表模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    balance = Column(Numeric(10, 2), default=0.00)
    commission = Column(Numeric(10, 2), default=0.00)
    pending_commission = Column(Numeric(10, 2), default=0.00)
    is_active = Column(Boolean, default=True)

    # 关系
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    admin = relationship("Admin", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class Admin(Base):
    """管理员表模型"""
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # 关系
    user = relationship("User", back_populates="admin")

    def __repr__(self):
        return f"<Admin(id={self.id}, user_id={self.user_id})>"


class Plan(Base):
    """套餐表模型"""
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    traffic_gb = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    period = Column(String(50), nullable=False)  # onetime, 1month, 3month, 6month, 1year
    is_unlimited_speed = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # 关系
    orders = relationship("Order", back_populates="plan")
    subscriptions = relationship("Subscription", back_populates="plan")

    def __repr__(self):
        return f"<Plan(id={self.id}, name={self.name}, price={self.price})>"


class Order(Base):
    """订单表模型"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_number = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(50), nullable=False, index=True)  # pending, paid, cancelled, completed
    period = Column(String(50), nullable=False)
    paid_at = Column(DateTime, nullable=True)
    transaction_id = Column(String(255), nullable=True)
    remark = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # 关系
    user = relationship("User", back_populates="orders")
    plan = relationship("Plan", back_populates="orders")
    subscriptions = relationship("Subscription", back_populates="order", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_orders_user_status', 'user_id', 'status'),
    )

    def __repr__(self):
        return f"<Order(id={self.id}, order_number={self.order_number}, status={self.status})>"


class Subscription(Base, TimestampMixin):
    """订阅表模型"""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    xui_email = Column(String(255), index=True)
    xui_uuid = Column(String(255))
    traffic_total_gb = Column(Integer, nullable=False)
    traffic_used_gb = Column(Integer, default=0)
    traffic_remaining_gb = Column(Integer, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # 关系
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")
    order = relationship("Order", back_populates="subscriptions")
    traffic_logs = relationship("TrafficLog", back_populates="subscription", cascade="all, delete-orphan")

    def is_expired(self) -> bool:
        """检查订阅是否过期"""
        if not self.is_active:
            return True
        if self.traffic_remaining_gb <= 0:
            return True
        if self.expires_at and self.expires_at < datetime.utcnow():
            return True
        return False

    def __repr__(self):
        return f"<Subscription(id={self.id}, token={self.token}, is_active={self.is_active})>"


class TrafficLog(Base):
    """流量日志表模型"""
    __tablename__ = "traffic_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False, index=True)
    upload_bytes = Column(BigInteger, nullable=False)
    download_bytes = Column(BigInteger, nullable=False)
    total_bytes = Column(BigInteger, nullable=False)
    rate_multiplier = Column(Numeric(5, 2), default=1.00)
    recorded_at = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_traffic_logs_subscription_recorded', 'subscription_id', 'recorded_at'),
    )

    subscription = relationship("Subscription", back_populates="traffic_logs")

    def __repr__(self):
        return f"<TrafficLog(id={self.id}, subscription_id={self.subscription_id}, recorded_at={self.recorded_at})>"


class Server(Base):
    """节点表模型"""
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    type = Column(String(50), default='vless')  # vless, vmess, trojan, etc.
    location = Column(String(100))
    flag = Column(String(50))  # country code or flag emoji
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    tags = Column(String(255))  # e.g. "Netflix,Chatgpt"
    rate_multiplier = Column(Numeric(5, 2), default=1.00)

    def __repr__(self):
        return f"<Server(id={self.id}, name={self.name}, host={self.host})>"


class SystemConfig(Base):
    """系统配置表模型"""
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(String, nullable=True)  # Can be large text
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<SystemConfig(key={self.key})>"
