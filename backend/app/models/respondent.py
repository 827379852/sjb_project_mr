"""
受访者（Agent 人物设定）模型
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RespondentConfig(Base):
    """受访者配置组（描述一批受访者的生成策略）"""
    __tablename__ = "respondent_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")

    # 受访者数量
    count: Mapped[int] = mapped_column(Integer, default=10)

    # 受众画像描述（自然语言）
    persona_description: Mapped[str] = mapped_column(Text, default="")

    # 结构化人口统计配置（用于 Agent 生成多样化受访者）
    # {
    #   "age_range": [18, 65],
    #   "gender_distribution": {"male": 0.5, "female": 0.5},
    #   "occupation_types": ["白领", "学生", "自由职业"],
    #   "income_level": ["中等", "高"],
    #   "region": "中国一线城市",
    #   "custom_traits": ["科技爱好者", "注重性价比"]
    # }
    demographics: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Respondent(Base):
    """单个受访者 Agent 档案（实际生成后的记录）"""
    __tablename__ = "respondents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    config_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # 受访者姓名（Agent 角色名）
    name: Mapped[str] = mapped_column(String(100), default="")

    # 完整的人物设定（由 LLM 生成）
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    # profile 示例:
    # {
    #   "age": 28,
    #   "gender": "female",
    #   "occupation": "产品经理",
    #   "income": "15k-25k",
    #   "location": "北京",
    #   "personality": "理性、注重实用性",
    #   "consumption_habits": "...",
    #   "background": "..."
    # }

    # AgentSociety 中的 agent_id（运行期映射）
    agent_backend_id: Mapped[str] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())