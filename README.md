# VPN 分发系统

基于 X-ui 的 VPN 分发系统 MVP 版本，类似魔戒.net 的功能实现。

## 项目简介

本项目是一个完整的 VPN 订阅分发管理系统，包含以下核心功能：

- 用户注册/登录系统（JWT 认证）
- 套餐管理和购买
- 订单系统
- 订阅管理和流量统计
- 用户首页仪表板
- 管理后台

## 技术栈

### 后端
- **框架**: FastAPI 0.109.0
- **数据库**: SQLite（生产环境可切换 PostgreSQL）
- **认证**: JWT (python-jose)
- **密码加密**: bcrypt
- **Python 版本**: 3.9+

### 前端
- **技术**: 原生 HTML + CSS + JavaScript
- **图标**: FontAwesome CDN
- **设计**: 深色主题，响应式布局

## 环境要求

### 服务器要求
- **操作系统**: Linux (Ubuntu 20.04+ 推荐)
- **Python**: 3.9 或更高版本
- **内存**: 最低 512MB
- **磁盘**: 最低 1GB

### 本地开发要求
- Python 3.9+
- pip 包管理器
- Git（可选）

## 安装步骤

### 1. 克隆项目（或上传代码）

```bash
# 如果使用 Git
git clone <repository-url>
cd vpn-distribution

# 或者直接上传文件到服务器
```

### 2. 创建虚拟环境（推荐）

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

**requirements.txt 内容：**
```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
requests==2.31.0
pytest==7.4.3
pytest-asyncio==0.21.1
```

### 4. 初始化数据库

```bash
python3 init_db.py
```

初始化后会自动创建：
- 所有数据表
- 默认管理员账户
- 初始套餐数据

### 5. 配置环境变量（可选）

创建 `.env` 文件：

```bash
SECRET_KEY=your-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_DAYS=7
DATABASE_URL=sqlite:///./vpn_distribution.db
XUI_BASE_URL=http://35.197.153.209
XUI_USERNAME=keithwy
XUI_PASSWORD=k19941030
```

## 运行后端

### 开发模式

```bash
# 直接运行
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或使用 Python
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 生产模式

```bash
# 使用 Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# 或使用 systemd 服务（见下文）
```

## 访问前端

前端文件位于 `app/static/` 目录，通过 FastAPI 静态文件服务访问。

- **首页**: http://localhost:8000/
- **登录页**: http://localhost:8000/login
- **注册页**: http://localhost:8000/register
- **管理后台**: http://localhost:8000/admin

## 默认账号信息

### 管理员账户
- **邮箱**: admin@vpn-local.com
- **密码**: admin123456

**安全提示**: 部署后请立即修改默认密码！

## 使用 systemd 部署

### 1. 创建服务文件

```bash
sudo nano /etc/systemd/system/vpn-distribution.service
```

### 2. 添加以下内容

```ini
[Unit]
Description=VPN Distribution System
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/opt/vpn-distribution
Environment="PATH=/opt/vpn-distribution/venv/bin"
ExecStart=/opt/vpn-distribution/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3. 启动服务

```bash
sudo systemctl daemon-reload
sudo systemctl enable vpn-distribution
sudo systemctl start vpn-distribution
sudo systemctl status vpn-distribution
```

### 4. 查看日志

```bash
sudo journalctl -u vpn-distribution -f
```

## 使用 Nginx 反向代理（可选）

### 1. 安装 Nginx

```bash
sudo apt update
sudo apt install nginx
```

### 2. 创建配置文件

```bash
sudo nano /etc/nginx/sites-available/vpn-distribution
```

### 3. 添加配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. 启用配置

```bash
sudo ln -s /etc/nginx/sites-available/vpn-distribution /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行仅 API 测试
pytest tests/test_api.py -v

# 运行仅数据库测试
pytest tests/test_database.py -v

# 生成覆盖率报告
pytest tests/ --cov=app --cov-report=html
```

