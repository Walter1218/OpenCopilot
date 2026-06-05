import os
import secrets
from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

TOKEN_FILE = os.path.expanduser("~/.asu_broker_token")
security = HTTPBearer()

def get_or_create_token() -> str:
    """获取现有的 Token，如果不存在则创建一个强随机 Token。"""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                token = f.read().strip()
                if token:
                    return token
        except Exception:
            pass
    
    # 如果不存在或读取失败，创建一个新的
    new_token = secrets.token_hex(32)
    # 以 600 权限（仅属主可读写）创建文件，防止同设备其他用户窃取
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    with os.fdopen(os.open(TOKEN_FILE, flags, 0o600), 'w') as f:
        f.write(new_token)
    return new_token

# 启动时加载或生成 Token
EXPECTED_TOKEN = get_or_create_token()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """FastAPI 依赖注入：验证请求头中的 Bearer Token"""
    if credentials.credentials != EXPECTED_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials
