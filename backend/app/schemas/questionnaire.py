"""
问卷 Schemas
"""
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class QuestionOption(BaseModel):
    value: str
    label: str


class Question(BaseModel):
    id: str
    type: str = Field(..., description="题型: single_choice | multi_choice | scale | text | nps | ranking")
    text: str = Field(..., description="题目内容")
    required: bool = True
    options: Optional[list[str]] = None         # 选择题选项
    scale_min: Optional[int] = None              # 量表题最小值
    scale_max: Optional[int] = None              # 量表题最大值
    scale_labels: Optional[dict[str, str]] = None  # 量表标签 {"1": "非常不满意", "5": "非常满意"}
    placeholder: Optional[str] = None           # 开放题提示


class Section(BaseModel):
    id: str
    title: str
    description: str = ""
    questions: list[Question]


class QuestionnaireSchema(BaseModel):
    sections: list[Section]
    estimated_minutes: int = Field(5, description="预计完成时间（分钟）")


class QuestionnaireCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    schema_: QuestionnaireSchema = Field(..., alias="schema")
    agent_prompt_override: str = ""

    model_config = {"populate_by_name": True}


class QuestionnaireUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    schema_: Optional[QuestionnaireSchema] = Field(None, alias="schema")
    agent_prompt_override: Optional[str] = None

    model_config = {"populate_by_name": True}


class QuestionnaireOut(BaseModel):
    id: str
    name: str
    description: str
    questionnaire_schema: Any = Field(alias="schema")   # 避免与 BaseModel.schema 冲突
    agent_prompt_override: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}