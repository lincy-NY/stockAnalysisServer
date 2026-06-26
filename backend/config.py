"""
选股系统配置
"""
import os

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '82728231lcy123L',
    'database': 'stock',
    'charset': 'utf8mb4'
}

# JWT配置
SECRET_KEY = os.environ.get('SECRET_KEY', 'stock-secret-key-change-in-production-2026')
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_HOURS = 24

# 用户配置（单用户）
USERS = {
    'admin': {
        'password': 'admin123',
        'name': '管理员'
    }
}
