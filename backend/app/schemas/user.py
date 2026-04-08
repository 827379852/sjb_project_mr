"""
用户 Schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class UserCreate(BaseModel):
    """注册请求"""
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    name: str = Field(..., min_length=1, max_length=50, description="用户名")


class UserLogin(BaseModel):
    """登录请求"""
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., description="密码")


class UserOut(BaseModel):
    """用户信息输出"""
    id: str
    email: str
    name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token 数据"""
    user_id: Optional[str] = None
