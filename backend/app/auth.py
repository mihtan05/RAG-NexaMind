"""
NexaMind AI - Authentication & JWT Security Module
Cung cấp phát hành và kiểm tra JSON Web Token (JWT) cho các API nhạy cảm.
"""

import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from fastapi import HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "nexamind-super-secret-enterprise-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 ngày

security_scheme = HTTPBearer(auto_error=False)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Tạo JWT Token có thời hạn."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Giải mã và xác thực token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None


async def get_current_user_optional(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)
) -> Dict[str, Any]:
    """
    Dependency lấy thông tin user hiện tại:
    1. Kiểm tra Authorization: Bearer <JWT>
    2. Fallback sang query param 'user_id' hoặc header 'x-user-id'
    3. Mặc định 'guest' nếu không có thông tin
    """
    token = None
    if creds and creds.credentials:
        token = creds.credentials
    elif "authorization" in request.headers:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

    if token:
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            return {
                "id": payload.get("sub"),
                "email": payload.get("email", payload.get("sub")),
                "name": payload.get("name", "Người dùng"),
                "role": payload.get("role", "user"),
                "is_authenticated": True
            }

    # Fallback cho client dev/query param
    user_id = (
        request.headers.get("x-user-id")
        or request.query_params.get("user_id")
        or "guest"
    )
    return {
        "id": user_id,
        "email": user_id if "@" in user_id else f"{user_id}@nexamind.local",
        "name": user_id,
        "role": "guest",
        "is_authenticated": False
    }
