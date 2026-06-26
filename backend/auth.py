"""
JWT 认证模块
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_HOURS, USERS

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
security = HTTPBearer()


def verify_password(plain_password: str, username: str) -> bool:
    """验证密码"""
    if username not in USERS:
        return False
    # 简单密码比对（单用户场景）
    return plain_password == USERS[username]['password']


def create_access_token(username: str) -> str:
    """创建访问令牌"""
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode = {
        'sub': username,
        'exp': expire
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """获取当前用户"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        if username is None or username not in USERS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='无效的认证凭证'
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='无效的认证凭证'
        )