## 项目结构

```
vpn-distribution/
├── app/                    # 应用主目录
│   ├── __init__.py
│   ├── main.py            # FastAPI 应用入口
│   ├── config.py          # 配置文件
│   ├── database.py        # 数据库连接和初始化
│   ├── models.py          # 数据库模型
│   ├── schemas.py         # Pydantic 模型
│   ├── auth.py            # 认证逻辑
│   ├── routers/           # 路由模块
│   │   ├── __init__.py
│   │   ├── auth.py        # 认证路由
│   │   ├── plans.py       # 套餐路由
│   │   ├── orders.py      # 订单路由
│   │   ├── subscriptions.py  # 订阅路由
│   │   └── dashboard.py   # 首页路由
│   └── static/            # 前端静态文件
│       ├── index.html
│       ├── login.html
│       ├── register.html
│       ├── dashboard.html
│       ├── shop.html
│       ├── my_order.html
│       ├── docs.html
│       ├── profile.html
│       ├── flow.html
│       ├── css/
│       ├── js/
│       └── img/
├── tests/                 # 测试目录
│   ├── __init__.py
│   ├── conftest.py
│   ├── pytest.ini
│   ├── test_api.py
│   └── test_database.py
├── requirements.txt       # 依赖列表
├── init_db.py            # 数据库初始化脚本
├── deploy.sh             # 部署脚本
├── vpn_distribution.db   # SQLite 数据库文件
└── README.md             # 本文档
```

## API 文档

启动服务后访问：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 常见问题

### 1. 端口被占用

**问题**: 启动时提示 "Address already in use"

**解决方案**:
```bash
# 查找占用端口的进程
sudo lsof -i :8000

# 结束进程
sudo kill -9 <PID>

# 或使用其他端口
uvicorn app.main:app --port 8001
```

### 2. 数据库权限错误

**问题**: 无法创建或写入数据库文件

**解决方案**:
```bash
# 检查文件权限
ls -la vpn_distribution.db

# 修改权限
chmod 664 vpn_distribution.db
chown your-username:your-username vpn_distribution.db
```

### 3. 依赖安装失败

**问题**: pip install 失败

**解决方案**:
```bash
# 升级 pip
pip install --upgrade pip

# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4. JWT Token 无效

**问题**: API 返回 "Token invalid or expired"

**解决方案**:
- 检查 `.env` 文件中的 `SECRET_KEY`
- 确保前后端使用相同的 `SECRET_KEY`
- Token 默认有效期为 7 天，过期需要重新登录

### 5. 静态文件 404

**问题**: HTML/CSS/JS 文件无法加载

**解决方案**:
```bash
# 检查 static 目录权限
ls -la app/static/

# 确保目录存在
mkdir -p app/static/css app/static/js app/static/img
```

## 安全建议

1. **修改默认密码**: 部署后立即修改管理员密码
2. **使用 HTTPS**: 生产环境必须启用 HTTPS
3. **保护 SECRET_KEY**: 使用强随机密钥，不要提交到版本控制
4. **定期备份**: 定期备份数据库文件
5. **防火墙配置**: 只开放必要端口（80、443）
6. **更新依赖**: 定期更新 Python 包以修复安全漏洞

## 后续优化

1. **支付集成**: 集成微信支付、支付宝
2. **邀请返利**: 实现推荐奖励系统
3. **工单系统**: 添加客服支持功能
4. **节点监控**: 实时监控节点状态
5. **Telegram Bot**: 添加机器人订阅分发
6. **CDN 加速**: 使用 CDN 加速静态资源
7. **多语言**: 支持国际化

## 联系方式

- **项目负责人**: 老k
- **服务器**: 35.197.153.209 (新加坡)
- **X-ui 管理员**: keithwy / k19941030

## 许可证

本项目仅供学习和内部使用。

---

**最后更新**: 2026-02-18
