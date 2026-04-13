from __future__ import annotations
"""
研究记录 Schema
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class StudyCreate(BaseModel):
    """创建研究请求"""
    user_request: str = Field(..., description="研究需求")
    context: str = Field("", description="补充上下文")
    title: str = Field("新研究", description="研究标题")


class StudyUpdate(BaseModel):
    """更新研究请求"""
    title: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = Field(None)
    current_phase: Optional[str] = Field(None)


class StudyOut(BaseModel):
    """研究列表项输出"""
    id: str
    user_id: str
    title: str
    status: str
    current_phase: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PersonaOut(BaseModel):
    """人设输出"""
    id: str
    name: str
    age: Optional[int] = None
    occupation: Optional[str] = None
    city: Optional[str] = None
    background: Optional[str] = None
    persona_data: Dict[str, Any] = Field(default_factory=dict)
    source: str = "generated"

    model_config = {"from_attributes": True}


class InterviewOut(BaseModel):
    """访谈输出"""
    id: str
    persona_id: str
    persona_name: str
    messages: List[Dict[str, str]] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ScoutResultOut(BaseModel):
    """侦察结果输出"""
    id: str
    persona_id: str | None = None
    keywords: List[str] = Field(default_factory=list)
    platforms: List[str] = Field(default_factory=list)
    posts: List[Dict[str, Any]] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ReportOut(BaseModel):
    """报告输出"""
    id: str
    content: str
    format: str = "markdown"

    model_config = {"from_attributes": True}


class AdjustmentHistoryItem(BaseModel):
    """调整历史记录项"""
    request: str
    result: str
    timestamp: str


class StudyDetailOut(BaseModel):
    """研究详情（包含关联数据）"""
    id: str
    user_id: str
    title: str
    user_request: str
    design_content: str
    previous_design_content: str = ""
    adjustment_history: List[AdjustmentHistoryItem] = Field(default_factory=list)
    status: str
    current_phase: str
    created_at: datetime
    updated_at: datetime

    personas: List[PersonaOut] = Field(default_factory=list)
    interviews: List[InterviewOut] = Field(default_factory=list)
    scout_results: List[ScoutResultOut] = Field(default_factory=list)
    reports: List[ReportOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}
