"""
问卷模型
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Questionnaire(Base):
    """问卷主表"""
    __tablename__ = "questionnaires"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")

    # 问卷结构：JSON Schema 格式，支持各类题型
    # schema 示例:
    # {
    #   "sections": [
    #     {
    #       "id": "s1",
    #       "title": "基本信息",
    #       "questions": [
    #         {
    #           "id": "q1",
    #           "type": "single_choice",   // single_choice | multi_choice | scale | text | nps
    #           "required": true,
    #           "text": "您如何评价该产品？",
    #           "options": ["非常好", "好", "一般", "差", "非常差"]
    #         }
    #       ]
    #     }
    #   ]
    # }
    schema: Mapped[dict] = mapped_column(JSON, default=dict)

    # Agent 提示词覆盖（可选，用于定制 Agent 的回答风格）
    agent_prompt_override: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())