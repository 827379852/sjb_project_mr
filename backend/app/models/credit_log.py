"""
积分记录模型
"""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CreditLogType(str, Enum):
    """积分日志类型"""
    DEDUCT = "deduct"           # 扣除
    REFUND = "refund"           # 返还
    REWARD = "reward"           # 奖励
    ADMIN_ADJUST = "admin_adjust"  # 管理员调整


class CreditLog(Base):
    """积分记录表"""
    __tablename__ = "credit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # 积分变化量（正数为增加，负数为扣除）
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)  # 操作后余额
    log_type: Mapped[str] = mapped_column(String(20), nullable=False)  # deduct, refund, reward, admin_adjust
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)  # 描述
    related_study_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # 关联的研究ID
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    # 关联用户
    user: Mapped["User"] = relationship("User", backref="credit_logs")
