"""
数据库初始化脚本
用于创建SQLite数据库表结构并初始化默认数据
"""
import sqlite3
import bcrypt
from datetime import datetime
from pathlib import Path


def init_database(db_path: str = "vpn_distribution.db"):
    """
    初始化数据库
    创建所有表并插入默认数据
    """
    # 确保数据库文件目录存在
    db_file = Path(db_path)
    if not db_file.parent.is_absolute():
        db_file = Path(__file__).parent / db_file

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # 创建用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            balance DECIMAL(10, 2) DEFAULT 0.00,
            commission DECIMAL(10, 2) DEFAULT 0.00,
            pending_commission DECIMAL(10, 2) DEFAULT 0.00,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建管理员表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id)
        )
    ''')

    # 创建套餐表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) NOT NULL,
            traffic_gb INTEGER NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            period VARCHAR(50) NOT NULL,
            is_unlimited_speed BOOLEAN DEFAULT TRUE,
            is_active BOOLEAN DEFAULT TRUE,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建订单表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number VARCHAR(255) UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            status VARCHAR(50) NOT NULL,
            period VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at TIMESTAMP NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (plan_id) REFERENCES plans(id)
        )
    ''')

    # 创建订阅表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            order_id INTEGER NOT NULL,
            token VARCHAR(255) UNIQUE NOT NULL,
            xui_email VARCHAR(255),
            xui_uuid VARCHAR(255),
            traffic_total_gb INTEGER NOT NULL,
            traffic_used_gb INTEGER DEFAULT 0,
            traffic_remaining_gb INTEGER NOT NULL,
            expires_at TIMESTAMP NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (plan_id) REFERENCES plans(id),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    ''')

    # 创建流量日志表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS traffic_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscription_id INTEGER NOT NULL,
            upload_bytes BIGINT NOT NULL,
            download_bytes BIGINT NOT NULL,
            total_bytes BIGINT NOT NULL,
            rate_multiplier DECIMAL(5,2) DEFAULT 1.00,
            recorded_at DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subscription_id) REFERENCES subscriptions(id)
        )
    ''')

    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_subscriptions_token ON subscriptions(token)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_subscriptions_xui_email ON subscriptions(xui_email)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_traffic_logs_subscription ON traffic_logs(subscription_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_traffic_logs_recorded_at ON traffic_logs(recorded_at)')
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_plans_name ON plans(name)')

    # 添加缺失的updated_at列（如果不存在）
    # for ORM compatibility
    try:
        cursor.execute("ALTER TABLE plans ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except sqlite3.OperationalError:
        pass  # 列已存在

    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except sqlite3.OperationalError:
        pass  # 列已存在

    try:
        cursor.execute("ALTER TABLE admins ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except sqlite3.OperationalError:
        pass  # 列已存在

    # 初始化套餐数据 (参考魔戒的套餐)
    plans_data = [
        ("2G流量-不限时间", 2, 1.0, "onetime", 1),
        ("130G流量-不限时间", 130, 14.9, "onetime", 2),
        ("420G流量-不限时间", 420, 42.0, "onetime", 3),
        ("750G流量-不限时间", 750, 69.0, "onetime", 4),
        ("1660G流量-不限时间", 1660, 138.0, "onetime", 5),
        ("3600G流量-不限时间", 3600, 279.0, "onetime", 6),
        ("10T流量-不限时间", 10240, 688.0, "onetime", 7),
    ]

    for name, traffic, price, period, sort_order in plans_data:
        cursor.execute('''
            INSERT OR IGNORE INTO plans (name, traffic_gb, price, period, sort_order)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, traffic, price, period, sort_order))

    # 创建默认管理员账户
    admin_email = "admin@vpn-local.com"
    admin_password = "admin123456"
    password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    cursor.execute('''
        INSERT OR IGNORE INTO users (email, password_hash)
        VALUES (?, ?)
    ''', (admin_email, password_hash))

    cursor.execute('''
        INSERT OR IGNORE INTO admins (user_id)
        SELECT id FROM users WHERE email = ?
    ''', (admin_email,))

    conn.commit()
    conn.close()

    print("=" * 50)
    print("数据库初始化完成！")
    print(f"数据库位置: {db_file.absolute()}")
    print(f"默认管理员账户: {admin_email} / {admin_password}")
    print("=" * 50)
    print("请登录后尽快修改默认密码！")
    print("=" * 50)


if __name__ == "__main__":
    init_database()
