"""
问卷设计接口
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.response import ApiResponse, PaginatedData
from app.core.exceptions import NotFoundError
from app.models.questionnaire import Questionnaire
from app.schemas.questionnaire import QuestionnaireCreate, QuestionnaireUpdate, QuestionnaireOut

router = APIRouter(prefix="/questionnaires", tags=["问卷设计"])


@router.get("", response_model=ApiResponse[PaginatedData[QuestionnaireOut]])
async def list_questionnaires(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取问卷列表"""
    query = select(Questionnaire).order_by(Questionnaire.created_at.desc())
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    items = (await db.execute(query.offset((page-1)*page_size).limit(page_size))).scalars().all()

    return ApiResponse.ok(PaginatedData.build(
        items=[QuestionnaireOut.model_validate(q) for q in items],
        total=total, page=page, page_size=page_size,
    ))


@router.post("", response_model=ApiResponse[QuestionnaireOut], status_code=201)
async def create_questionnaire(
    payload: QuestionnaireCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建问卷"""
    data = payload.model_dump(by_alias=False)
    # 将 schema_ 映射回 schema 字段
    if "schema_" in data:
        schema_val = data.pop("schema_")
        # 转为 dict（如果是 Pydantic 对象）
        data["schema"] = schema_val.model_dump() if hasattr(schema_val, "model_dump") else schema_val

    questionnaire = Questionnaire(**data)
    db.add(questionnaire)
    await db.flush()
    await db.refresh(questionnaire)
    return ApiResponse.ok(QuestionnaireOut.model_validate(questionnaire), message="问卷创建成功")


@router.get("/{questionnaire_id}", response_model=ApiResponse[QuestionnaireOut])
async def get_questionnaire(questionnaire_id: str, db: AsyncSession = Depends(get_db)):
    """获取问卷详情"""
    q = await db.get(Questionnaire, questionnaire_id)
    if not q:
        raise NotFoundError("问卷", questionnaire_id)
    return ApiResponse.ok(QuestionnaireOut.model_validate(q))


@router.put("/{questionnaire_id}", response_model=ApiResponse[QuestionnaireOut])
async def update_questionnaire(
    questionnaire_id: str,
    payload: QuestionnaireUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新问卷"""
    q = await db.get(Questionnaire, questionnaire_id)
    if not q:
        raise NotFoundError("问卷", questionnaire_id)

    data = payload.model_dump(exclude_unset=True, by_alias=False)
    if "schema_" in data:
        schema_val = data.pop("schema_")
        data["schema"] = schema_val.model_dump() if hasattr(schema_val, "model_dump") else schema_val

    for field, value in data.items():
        setattr(q, field, value)

    await db.flush()
    await db.refresh(q)
    return ApiResponse.ok(QuestionnaireOut.model_validate(q))


@router.delete("/{questionnaire_id}", response_model=ApiResponse[None])
async def delete_questionnaire(questionnaire_id: str, db: AsyncSession = Depends(get_db)):
    """删除问卷"""
    q = await db.get(Questionnaire, questionnaire_id)
    if not q:
        raise NotFoundError("问卷", questionnaire_id)
    await db.delete(q)
    return ApiResponse.ok(message="问卷已删除")