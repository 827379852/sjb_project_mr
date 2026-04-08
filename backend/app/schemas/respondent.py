from __future__ import annotations
"""
受访者 Schemas
"""
from typing import Optional, Any, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field


# ── 受访者配置 ─────────────────────────────────────────────────────

class DemographicsConfig(BaseModel):
    age_range: List[int] = Field([18, 65], description="年龄范围 [min, max]")
    gender_distribution: Dict[str, float] = Field(
        {"male": 0.5, "female": 0.5},
        description="性别分布比例"
    )
    occupation_types: List[str] = Field([], description="职业类型列表")
    income_level: List[str] = Field([], description="收入层级")
    region: str = Field("中国", description="地区描述")
    custom_traits: List[str] = Field([], description="自定义特征标签")


class RespondentConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    count: int = Field(10, ge=1, le=1000, description="受访者数量")
    persona_description: str = Field("", description="受众画像自然语言描述")
    demographics: DemographicsConfig = Field(default_factory=DemographicsConfig)


class RespondentConfigUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    count: Optional[int] = Field(None, ge=1, le=1000)
    persona_description: Optional[str] = None
    demographics: Optional[DemographicsConfig] = None


class RespondentConfigOut(BaseModel):
    id: str
    name: str
    description: str
    count: int
    persona_description: str
    demographics: Any
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── 受访者档案 ─────────────────────────────────────────────────────

class RespondentProfile(BaseModel):
    age: int
    gender: str
    occupation: str
    income: str = ""
    location: str = ""
    personality: str = ""
    consumption_habits: str = ""
    background: str = ""
    custom_attributes: Dict[str, Any] = {}


class RespondentOut(BaseModel):
    id: str
    config_id: str
    name: str
    profile: Any
    agent_backend_id: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}