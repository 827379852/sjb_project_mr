"""
调研项目模型
"""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProjectStatus(str, Enum):
    DRAFT = "draft"           # 草稿
    READY = "ready"           # 就绪，可启动
    RUNNING = "running"       # 运行中
    COMPLETED = "completed"   # 已完成
    ARCHIVED = "archived"     # 已归档


class ResearchProject(Base):
    """调研项目主表"""
    __tablename__ = "research_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    research_type: Mapped[str] = mapped_column(String(50), default="survey")   # survey | product_test | focus_group
    status: Mapped[str] = mapped_column(String(20), default=ProjectStatus.DRAFT)

    # 目标受众描述（自然语言，供 Agent 生成受访者用）
    target_audience: Mapped[str] = mapped_column(Text, default="")

    # 关联的问卷 ID（JSON 列表，简单实现；生产可用关联表）
    questionnaire_id: Mapped[str] = mapped_column(String(36), nullable=True)

    # 关联的受访者配置 ID
    respondent_config_id: Mapped[str] = mapped_column(String(36), nullable=True)

    # 最后一次运行 ID
    last_run_id: Mapped[str] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())