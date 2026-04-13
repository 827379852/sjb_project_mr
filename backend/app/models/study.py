"""
研究记录相关模型
"""
import uuid
from datetime import datetime
from typing import List, Dict
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Study(Base):
    """研究记录 - 对应一次完整的研究流程"""
    __tablename__ = "studies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 基本信息
    title: Mapped[str] = mapped_column(String(200), default="新研究")
    user_request: Mapped[str] = mapped_column(Text, default="")  # 用户输入的研究需求
    design_content: Mapped[str] = mapped_column(Text, default="")  # LLM 生成的设计框架
    previous_design_content: Mapped[str] = mapped_column(Text, default="")  # 调整前的设计框架（用于对比）

    # 状态
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | in_progress | completed | failed | archived
    current_phase: Mapped[str] = mapped_column(String(20), default="idle")
    error_message: Mapped[str] = mapped_column(Text, default="")  # 错误信息（失败时记录）

    # 来源
    source: Mapped[str] = mapped_column(String(20), default="web")  # web | api

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    user: Mapped["User"] = relationship("User", backref="studies")
    personas: Mapped[List["StudyPersona"]] = relationship(back_populates="study", cascade="all, delete-orphan")
    interviews: Mapped[List["StudyInterview"]] = relationship(back_populates="study", cascade="all, delete-orphan")
    scout_results: Mapped[List["ScoutResult"]] = relationship(back_populates="study", cascade="all, delete-orphan")
    reports: Mapped[List["StudyReport"]] = relationship(back_populates="study", cascade="all, delete-orphan")


class StudyPersona(Base):
    """研究相关的人设"""
    __tablename__ = "study_personas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    study_id: Mapped[str] = mapped_column(String(36), ForeignKey("studies.id"), nullable=False, index=True)

    # 人设基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    occupation: Mapped[str] = mapped_column(String(100), default="")
    city: Mapped[str] = mapped_column(String(50), default="")
    background: Mapped[str] = mapped_column(Text, default="")

    # 完整人设数据 (JSON)
    persona_data: Mapped[Dict] = mapped_column(JSON, default=dict)

    source: Mapped[str] = mapped_column(String(20), default="generated")  # generated | scouted
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    study: Mapped["Study"] = relationship(back_populates="personas")
    scout_results: Mapped[List["ScoutResult"]] = relationship(back_populates="persona", cascade="all, delete-orphan")


class StudyInterview(Base):
    """访谈记录"""
    __tablename__ = "study_interviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    study_id: Mapped[str] = mapped_column(String(36), ForeignKey("studies.id"), nullable=False, index=True)
    persona_id: Mapped[str] = mapped_column(String(36), nullable=False)  # 关联 study_personas.id

    persona_name: Mapped[str] = mapped_column(String(100), default="")
    messages: Mapped[List] = mapped_column(JSON, default=list)  # [{role, content}]

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    study: Mapped["Study"] = relationship(back_populates="interviews")


class ScoutResult(Base):
    """社媒侦察结果"""
    __tablename__ = "scout_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    study_id: Mapped[str] = mapped_column(String(36), ForeignKey("studies.id"), nullable=False, index=True)
    persona_id: Mapped[str] = mapped_column(String(36), ForeignKey("study_personas.id"), nullable=True, index=True)

    keywords: Mapped[List] = mapped_column(JSON, default=list)
    platforms: Mapped[List] = mapped_column(JSON, default=list)
    posts: Mapped[List] = mapped_column(JSON, default=list)  # [{platform, title, content, author, link, comments, ...}]
    insights: Mapped[List] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    study: Mapped["Study"] = relationship(back_populates="scout_results")
    persona: Mapped["StudyPersona"] = relationship(back_populates="scout_results")


class StudyReport(Base):
    """研究报告"""
    __tablename__ = "study_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    study_id: Mapped[str] = mapped_column(String(36), ForeignKey("studies.id"), nullable=False, index=True)

    content: Mapped[str] = mapped_column(Text, default="")  # Markdown 格式报告内容
    format: Mapped[str] = mapped_column(String(20), default="markdown")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    study: Mapped["Study"] = relationship(back_populates="reports")
