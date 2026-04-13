"""
积分记录 Schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CreditLogOut(BaseModel):
    """积分记录输出"""
    id: str
    user_id: str
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    amount: int
    balance_after: int
    log_type: str
    description: Optional[str] = None
    related_study_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreditLogListResponse(BaseModel):
    """积分记录列表响应"""
    total: int
    items: list[CreditLogOut]
