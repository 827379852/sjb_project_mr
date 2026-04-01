"""
调研项目 Schemas
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.research_project import ProjectStatus


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="项目名称")
    description: str = Field("", description="项目描述")
    research_type: str = Field("survey", description="调研类型: survey | product_test | focus_group")
    target_audience: str = Field("", description="目标受众描述（自然语言）")
    questionnaire_id: Optional[str] = Field(None, description="关联问卷 ID")
    respondent_config_id: Optional[str] = Field(None, description="受访者配置 ID")


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    research_type: Optional[str] = None
    target_audience: Optional[str] = None
    questionnaire_id: Optional[str] = None
    respondent_config_id: Optional[str] = None
    status: Optional[ProjectStatus] = None


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str
    research_type: str
    status: ProjectStatus
    target_audience: str
    questionnaire_id: Optional[str]
    respondent_config_id: Optional[str]
    last_run_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}