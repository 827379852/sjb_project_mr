"""
系统配置模型
用于存储可动态调整的系统参数，如最大并行用户数等
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 配置键（唯一）
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    # 配置值
    value: Mapped[str] = mapped_column(Text, nullable=False)
    # 描述
    description: Mapped[str] = mapped_column(String(500), default="")
    # 配置类型：string | int | float | bool | json
    config_type: Mapped[str] = mapped_column(String(20), default="string")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# 默认系统配置
DEFAULT_SYSTEM_CONFIGS = [
    {
        "key": "max_concurrent_users",
        "value": "4",
        "description": "最大并行用户数（同时执行市场调研任务的用户数量）",
        "config_type": "int"
    },
    {
        "key": "xhs_max_posts_per_persona",
        "value": "6",
        "description": "每个人设社媒侦察时最多抓取的帖子数量",
        "config_type": "int"
    },
    {
        "key": "xhs_max_comments_per_post",
        "value": "20",
        "description": "每篇帖子最多抓取的评论数量",
        "config_type": "int"
    },
]
