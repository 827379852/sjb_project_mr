"""
调研运行记录模型（一次调研执行的完整生命周期）
"""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import String, Text, Integer, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RunStatus(str, Enum):
    PENDING = "pending"       # 等待执行
    INITIALIZING = "initializing"  # 初始化 Agent 中
    RUNNING = "running"       # 调研进行中
    ANALYZING = "analyzing"   # 结果分析中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 已取消


class ResearchRun(Base):
    """调研运行记录"""
    __tablename__ = "research_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=RunStatus.PENDING)

    # 进度信息
    progress: Mapped[int] = mapped_column(Integer, default=0)   # 0-100
    total_respondents: Mapped[int] = mapped_column(Integer, default=0)
    completed_respondents: Mapped[int] = mapped_column(Integer, default=0)

    # AgentSociety 实验 ID（后端映射）
    backend_experiment_id: Mapped[str] = mapped_column(String(100), nullable=True)

    # 运行时配置快照（防止后续修改影响历史记录）
    run_config_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)

    # 错误信息
    error_message: Mapped[str] = mapped_column(Text, default="")

    # Token 消耗统计
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)

    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SurveyResponse(Base):
    """问卷回复记录（每个 Agent 对每道题的回答）"""
    __tablename__ = "survey_responses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    respondent_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    questionnaire_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # 完整回答（JSON，包含所有题目的回答）
    # {
    #   "q1": "非常好",
    #   "q2": ["价格实惠", "质量好"],
    #   "q3": 8,
    #   "q4": "产品很好用，但包装可以改进..."
    # }
    answers: Mapped[dict] = mapped_column(JSON, default=dict)

    # Agent 原始对话（可选，用于深度分析）
    raw_dialog: Mapped[list] = mapped_column(JSON, default=list)

    # 情感倾向（由 LLM 分析得出）
    sentiment: Mapped[str] = mapped_column(String(20), default="")  # positive | neutral | negative

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())