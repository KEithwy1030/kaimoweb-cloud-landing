"""
定时任务模块
处理流量同步等定时任务
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, date
import logging

from app.database import SessionLocal
from app.models import Subscription, TrafficLog
from app.xui_client import xui_client
from app.config import settings


logger = logging.getLogger(__name__)


# 创建调度器
scheduler = BackgroundScheduler()


def sync_traffic_data():
    """
    同步流量数据
    从X-ui获取所有用户的流量数据，更新到本地数据库
    """
    logger.info("=" * 50)
    logger.info("开始同步流量数据...")
    db = SessionLocal()

    try:
        # 从X-ui获取所有用户流量数据
        all_traffic = xui_client.get_all_users_traffic()

        if not all_traffic:
            logger.warning("未获取到任何流量数据")
            return

        updated_count = 0
        today = date.today()

        for traffic_info in all_traffic:
            email = traffic_info.get("email")
            upload_bytes = traffic_info.get("upload_bytes", 0)
            download_bytes = traffic_info.get("download_bytes", 0)
            total_bytes = traffic_info.get("total_bytes", 0)

            # 查找对应的订阅
            subscription = db.query(Subscription).filter(
                Subscription.xui_email == email,
                Subscription.is_active == True
            ).first()

            if subscription:
                # 计算流量（字节转GB）
                total_gb = round(total_bytes / (1024**3), 2)
                used_gb = total_gb

                # 更新订阅流量
                old_used = subscription.traffic_used_gb
                subscription.traffic_used_gb = used_gb
                subscription.traffic_remaining_gb = max(
                    0,
                    subscription.traffic_total_gb - used_gb
                )
                subscription.updated_at = datetime.utcnow()

                # 记录流量日志（如果今天还没有记录）
                existing_log = db.query(TrafficLog).filter(
                    TrafficLog.subscription_id == subscription.id,
                    TrafficLog.recorded_at == today
                ).first()

                if not existing_log:
                    traffic_log = TrafficLog(
                        subscription_id=subscription.id,
                        upload_bytes=upload_bytes,
                        download_bytes=download_bytes,
                        total_bytes=total_bytes,
                        rate_multiplier=1.00,
                        recorded_at=today
                    )
                    db.add(traffic_log)
                else:
                    # 更新今日日志
                    existing_log.upload_bytes = upload_bytes
                    existing_log.download_bytes = download_bytes
                    existing_log.total_bytes = total_bytes

                updated_count += 1
                logger.info(
                    f"更新订阅流量: {email}, "
                    f"使用: {old_used:.2f}GB -> {used_gb:.2f}GB, "
                    f"剩余: {subscription.traffic_remaining_gb:.2f}GB"
                )

        db.commit()
        logger.info(f"流量同步完成！更新了 {updated_count} 个订阅")

    except Exception as e:
        logger.error(f"流量同步失败: {str(e)}")
        db.rollback()
    finally:
        db.close()
        logger.info("=" * 50)


def check_expired_subscriptions():
    """
    检查过期订阅
    定时检查订阅是否过期，自动标记过期订阅为不活跃
    """
    logger.info("=" * 50)
    logger.info("开始检查过期订阅...")
    db = SessionLocal()

    try:
        # 获取所有活跃订阅
        active_subscriptions = db.query(Subscription).filter(
            Subscription.is_active == True
        ).all()

        expired_count = 0

        for subscription in active_subscriptions:
            if subscription.is_expired():
                subscription.is_active = False
                expired_count += 1
                logger.info(
                    f"订阅已过期: ID={subscription.id}, "
                    f"Token={subscription.token[:20]}..."
                )

        db.commit()
        logger.info(f"过期订阅检查完成！标记了 {expired_count} 个过期订阅")

    except Exception as e:
        logger.error(f"过期订阅检查失败: {str(e)}")
        db.rollback()
    finally:
        db.close()
        logger.info("=" * 50)


def start_scheduler():
    """
    启动定时任务调度器
    """
    # 流量同步任务：每60分钟执行一次
    scheduler.add_job(
        sync_traffic_data,
        trigger=IntervalTrigger(minutes=settings.TRAFFIC_SYNC_INTERVAL_MINUTES),
        id="sync_traffic_data",
        name="同步流量数据",
        replace_existing=True
    )

    # 过期订阅检查任务：每小时执行一次
    scheduler.add_job(
        check_expired_subscriptions,
        trigger=IntervalTrigger(minutes=60),
        id="check_expired_subscriptions",
        name="检查过期订阅",
        replace_existing=True
    )

    scheduler.start()
    logger.info("=" * 50)
    logger.info("定时任务调度器已启动")
    logger.info(f"- 流量同步: 每 {settings.TRAFFIC_SYNC_INTERVAL_MINUTES} 分钟")
    logger.info("- 过期订阅检查: 每 60 分钟")
    logger.info("=" * 50)


def stop_scheduler():
    """
    停止定时任务调度器
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("定时任务调度器已停止")
