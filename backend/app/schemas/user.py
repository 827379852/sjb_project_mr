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
    is_superuser: bool = False
    credits: int = 0
    api_key: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """用户更新请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="用户名")
    is_active: Optional[bool] = Field(None, description="是否激活")
    credits: Optional[int] = Field(None, ge=0, description="积分")


class Token(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token 数据"""
    user_id: Optional[str] = None


class CreditsDeduct(BaseModel):
    """积分扣除请求"""
    amount: int = Field(..., ge=1, description="扣除数量")
    reason: str = Field(..., description="扣除原因")


class CreditsRefund(BaseModel):
    """积分返还请求"""
    amount: int = Field(..., ge=1, description="返还数量")
    reason: str = Field(..., description="返还原因")
