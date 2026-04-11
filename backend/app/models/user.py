"""
用户模型
"""
import uuid
import secrets
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# 新用户注册赠送的积分
DEFAULT_CREDITS = 100
# 每次任务消耗的积分
TASK_COST_CREDITS = 100


def generate_api_key() -> str:
    """生成安全的 API Key，格式: mr_live_xxxxx"""
    return f"mr_live_{secrets.token_urlsafe(32)}"


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    credits: Mapped[int] = mapped_column(Integer, default=DEFAULT_CREDITS)
    api_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True, default=generate_api_key)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
