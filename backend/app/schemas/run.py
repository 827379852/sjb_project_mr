"""
调研运行 & 结果 Schemas
"""
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.research_run import RunStatus


# ── 运行控制 ───────────────────────────────────────────────────────

class RunCreate(BaseModel):
    """启动一次调研运行"""
    project_id: str
    override_respondent_count: Optional[int] = Field(None, ge=1, le=1000, description="覆盖受访者数量")


class RunOut(BaseModel):
    id: str
    project_id: str
    status: RunStatus
    progress: int
    total_respondents: int
    completed_respondents: int
    backend_experiment_id: Optional[str]
    error_message: str
    input_tokens: int
    output_tokens: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── 问卷回复 ───────────────────────────────────────────────────────

class SurveyResponseOut(BaseModel):
    id: str
    run_id: str
    respondent_id: str
    questionnaire_id: str
    answers: dict
    raw_dialog: list
    sentiment: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── 分析结果 ───────────────────────────────────────────────────────

class QuestionStats(BaseModel):
    question_id: str
    question_text: str
    question_type: str
    total_responses: int
    # 选择题：选项频率分布
    option_distribution: Optional[dict[str, int]] = None
    option_percentage: Optional[dict[str, float]] = None
    # 量表/NPS：统计值
    mean: Optional[float] = None
    median: Optional[float] = None
    std_dev: Optional[float] = None
    # 开放题：关键词与主题摘要
    keywords: Optional[list[str]] = None
    themes: Optional[list[dict]] = None
    # 情感分布
    sentiment_distribution: Optional[dict[str, int]] = None


class RunAnalyticsOut(BaseModel):
    run_id: str
    project_id: str
    total_respondents: int
    completed_at: Optional[datetime]
    # 各题目统计
    question_stats: list[QuestionStats]
    # 整体情感分布
    overall_sentiment: dict[str, int]
    # 关键洞察（LLM 生成）
    key_insights: list[str]
    # 原始摘要报告（Markdown）
    summary_report: str
    # 受访者画像分布统计
    demographic_breakdown: dict[str, Any]