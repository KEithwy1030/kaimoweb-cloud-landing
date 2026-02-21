"""
VPN Distribution System - Main Application
FastAPI应用入口文件
"""
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from app.config import settings
from app.database import init_db, get_db_path
from app.auth import get_current_admin
from app.routers import auth, plans, orders, subscriptions, dashboard, payment, wallet
from app.routers.admin import router as admin_router


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    启动时初始化数据库
    """
    # 启动时执行
    logger.info("=" * 50)
    logger.info(f"启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"数据库位置: {get_db_path()}")
    logger.info("=" * 50)

    # 初始化数据库
    try:
        init_db()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")

    yield

    # 关闭时执行
    logger.info("应用关闭")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="VPN Distribution System API",
    lifespan=lifespan
)


# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理"""
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": 5001,
            "message": str(exc.detail),
            "data": None
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.error(f"未处理的异常: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 5001,
            "message": "服务器内部错误",
            "data": None
        }
    )


# 注册路由
app.include_router(auth.router)
app.include_router(plans.router)
app.include_router(orders.router)
app.include_router(subscriptions.router)
app.include_router(dashboard.router)
app.include_router(payment.router)
app.include_router(wallet.router)
app.include_router(admin_router)
from app.routers import client_sub
app.include_router(client_sub.router)


# 静态文件服务
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# HTML页面路由
from fastapi.responses import FileResponse

pages_dir = static_dir / "pages"


@app.get("/login", include_in_schema=False)
async def login_page():
    """登录页面"""
    page_path = pages_dir / "login.html"
    if page_path.exists():
        return FileResponse(str(page_path))
    return {"error": "Login page not found"}


@app.get("/register", include_in_schema=False)
async def register_page():
    """注册页面"""
    page_path = pages_dir / "register.html"
    if page_path.exists():
        return FileResponse(str(page_path))
    return {"error": "Register page not found"}


@app.get("/dashboard", include_in_schema=False)
async def dashboard_page():
    """首页"""
    page_path = pages_dir / "dashboard.html"
    if page_path.exists():
        return FileResponse(str(page_path))
    return {"error": "Dashboard page not found"}


@app.get("/shop", include_in_schema=False)
async def shop_page():
    """商店页面"""
    page_path = pages_dir / "shop.html"
    if page_path.exists():
        return FileResponse(str(page_path))
    return {"error": "Shop page not found"}


@app.get("/my_order", include_in_schema=False)
async def my_order_page():
    """我的订单页面"""
    page_path = pages_dir / "my_order.html"
    if page_path.exists():
        return FileResponse(str(page_path))
    return {"error": "My Order page not found"}


@app.get("/payment", include_in_schema=False)
async def payment_page():
    """支付页面"""
    page_path = pages_dir / "payment.html"
    if page_path.exists():
        return FileResponse(str(page_path))
    return {"error": "Payment page not found"}


@app.get("/recharge", include_in_schema=False)
async def recharge_page():
    """充值页面"""
    page_path = pages_dir / "recharge.html"
    if page_path.exists():
        return FileResponse(str(page_path))
    return {"error": "Recharge page not found"}


@app.get("/docs", include_in_schema=False)
async def docs_page():
    """使用文档页面"""
    page_path = pages_dir / "docs.html"
    if page_path.exists():
        return FileResponse(str(page_path))
    return {"error": "Docs page not found"}


@app.get("/user-docs", include_in_schema=False)
async def user_docs_page():
    """使用文档页面 (备用路由)"""
    page_path = pages_dir / "docs.html"
    if page_path.exists():
        return FileResponse(str(page_path))
    return {"error": "Docs page not found"}


@app.get("/profile", include_in_schema=False)
async def profile_page():
    """个人中心页面"""
    page_path = pages_dir / "profile.html"
    if page_path.exists():
        return FileResponse(str(page_path))
    return {"error": "Profile page not found"}


@app.get("/flow", include_in_schema=False)
async def flow_page():
    """流量明细页面"""
    page_path = pages_dir / "flow.html"
    if page_path.exists():
        return FileResponse(str(page_path))
    return {"error": "Flow page not found"}


@app.get("/admin", include_in_schema=False)
async def admin_page():
    """管理后台页面"""
    page_path = pages_dir / "admin.html"
    if page_path.exists():
        return FileResponse(str(page_path))
    return {"error": "Admin page not found"}


# 根路径
@app.get("/", tags=["根路径"])
async def root():
    """根路径，返回登录页面"""
    page_path = pages_dir / "login.html"
    if page_path.exists():
        return FileResponse(str(page_path))
    return {"message": "Welcome to VPN Distribution System API"}


# 健康检查
@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION
    }


# 错误码说明
@app.get("/api/codes", tags=["系统"])
async def error_codes():
    """返回错误码说明"""
    return {
        "error_codes": {
            "0": "成功",
            "1001": "参数错误",
            "1002": "用户已存在",
            "1003": "用户不存在",
            "1004": "密码错误",
            "1005": "Token无效或过期",
            "1006": "权限不足",
            "2001": "套餐不存在",
            "2002": "套餐已下架",
            "3001": "订单不存在",
            "3002": "订单状态错误",
            "3003": "订单已支付",
            "4001": "订阅不存在",
            "4002": "订阅已过期",
            "4003": "流量不足",
            "5001": "服务器内部错误"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
